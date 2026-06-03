"""LLM Service — unified interface to Groq, Ollama, and HuggingFace models."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Optional

import httpx
import litellm
from pydantic import BaseModel

from app.config import settings
from app.middleware.circuit_breaker import groq_breaker, ollama_breaker, with_circuit_breaker

logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.set_verbose = False
litellm.drop_params = True


class LLMService:
    """Unified LLM service with triple-mode inference routing.

    Primary: Groq (394 TPS on Llama 70B)
    Secondary: Ollama local (finetuned models)
    Tertiary: HuggingFace Inference API
    """

    # Default models for each provider
    GROQ_MODEL = "groq/llama-3.3-70b-versatile"
    OLLAMA_MODEL = "ollama/llama3.2:3b"
    FALLBACK_MODEL = "ollama/llama3.2:3b"

    def __init__(self) -> None:
        self._groq_api_key = settings.GROQ_API_KEY
        self._ollama_url = settings.OLLAMA_URL

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """Send a chat completion request with automatic fallback.

        Tries Groq first, falls back to Ollama on failure.
        """
        target_model = model or self.GROQ_MODEL

        # Attempt 1: Groq (primary)
        if self._groq_api_key:
            try:
                response = await self._call_groq(messages, target_model, temperature, max_tokens)
                return response
            except Exception as e:
                logger.warning("Groq failed: %s — falling back to Ollama", e)

        # Attempt 2: Ollama (fallback)
        try:
            response = await self._call_ollama(messages, self.OLLAMA_MODEL, temperature, max_tokens)
            return response
        except Exception as e:
            logger.warning("Ollama failed: %s — using hardcoded fallback", e)

        # Attempt 3: Static fallback
        return "I'm currently experiencing high demand. Please try again in a moment."

    async def _call_groq(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call Groq API via LiteLLM."""
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=self._groq_api_key,
        )
        return response.choices[0].message.content

    async def _call_ollama(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call Ollama local API via LiteLLM."""
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_base=self._ollama_url,
        )
        return response.choices[0].message.content

    async def stream_completion(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion response token by token."""
        target_model = model or self.GROQ_MODEL
        try:
            response = await litellm.acompletion(
                model=target_model,
                messages=messages,
                temperature=temperature,
                stream=True,
                api_key=self._groq_api_key,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            logger.warning("Streaming failed: %s", e)
            yield "I'm having trouble right now. Please try again."

    async def classify_intent(self, text: str) -> dict:
        """Classify user intent using the LLM.

        Returns an IntentClassification dict with intent, confidence, and parameters.
        """
        system_prompt = """You are an intent classifier for a fashion AI assistant. 
Classify the user's message into one of these intents:
- greeting: Hello, hi, how are you
- design_request: Design outfit, create look, suggest clothes for occasion
- style_advice: What suits me, fashion tips, color advice
- product_search: Find products, buy, purchase, shop
- body_scan: Take measurements, scan body, upload photo
- virtual_tryon: Try on, see how it looks, preview
- wardrobe_manage: Add to wardrobe, my closet, what I own
- tailoring: Stitch, tailor, fabric, sew
- feedback: I like, I don't like, rate
- general_chat: Everything else

Respond in JSON format: {"intent": "...", "confidence": 0.0-1.0, "parameters": {...}}
Extract parameters like occasion, colors, budget, garment_type where applicable."""

        try:
            response = await self.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=200,
            )
            # Parse JSON from response
            try:
                # Try to extract JSON from response
                json_str = response.strip()
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0]
                result = json.loads(json_str)
                return result
            except json.JSONDecodeError:
                return {"intent": "general_chat", "confidence": 0.5, "parameters": {}}
        except Exception as e:
            logger.exception("Intent classification failed: %s", e)
            return {"intent": "unknown", "confidence": 0.0, "parameters": {}}
