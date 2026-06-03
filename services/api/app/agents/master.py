"""
LangGraph Master Agent — Full multi-agent orchestration.

Implements a stateful agent graph:
  classify_intent → route → [design_agent | product_agent | tailor_agent | style_agent] → synthesize_response

Uses TypedDict state machine with persistent context, memory retrieval,
and per-turn observability logging via Langfuse.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Optional, TypedDict

from app.config import settings
from app.services.llm import LLMService

logger = logging.getLogger(__name__)


# ── Intent Taxonomy ──────────────────────────────────────────────────
class Intent(str, Enum):
    GREETING = "greeting"
    DESIGN_REQUEST = "design_request"
    PRODUCT_SEARCH = "product_search"
    STYLE_ADVICE = "style_advice"
    BODY_SCAN = "body_scan"
    VIRTUAL_TRYON = "virtual_tryon"
    WARDROBE_MANAGE = "wardrobe_manage"
    TAILORING = "tailoring"
    FEEDBACK = "feedback"
    GENERAL_CHAT = "general_chat"

# Map intents to specialist agent functions
AGENT_ROUTES: dict[Intent, str] = {
    Intent.DESIGN_REQUEST: "design_agent",
    Intent.PRODUCT_SEARCH: "product_agent",
    Intent.STYLE_ADVICE: "style_agent",
    Intent.TAILORING: "tailor_agent",
    Intent.BODY_SCAN: "body_scan_agent",
    Intent.VIRTUAL_TRYON: "tryon_agent",
    Intent.WARDROBE_MANAGE: "wardrobe_agent",
    Intent.FEEDBACK: "feedback_agent",
    Intent.GREETING: "greeting_agent",
    Intent.GENERAL_CHAT: "general_agent",
}


# ── Agent State (LangGraph TypedDict) ────────────────────────────────
class AgentState(TypedDict, total=False):
    # Input
    user_id: str
    session_id: str
    message: str
    language: str
    turn_count: int
    conversation_history: list[dict[str, str]]
    user_profile: dict[str, Any]

    # Intent classification
    intent: str
    intent_confidence: float
    extracted_params: dict[str, Any]

    # Agent outputs
    agent_response: str
    suggestions: list[str]
    outfit_images: list[str]
    products: list[dict[str, Any]]
    tailoring_data: dict[str, Any]

    # Metadata
    request_id: str
    processing_time_ms: float
    tokens_used: int
    agent_used: str
    error: Optional[str]


# ── Classifier Node ──────────────────────────────────────────────────
class IntentClassifier:
    """LLM-based intent classifier with confidence scoring."""

    SYSTEM_PROMPT = """You are an intent classifier for an AI-powered fashion designer assistant 
specializing in Indian fashion (sarees, lehengas, kurtas, sherwanis, Indo-western).

Classify the user's message into EXACTLY ONE intent:
- greeting: Hello, hi, namaste, how are you
- design_request: Design outfit, create look, suggest clothes for an occasion, "I want a lehenga"
- product_search: Find products, buy, purchase, shop, "show me kurtas under 2000"
- style_advice: What suits me, fashion tips, color advice, "what should I wear to a wedding"
- body_scan: Take measurements, scan body, upload photo for body profile
- virtual_tryon: Try on, see how it looks, preview on avatar
- wardrobe_manage: Add to wardrobe, my closet, what I own, organize clothes
- tailoring: Stitch, tailor, fabric requirements, sewing pattern, yardage
- feedback: I like this, I don't like, rate, thumbs up/down
- general_chat: Anything else about fashion, chitchat

Also detect language: en (English), hi (Hindi), te (Telugu), mixed (code-mixed).

Extract parameters where applicable:
- occasion: wedding, party, office, casual, festival, temple, date
- garment_type: saree, lehenga, kurta, sherwani, dress, suit, etc.
- colors: any mentioned colors
- budget: any price range mentioned (convert to INR)
- body_type: pear, apple, hourglass, rectangle, inverted_triangle
- cultural_context: South Indian, North Indian, Hyderabadi, Rajasthani, etc.
- fabric: silk, cotton, chiffon, georgette, etc.

