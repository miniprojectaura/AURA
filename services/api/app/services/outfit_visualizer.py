"""Outfit Visualizer — generate outfit images via HuggingFace free Inference API.

Takes the outfit design from FashionBrain and generates a visualization image
showing the outfit on a model matching the user's body type.

Uses HuggingFace Inference API (free tier) with FLUX.1-schnell or SDXL.
"""
from __future__ import annotations

import base64
import logging
import os
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Free HuggingFace models for image generation
HF_IMAGE_MODELS = [
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
]
HF_API_BASE = "https://api-inference.huggingface.co/models"


class OutfitVisualizerService:
    """Generate outfit visualization images using HuggingFace free API."""

    def __init__(self):
        self._hf_token = settings.HF_API_KEY or os.getenv("HF_TOKEN", "")
        self._http: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        return self._http

    async def generate_outfit_image(
        self,
        outfit_design: dict,
        body_profile: dict,
    ) -> Optional[str]:
        """Generate an outfit visualization image.

        Args:
            outfit_design: The outfit design from FashionBrain (with garments, colors)
            body_profile: User's body profile (skin tone, body shape, gender)

        Returns:
            Base64-encoded image string, or None if generation fails
        """
        if not self._hf_token:
            logger.warning("HF_API_KEY not set — skipping outfit visualization")
            return None

        prompt = self._build_image_prompt(outfit_design, body_profile)
        logger.info("Generating outfit image with prompt: %s", prompt[:150])

        # Try each model in order
        for model in HF_IMAGE_MODELS:
            try:
                image_b64 = await self._call_hf_model(model, prompt)
                if image_b64:
                    logger.info("Outfit image generated with model: %s", model)
                    return image_b64
            except Exception as e:
                logger.warning("Model %s failed: %s — trying next", model, e)

        logger.error("All image generation models failed")
        return None

    def _build_image_prompt(self, outfit_design: dict, body_profile: dict) -> str:
        """Build a detailed image generation prompt from outfit design."""
        parts = ["Fashion photography, full body shot, studio lighting, high quality"]

        # Body description
        gender = body_profile.get("gender_presentation", "person")
        skin = body_profile.get("skin_tone", "medium")
        shape = body_profile.get("body_shape", "average")
        parts.append(f"{skin} skin {gender} with {shape} body shape")

        # Outfit description
        garments = outfit_design.get("garments", [])
        for g in garments[:5]:  # Limit to avoid token overflow
            name = g.get("name", "")
            color = g.get("color", "")
            fabric = g.get("fabric", "")
            if name:
                desc = name
                if color:
                    desc = f"{color} {desc}"
                if fabric:
                    desc = f"{fabric} {desc}"
                parts.append(f"wearing {desc}")

        # Color palette
        palette = outfit_design.get("color_palette", {})
        if palette.get("primary"):
            parts.append(f"primary color {palette['primary']}")

        # Overall look
        look = outfit_design.get("overall_look_description", "")
        if look:
            parts.append(look[:100])

        # Quality boosters
        parts.append("professional fashion photoshoot, magazine quality, elegant pose")

        return ", ".join(parts)

    async def _call_hf_model(self, model: str, prompt: str) -> Optional[str]:
        """Call HuggingFace Inference API for image generation."""
        client = await self._get_client()
        url = f"{HF_API_BASE}/{model}"

        headers = {
            "Authorization": f"Bearer {self._hf_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "inputs": prompt,
            "parameters": {
                "num_inference_steps": 4 if "schnell" in model.lower() else 25,
                "guidance_scale": 0.0 if "schnell" in model.lower() else 7.5,
                "width": 512,
                "height": 768,
            },
        }

        response = await client.post(url, json=payload, headers=headers)

        if response.status_code == 503:
            # Model loading — wait and retry once
            logger.info("Model %s loading, waiting...", model)
            import asyncio
            await asyncio.sleep(20)
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            logger.warning("HF API returned %d for %s: %s",
                           response.status_code, model, response.text[:200])
            return None

        # Response is raw image bytes
        image_bytes = response.content
        if len(image_bytes) < 1000:
            # Probably an error response, not an image
            logger.warning("Response too small (%d bytes), likely error", len(image_bytes))
            return None

        return base64.b64encode(image_bytes).decode("utf-8")

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()
