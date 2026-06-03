"""Chat endpoints — WebSocket streaming, sessions, and message history."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_active_user, verify_token
from app.database import async_session_factory, get_db
from app.models.conversation import Message, MessageRole, Session
from app.models.user import User
from app.schemas.chat import (
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionResponse,
    ClassifyRequest,
    IntentClassification,
    SynthesizeRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---- WebSocket Chat ----

@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None),
) -> None:
    """Bidirectional WebSocket for real-time chat.

    Supports:
    - TEXT frames: JSON messages with type field
    - BINARY frames: audio data
    - Streaming responses from LangGraph agent
    - Session persistence to PostgreSQL
    - Heartbeat ping/pong
    """
    # Authenticate
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    try:
        token_data = verify_token(token)
        user_id = uuid.UUID(token_data.user_id)
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()
    logger.info("WebSocket connected: user=%s session=%s", user_id, session_id)

    try:
        # Ensure session exists
        async with async_session_factory() as db:
            try:
                sid = uuid.UUID(session_id)
            except (ValueError, AttributeError):
                sid = None
            if sid:
                result = await db.execute(select(Session).where(Session.id == sid))
                session = result.scalar_one_or_none()
            else:
                session = None

            if not session:
                session = Session(user_id=user_id, language="en")
                db.add(session)
                await db.commit()
                await db.refresh(session)
                sid = session.id

        # Main message loop
        while True:
            try:
                raw = await websocket.receive()
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected: user=%s", user_id)
                break

            if "text" in raw:
                data = json.loads(raw["text"])
                msg_type = data.get("type", "message")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                if msg_type == "message":
                    content = data.get("content", "")
                    language = data.get("language", "en")

                    # Persist user message
                    async with async_session_factory() as db:
                        user_msg = Message(
                            session_id=sid,
                            role=MessageRole.USER,
                            content=content,
                        )
                        db.add(user_msg)
                        await db.commit()

                    # Send response start
                    request_id = str(uuid.uuid4())
                    await websocket.send_json({
                        "type": "response_start",
                        "request_id": request_id,
                    })

                    # Generate response via LLM
                    try:
                        response_text = await _generate_response(content, language, user_id)
                    except Exception as e:
                        logger.exception("Agent error")
                        response_text = "I apologize, but I encountered an issue. Please try again."

                    # Stream response in chunks
                    chunk_size = 20
                    for i in range(0, len(response_text), chunk_size):
                        chunk = response_text[i:i + chunk_size]
                        await websocket.send_json({
                            "type": "response_chunk",
                            "content": chunk,
                            "request_id": request_id,
                        })

                    # Send response end
                    await websocket.send_json({
                        "type": "response_end",
                        "request_id": request_id,
                        "full_content": response_text,
                    })

                    # Persist assistant message
                    async with async_session_factory() as db:
                        asst_msg = Message(
                            session_id=sid,
                            role=MessageRole.ASSISTANT,
                            content=response_text,
                        )
                        db.add(asst_msg)
                        await db.commit()

            elif "bytes" in raw:
                # Handle binary audio frames
                audio_data = raw["bytes"]
                logger.info("Received %d bytes of audio", len(audio_data))
                # TODO: Route to ASR service when fully integrated
                await websocket.send_json({
                    "type": "response_chunk",
                    "content": "Audio received — processing...",
                    "request_id": str(uuid.uuid4()),
                })

    except Exception as e:
        logger.exception("WebSocket error: %s", e)
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            pass


async def _generate_response(content: str, language: str, user_id: uuid.UUID) -> str:
    """Generate a response using the LangGraph master agent.

    Routes through: intent classification → specialist agent → response synthesis.
    Falls back to direct LLM if the agent pipeline fails.
    """
    try:
        from app.agents.master import get_master_agent
        agent = get_master_agent()
        result = await agent.run(
            user_id=str(user_id),
            session_id="",  # Will be set by caller if needed
            message=content,
            language=language,
        )
        return result.get("reply", "I'm here to help with fashion advice!")
    except Exception as e:
        logger.warning("Master agent unavailable: %s — falling back to direct LLM", e)

    # Fallback: direct LLM call
    try:
        from app.services.llm import LLMService
        llm = LLMService()
        response = await llm.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a warm, knowledgeable AI fashion designer assistant. "
                        "You specialize in Indian fashion including sarees, lehengas, "
                        "kurtas, and Indo-western styles. You give culturally appropriate "
                        "fashion advice for Telugu, Hindi, and English speaking users. "
                        "Be enthusiastic, helpful, and specific with your recommendations."
                    ),
                },
                {"role": "user", "content": content},
            ],
            temperature=0.7,
            max_tokens=500,
        )
        return response
    except Exception as e:
        logger.warning("LLM service unavailable: %s — using static fallback", e)
        fallback_responses = {
            "en": "Thank you for your message! I'm your AI fashion assistant. I can help with outfit designs, style advice, and finding products. How can I help you today?",
            "hi": "आपके संदेश के लिए धन्यवाद! मैं आपका AI फैशन असिस्टेंट हूं। मैं आउटफिट डिज़ाइन, स्टाइल सलाह और प्रोडक्ट्स खोजने में मदद कर सकता/सकती हूं।",
            "te": "మీ సందేశానికి ధన్యవాదాలు! నేను మీ AI ఫ్యాషన్ అసిస్టెంట్‌ని. ఔట్‌ఫిట్ డిజైన్‌లు, స్టైల్ సలహాలు మరియు ఉత్పత్తులు కనుగొనడంలో నేను మీకు సహాయం చేయగలను.",
        }
        return fallback_responses.get(language, fallback_responses["en"])


# ---- REST Endpoints ----

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    """Create a new chat session."""
    session = Session(
        user_id=current_user.id,
        language=session_data.language,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    logger.info("Chat session created: %s for user %s", session.id, current_user.id)
    return ChatSessionResponse(
        id=session.id,
        language=session.language,
        title=session.title,
        started_at=session.started_at,
        ended_at=session.ended_at,
        message_count=0,
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ChatSessionResponse]:
    """List the authenticated user's chat sessions."""
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .order_by(Session.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    sessions = result.scalars().all()

    responses = []
    for s in sessions:
        count_result = await db.execute(
            select(func.count()).where(Message.session_id == s.id)
        )
        msg_count = count_result.scalar() or 0
        responses.append(ChatSessionResponse(
            id=s.id,
            language=s.language,
            title=s.title,
            started_at=s.started_at,
            ended_at=s.ended_at,
            message_count=msg_count,
        ))
    return responses


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def get_session_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ChatMessageOut]:
    """Get messages for a specific chat session."""
    # Verify session belongs to user
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    messages = result.scalars().all()
    return [ChatMessageOut.model_validate(m) for m in messages]


@router.post("/classify", response_model=IntentClassification)
async def classify_intent(
    request_data: ClassifyRequest,
    current_user: User = Depends(get_current_active_user),
) -> IntentClassification:
    """Classify user intent from text input."""
    try:
        from app.services.llm import LLMService
        llm = LLMService()
        classification = await llm.classify_intent(request_data.text)
        return classification
    except Exception as e:
        logger.exception("Intent classification failed: %s", e)
        return IntentClassification(
            intent="general_chat",
            confidence=0.5,
            parameters={},
        )