Respond ONLY with valid JSON:
{"intent": "...", "confidence": 0.0-1.0, "language": "en|hi|te|mixed", "parameters": {...}}"""

    def __init__(self, llm: LLMService):
        self._llm = llm

    async def classify(self, message: str, history: list[dict] | None = None) -> dict:
        """Classify intent with context from conversation history."""
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

        # Add recent history for context (last 3 turns)
        if history:
            for turn in history[-6:]:
                messages.append(turn)

        messages.append({"role": "user", "content": message})

        try:
            response = await self._llm.chat_completion(
                messages=messages,
                temperature=0.05,  # Near-deterministic for classification
                max_tokens=300,
            )

            # Parse JSON
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            parsed = json.loads(text)
            return {
                "intent": parsed.get("intent", "general_chat"),
                "confidence": float(parsed.get("confidence", 0.5)),
                "language": parsed.get("language", "en"),
                "parameters": parsed.get("parameters", {}),
            }
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Intent classification parse error: %s", e)
            return {
                "intent": "general_chat",
                "confidence": 0.3,
                "language": "en",
                "parameters": {},
            }


# ── Specialist Agents ────────────────────────────────────────────────
class DesignAgent:
    """Generates outfit design descriptions and triggers SDXL generation."""

    SYSTEM_PROMPT = """You are an expert Indian fashion designer AI. Your role is to:
1. Create detailed outfit designs based on user requirements
2. Consider body type, occasion, cultural context, and season
3. Specify exact colors (use specific shades like "dusty rose" not just "pink")
4. Recommend specific fabrics with GSM/thread-count when relevant
5. Describe embroidery, embellishments, and construction details
6. Suggest complementary accessories (jewelry, footwear, clutch)

Your designs should be vivid enough to generate an image from. For Indian garments:
- Saree: describe draping style, pallu design, border width, blouse design
- Lehenga: describe silhouette (A-line/flared/mermaid), choli design, dupatta
- Kurta: describe neckline, sleeve length, length, pants style
- Sherwani: describe collar, buttons, embroidery placement

Always provide:
1. A vivid natural-language description (3-4 sentences)
2. An SDXL-ready prompt (comma-separated fashion photography descriptors)
3. Fabric and construction notes
4. Estimated price range in INR"""

    def __init__(self, llm: LLMService):
        self._llm = llm

    async def run(self, state: AgentState) -> AgentState:
        """Generate design based on extracted parameters."""
        params = state.get("extracted_params", {})

        user_prompt = f"""Design an outfit with these requirements:
- User message: {state['message']}
- Occasion: {params.get('occasion', 'not specified')}
- Garment type: {params.get('garment_type', 'any')}
- Colors: {', '.join(params.get('colors', [])) or 'designer choice'}
- Body type: {params.get('body_type', 'not specified')}
- Cultural context: {params.get('cultural_context', 'Indian')}
- Fabric preference: {params.get('fabric', 'not specified')}
- Budget: {params.get('budget', 'not specified')}

Provide:
1. Detailed design description
2. SDXL image generation prompt (professional fashion photography style)
3. Fabric and construction details
4. Estimated cost range in INR
5. 2-3 alternative suggestions

Format response as JSON:
{{
  "description": "...",
  "sdxl_prompt": "...",
  "fabric_notes": "...",
  "cost_range": "₹X,XXX - ₹XX,XXX",
  "alternatives": ["...", "..."],
  "accessories": ["...", "..."]
}}"""

        try:
            response = await self._llm.chat_completion(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,  # Creative for design
                max_tokens=800,
            )

            # Parse design response
            try:
                text = response.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                design_data = json.loads(text)

                # Build human-readable response
                state["agent_response"] = self._format_design_response(design_data, state.get("language", "en"))
                state["suggestions"] = [
                    "🎨 Generate outfit image",
                    "🔍 Find similar products",
                    "✂️ Get tailoring guide",
                    "👗 Try on my avatar",
                ]
            except json.JSONDecodeError:
                state["agent_response"] = response
                state["suggestions"] = ["Generate outfit image", "Modify design"]

        except Exception as e:
            logger.error("Design agent failed: %s", e)
            state["agent_response"] = "I'd love to help design your outfit! Could you tell me more about the occasion and any style preferences?"
            state["error"] = str(e)

        state["agent_used"] = "design_agent"
        return state

    @staticmethod
    def _format_design_response(data: dict, language: str) -> str:
        """Format design data into a rich response."""
        desc = data.get("description", "")
        fabric = data.get("fabric_notes", "")
        cost = data.get("cost_range", "")
        accessories = data.get("accessories", [])
        alts = data.get("alternatives", [])

        parts = [f"✨ **Design Concept**\n{desc}"]

        if fabric:
            parts.append(f"\n🧵 **Fabric & Construction**\n{fabric}")
        if cost:
            parts.append(f"\n💰 **Estimated Cost**: {cost}")
        if accessories:
            parts.append(f"\n💍 **Accessories**: {', '.join(accessories)}")
        if alts:
            parts.append("\n🔄 **Alternatives**:")
            for i, alt in enumerate(alts, 1):
                parts.append(f"  {i}. {alt}")

        return "\n".join(parts)


class ProductSearchAgent:
    """Handles product search queries with FashionCLIP + Qdrant."""

    SYSTEM_PROMPT = """You are a fashion product search assistant specializing in Indian fashion.
When a user wants to find products:
1. Extract search parameters: garment type, color, budget range, brand preference
2. Generate a semantic search query optimized for FashionCLIP embeddings
3. Suggest category filters and sort order
4. Recommend complementary items

Respond with JSON:
{
  "search_query": "optimized search text for FashionCLIP",
  "filters": {"category": "...", "min_price": 0, "max_price": 0, "color": "..."},
  "sort_by": "relevance|price_low|price_high|rating",
  "complementary_items": ["...", "..."],
  "response_text": "natural language response to user"
}"""

    def __init__(self, llm: LLMService):
        self._llm = llm

    async def run(self, state: AgentState) -> AgentState:
        params = state.get("extracted_params", {})

        try:
            response = await self._llm.chat_completion(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"User wants: {state['message']}\nExtracted params: {json.dumps(params)}"},
                ],
                temperature=0.3,
                max_tokens=400,
            )

            try:
                text = response.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                search_data = json.loads(text)

                # Execute actual product search
                from app.services.product_search import ProductSearchService
                search_service = ProductSearchService()

                results = await search_service.search(
                    query=search_data.get("search_query", state["message"]),
                    category=search_data.get("filters", {}).get("category"),
                    min_price=search_data.get("filters", {}).get("min_price"),
                    max_price=search_data.get("filters", {}).get("max_price"),
                    limit=10,
                )

                state["products"] = [r.model_dump() if hasattr(r, 'model_dump') else r for r in results] if results else []
                state["agent_response"] = search_data.get("response_text", "Here are the products I found for you!")

                if state["products"]:
                    state["agent_response"] += f"\n\n📦 Found **{len(state['products'])}** matching products."
                else:
                    state["agent_response"] += "\n\n🔍 No exact matches found yet. Try broadening your search or check back soon!"

            except (json.JSONDecodeError, Exception):
                state["agent_response"] = response

            state["suggestions"] = ["Filter by price", "Show more results", "Try a different style"]

        except Exception as e:
            logger.error("Product search agent failed: %s", e)
            state["agent_response"] = "I'll help you find the perfect products. Could you tell me what you're looking for — garment type, budget, or occasion?"
            state["error"] = str(e)

        state["agent_used"] = "product_agent"
        return state


class TailorAgent:
    """Generates detailed tailoring guides with fabric/yardage/construction."""

    SYSTEM_PROMPT = """You are an expert Indian master tailor with 40 years of experience.
You specialize in: saree blouses, lehenga cholis, kurta sets, sherwanis, salwar kameez.

When asked about tailoring, provide:
1. Exact fabric yardage (in meters) with 10% waste buffer
2. Fabric type recommendation with GSM and thread count
3. Step-by-step construction sequence (numbered)
4. Seam allowance specifications (in cm)
5. Interlining/interfacing requirements
6. Iron and pressing instructions
7. Finishing details (hooks, buttons, zippers)
8. Common pitfalls and pro tips

Respond with JSON:
{
  "garment": "...",
  "fabric_recommendation": "...",
  "fabric_gsm": "...",
  "yardage_meters": 0.0,
  "lining_meters": 0.0,
  "interfacing_meters": 0.0,
  "seam_allowance_cm": 1.5,
  "construction_steps": ["1. ...", "2. ...", ...],
  "iron_settings": "...",
  "finishing": "...",
  "pro_tips": ["...", "..."],
  "estimated_tailoring_cost": "₹X,XXX - ₹X,XXX",
  "difficulty_level": "beginner|intermediate|advanced",
  "time_estimate_hours": 0
}"""

    def __init__(self, llm: LLMService):
        self._llm = llm

    async def run(self, state: AgentState) -> AgentState:
        params = state.get("extracted_params", {})

        try:
            response = await self._llm.chat_completion(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"""Tailoring request:
- User message: {state['message']}
- Garment type: {params.get('garment_type', 'not specified')}
- Fabric preference: {params.get('fabric', 'not specified')}
- Occasion: {params.get('occasion', 'general')}
- Body adjustments: {params.get('body_adjustments', 'none')}"""},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            try:
                text = response.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                tailor_data = json.loads(text)

                state["tailoring_data"] = tailor_data
                state["agent_response"] = self._format_tailoring_response(tailor_data)
            except json.JSONDecodeError:
                state["agent_response"] = response

            state["suggestions"] = [
                "📏 Show measurement guide",
                "🧵 Find this fabric online",
                "📄 Generate PDF pattern",
            ]

        except Exception as e:
            logger.error("Tailor agent failed: %s", e)
            state["agent_response"] = "I'll help with tailoring guidance. What garment are you looking to stitch?"
            state["error"] = str(e)

        state["agent_used"] = "tailor_agent"
        return state

    @staticmethod
    def _format_tailoring_response(data: dict) -> str:
        parts = [f"✂️ **Tailoring Guide: {data.get('garment', 'Garment')}**"]
        parts.append(f"\n🧵 **Fabric**: {data.get('fabric_recommendation', 'N/A')} ({data.get('fabric_gsm', 'N/A')})")
        parts.append(f"📐 **Yardage**: {data.get('yardage_meters', 'N/A')}m main + {data.get('lining_meters', 0)}m lining")
        parts.append(f"📏 **Seam Allowance**: {data.get('seam_allowance_cm', 1.5)}cm")

        steps = data.get("construction_steps", [])
        if steps:
            parts.append("\n🔨 **Construction Steps**:")
            for step in steps:
                parts.append(f"  {step}")

        parts.append(f"\n🔥 **Iron Settings**: {data.get('iron_settings', 'Medium heat')}")
        parts.append(f"✅ **Finishing**: {data.get('finishing', 'Standard')}")
        parts.append(f"💰 **Est. Tailoring Cost**: {data.get('estimated_tailoring_cost', 'Varies')}")
        parts.append(f"⏱️ **Time**: ~{data.get('time_estimate_hours', 'N/A')} hours")
        parts.append(f"📊 **Difficulty**: {data.get('difficulty_level', 'intermediate').title()}")

        tips = data.get("pro_tips", [])
        if tips:
            parts.append("\n💡 **Pro Tips**:")
            for tip in tips:
                parts.append(f"  • {tip}")

        return "\n".join(parts)


class StyleAdviceAgent:
    """Provides personalized style recommendations."""

    SYSTEM_PROMPT = """You are an expert Indian fashion stylist with deep knowledge of:
- Regional styles: South Indian (Kanjeevaram, Pochampally), North Indian (Banarasi, Lucknowi)
- Body type dressing: flattering silhouettes for pear, apple, hourglass, rectangle, inverted triangle
- Color theory: skin-tone-based color palettes, seasonal colors
- Occasion dressing: wedding guest, host, office, casual, festival, temple
- Cultural norms: modest dressing, regional expectations, generational preferences
- Current trends: contemporary Indian fashion, fusion wear

Provide specific, actionable advice with exact product suggestions.
Be warm, encouraging, and culturally sensitive.

Format response as helpful paragraphs with emoji headers.
End with 2-3 follow-up suggestion chips."""

    def __init__(self, llm: LLMService):
        self._llm = llm

    async def run(self, state: AgentState) -> AgentState:
        params = state.get("extracted_params", {})
        history = state.get("conversation_history", [])

        context = f"""User's style question: {state['message']}
Known preferences: {json.dumps(params)}
User profile: {json.dumps(state.get('user_profile', {}))}"""

        try:
            messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
            # Include history for continuity
            if history:
                messages.extend(history[-4:])
            messages.append({"role": "user", "content": context})

            response = await self._llm.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=600,
            )

            state["agent_response"] = response
            state["suggestions"] = [
                "🎨 Design an outfit based on this",
                "🛍️ Find matching products",
                "📐 What's my body type?",
            ]

        except Exception as e:
            logger.error("Style agent failed: %s", e)
            state["agent_response"] = "I'd love to help with style advice! Tell me about the occasion, your preferences, or any specific questions."
            state["error"] = str(e)

        state["agent_used"] = "style_agent"
        return state


class GreetingAgent:
    """Handles greeting messages with warm, culturally-appropriate responses."""

    GREETINGS = {
        "en": "Hello! 👋 I'm your AI Fashion Designer. I can help you:\n\n✨ Design custom outfits\n🛍️ Find products to buy\n✂️ Get tailoring guidance\n👗 Manage your wardrobe\n📐 Analyze your body type\n\nWhat would you like to start with?",
        "hi": "नमस्ते! 👋 मैं आपका AI Fashion Designer हूं। मैं आपकी मदद कर सकता/सकती हूं:\n\n✨ Custom outfits design करें\n🛍️ Products ढूंढें\n✂️ Tailoring guidance पाएं\n👗 अपनी wardrobe manage करें\n\nआप किससे शुरू करना चाहेंगे?",
        "te": "నమస్కారం! 👋 నేను మీ AI Fashion Designer ని. నేను మీకు సహాయం చేయగలను:\n\n✨ Custom outfits డిజైన్\n🛍️ Products కనుగొనడం\n✂️ Tailoring guidance\n👗 మీ wardrobe manage చేయడం\n\nమీరు ఏమి మొదలు పెట్టాలనుకుంటున్నారు?",
    }

    async def run(self, state: AgentState) -> AgentState:
        lang = state.get("language", "en")
        state["agent_response"] = self.GREETINGS.get(lang, self.GREETINGS["en"])
        state["suggestions"] = [
            "Design a wedding outfit",
            "Find trendy kurtas under ₹2000",
            "Style advice for my body type",
            "Tailoring tips for saree blouse",
        ]
        state["agent_used"] = "greeting_agent"
        return state


class GeneralAgent:
    """Handles general fashion queries and chitchat."""

    SYSTEM_PROMPT = """You are a friendly, knowledgeable AI fashion assistant specializing in Indian fashion.
You can discuss any fashion topic: trends, history, care tips, fabric knowledge, etc.
Be warm, enthusiastic, and culturally aware. Use appropriate language based on detected input language.
Keep responses concise but informative (3-5 sentences max).
End with a helpful suggestion."""

    def __init__(self, llm: LLMService):
        self._llm = llm

    async def run(self, state: AgentState) -> AgentState:
        try:
            response = await self._llm.chat_completion(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": state["message"]},
                ],
                temperature=0.7,
                max_tokens=400,
            )
            state["agent_response"] = response
        except Exception as e:
            state["agent_response"] = "That's a great question! I'm here to help with anything fashion-related. Could you tell me more?"
            state["error"] = str(e)

        state["suggestions"] = ["Design an outfit", "Find products", "Style advice"]
        state["agent_used"] = "general_agent"
        return state


class FeedbackAgent:
    """Processes user feedback on designs and recommendations."""

    async def run(self, state: AgentState) -> AgentState:
        message = state["message"].lower()

        if any(w in message for w in ["like", "love", "great", "perfect", "amazing", "beautiful"]):
            state["agent_response"] = "I'm glad you love it! 😊 Would you like me to:\n• Generate an image of this design\n• Find similar products to buy\n• Get a tailoring guide for this"
        elif any(w in message for w in ["don't like", "change", "different", "not"]):
            state["agent_response"] = "No problem! Let me know what you'd like to change:\n• Different color scheme\n• Different silhouette\n• More or less embellishment\n• Different occasion style"
        else:
            state["agent_response"] = "Thanks for the feedback! I'll use this to improve my suggestions. What would you like to try next?"

        state["suggestions"] = ["Modify the design", "Try something different", "Show more options"]
        state["agent_used"] = "feedback_agent"
        return state


class BodyScanAgent:
    """Guides users through body scanning / measurement process."""

    async def run(self, state: AgentState) -> AgentState:
        state["agent_response"] = """📸 **Body Profile Setup**

I can help you create a 3D body profile! Here's how:

**Option 1: Photo Scan** (Recommended)
1. Stand in front of a plain wall
2. Take a front-facing photo and a side-view photo
3. Upload both photos through the Avatar tab
4. I'll generate your 3D avatar in ~30 seconds

**Option 2: Manual Measurements**
Enter these measurements:
• Height, Chest/Bust, Waist, Hips
• Shoulder width, Arm length

Your body profile helps me:
✨ Recommend flattering silhouettes
📐 Provide accurate tailoring measurements
👗 Enable virtual try-on

Which option would you prefer?"""

        state["suggestions"] = [
            "📸 Upload photos now",
            "📏 Enter measurements manually",
            "❓ Why do you need this?",
        ]
        state["agent_used"] = "body_scan_agent"
        return state


class VirtualTryOnAgent:
    """Handles virtual try-on requests."""

    async def run(self, state: AgentState) -> AgentState:
        state["agent_response"] = """👗 **Virtual Try-On**

To try on an outfit virtually, I need:

1. **Your body profile** — Upload photos or enter measurements in the Avatar tab
2. **An outfit to try** — Either:
   • A design I generated for you
   • A product from our catalog
   • Upload your own garment photo

I use **Kolors Virtual Try-On** technology to show you how outfits look on your body shape.

Would you like to set up your avatar first, or try on a design?"""

        state["suggestions"] = [
            "Set up my avatar",
            "Try on last design",
            "Upload a garment photo",
        ]
        state["agent_used"] = "tryon_agent"
        return state


class WardrobeAgent:
    """Manages wardrobe queries — listing, adding, outfit suggestions from closet."""

    SYSTEM_PROMPT = """You are a wardrobe management assistant. Help users:
1. Organize their existing clothes by category, color, season
2. Suggest outfits from items they already own
3. Identify wardrobe gaps and essentials they're missing
4. Create capsule wardrobe plans
5. Suggest outfit combinations for specific occasions

Be specific and practical. Reference Indian fashion staples (kurtas, sarees, ethnic sets)
alongside western wear."""

    def __init__(self, llm: LLMService):
        self._llm = llm

    async def run(self, state: AgentState) -> AgentState:
        try:
            response = await self._llm.chat_completion(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": state["message"]},
                ],
                temperature=0.7,
                max_tokens=400,
            )
            state["agent_response"] = response
        except Exception as e:
            state["agent_response"] = "I can help you manage your wardrobe! You can add items via the Wardrobe tab — take a photo or enter details manually."
            state["error"] = str(e)

        state["suggestions"] = [
            "📸 Add an item to wardrobe",
            "👗 Suggest outfit from my closet",
            "📋 Show wardrobe essentials",
        ]
        state["agent_used"] = "wardrobe_agent"
        return state


# ── Master Agent — Graph Orchestrator ────────────────────────────────
class MasterAgent:
    """
    LangGraph-style master agent that orchestrates the full pipeline:
    
        classify_intent → route_to_specialist → synthesize_response
    
    Maintains conversation context across turns and routes to the
    appropriate specialist agent based on detected intent.
    """

    def __init__(self):
        self._llm = LLMService()
        self._classifier = IntentClassifier(self._llm)

        # Initialize specialist agents
        self._agents = {
            "design_agent": DesignAgent(self._llm),
            "product_agent": ProductSearchAgent(self._llm),
            "tailor_agent": TailorAgent(self._llm),
            "style_agent": StyleAdviceAgent(self._llm),
            "greeting_agent": GreetingAgent(),
            "general_agent": GeneralAgent(self._llm),
            "feedback_agent": FeedbackAgent(),
            "body_scan_agent": BodyScanAgent(),
            "tryon_agent": VirtualTryOnAgent(),
            "wardrobe_agent": WardrobeAgent(self._llm),
        }

    async def run(
        self,
        user_id: str,
        session_id: str,
        message: str,
        language: str = "en",
        conversation_history: list[dict] | None = None,
        user_profile: dict | None = None,
    ) -> dict[str, Any]:
        """Execute the full agent graph for a single user turn."""
        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())

        # Initialize state
        state: AgentState = {
            "user_id": user_id,
            "session_id": session_id,
            "message": message,
            "language": language,
            "conversation_history": conversation_history or [],
            "user_profile": user_profile or {},
            "request_id": request_id,
            "intent": "",
            "intent_confidence": 0.0,
            "extracted_params": {},
            "agent_response": "",
            "suggestions": [],
            "outfit_images": [],
            "products": [],
            "tailoring_data": {},
            "processing_time_ms": 0.0,
            "tokens_used": 0,
            "agent_used": "",
            "error": None,
        }

        try:
            # ── Node 1: Classify Intent ──
            classification = await self._classifier.classify(
                message, conversation_history
            )
            state["intent"] = classification["intent"]
            state["intent_confidence"] = classification["confidence"]
            state["extracted_params"] = classification.get("parameters", {})

            # Override language if classifier detected it
            detected_lang = classification.get("language", language)
            if detected_lang in ("en", "hi", "te", "mixed"):
                state["language"] = detected_lang

            logger.info(
                "Intent: %s (%.2f) | Language: %s | Params: %s",
                state["intent"],
                state["intent_confidence"],
                state["language"],
                json.dumps(state["extracted_params"]),
            )

            # ── Node 2: Route to Specialist Agent ──
            intent_enum = Intent(state["intent"]) if state["intent"] in Intent.__members__.values() else Intent.GENERAL_CHAT
            agent_name = AGENT_ROUTES.get(intent_enum, "general_agent")
            agent = self._agents.get(agent_name, self._agents["general_agent"])

            state = await agent.run(state)

        except Exception as e:
            logger.exception("Master agent error: %s", e)
            state["agent_response"] = "I'm here to help! Could you rephrase your question?"
            state["error"] = str(e)
            state["agent_used"] = "error_fallback"

        # ── Compute timing ──
        state["processing_time_ms"] = (time.perf_counter() - start_time) * 1000

        logger.info(
            "Agent: %s | Time: %.0fms | Intent: %s",
            state["agent_used"],
            state["processing_time_ms"],
            state["intent"],
        )

        return {
            "reply": state["agent_response"],
            "intent": state["intent"],
            "confidence": state["intent_confidence"],
            "language": state["language"],
            "suggestions": state["suggestions"],
            "outfit_images": state.get("outfit_images", []),
            "products": state.get("products", []),
            "tailoring_data": state.get("tailoring_data", {}),
            "agent_used": state["agent_used"],
            "request_id": request_id,
            "processing_time_ms": state["processing_time_ms"],
        }


# ── Module-level singleton ───────────────────────────────────────────
_master_agent: MasterAgent | None = None


def get_master_agent() -> MasterAgent:
    """Get or create the singleton master agent."""
    global _master_agent
    if _master_agent is None:
        _master_agent = MasterAgent()
    return _master_agent
