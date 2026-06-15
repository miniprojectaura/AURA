"""Fashion Brain Agent — Elite AI fashion designer powered by Groq LLM.

Takes user's body profile + style request and generates a complete
personalized outfit design from head to toe.

Uses Groq llama-3.3-70b-versatile with a 2000-word expert system prompt.
Free tier: 30 req/min, no fine-tuning needed.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import litellm

from app.config import settings

logger = logging.getLogger(__name__)

DESIGNER_MODEL = "groq/llama-3.3-70b-versatile"

FASHION_BRAIN_SYSTEM_PROMPT = """You are AURA — an elite AI fashion designer with 25 years of experience in haute couture, ready-to-wear, and Indian traditional fashion. You have deep expertise in:

BODY ANALYSIS:
- Body shape classification (hourglass, pear, apple, rectangle, inverted triangle)
- Proportional dressing to enhance natural body shape
- Color theory matched to skin tone and undertone
- Face shape complementary necklines and accessories

DESIGN PHILOSOPHY:
- Every outfit must flatter the individual's SPECIFIC body measurements
- Color palette must complement their skin tone and undertone
- Silhouettes must enhance their body shape strengths
- Accessories must complement facial features (face shape, hair type)
- Cultural context matters — respect traditions while innovating
- Budget-consciousness — suggest attainable options

YOUR TASK:
Given a user's body profile (measurements, shape, skin tone, facial features) and their style request, design a COMPLETE outfit from head to toe.

OUTPUT FORMAT — Return ONLY a JSON object:
{
  "outfit_name": "<creative name for the outfit>",
  "occasion": "<the occasion this outfit is designed for>",
  "style_category": "<casual/formal/traditional/fusion/party/wedding/office>",
  "color_palette": {
    "primary": "<hex color>",
    "secondary": "<hex color>",
    "accent": "<hex color>",
    "reasoning": "<why these colors work for this skin tone>"
  },
  "garments": [
    {
      "type": "<garment category: headwear/top/bottom/dress/outerwear/footwear/accessory/innerwear/jewelry>",
      "name": "<specific garment name, e.g., 'Mandarin collar silk kurta'>",
      "description": "<detailed description: fabric, cut, fit, length, pattern>",
      "color": "<specific color with hex>",
      "fabric": "<recommended fabric>",
      "fit_notes": "<how this fits their specific body shape>",
      "styling_tip": "<how to wear/style this piece>",
      "estimated_price_inr": <number>,
      "search_keywords": "<comma-separated keywords for shopping>"
    }
  ],
  "hair_suggestion": {
    "style": "<hairstyle recommendation>",
    "reasoning": "<why this works for their face shape and hair type>"
  },
  "makeup_suggestion": {
    "style": "<makeup look recommendation>",
    "key_products": "<lip color, eye look, etc.>",
    "reasoning": "<why this works for their skin tone>"
  },
  "overall_look_description": "<2-3 sentence vivid description of the complete look>",
  "body_shape_advice": "<specific advice for their body shape>",
  "confidence_score": <0.0-1.0>
}

RULES:
1. ALWAYS include garments for: top, bottom (or dress), footwear, at least 2 accessories
2. Every garment MUST have fit_notes specific to their body measurements
3. Color palette MUST complement their skin tone
4. Include hair and makeup suggestions based on facial features
5. Prices in INR (Indian Rupees) — realistic estimates
6. search_keywords should be useful for online shopping
7. Return ONLY the JSON, no markdown or extra text"""


@dataclass
class OutfitDesign:
    """Complete outfit design from the Fashion Brain."""
    outfit_name: str = ""
    occasion: str = ""
    style_category: str = ""
    color_palette: dict = field(default_factory=dict)
    garments: list[dict] = field(default_factory=list)
    hair_suggestion: dict = field(default_factory=dict)
    makeup_suggestion: dict = field(default_factory=dict)
    overall_look_description: str = ""
    body_shape_advice: str = ""
    confidence_score: float = 0.0
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "outfit_name": self.outfit_name,
            "occasion": self.occasion,
            "style_category": self.style_category,
            "color_palette": self.color_palette,
            "garments": self.garments,
            "hair_suggestion": self.hair_suggestion,
            "makeup_suggestion": self.makeup_suggestion,
            "overall_look_description": self.overall_look_description,
            "body_shape_advice": self.body_shape_advice,
            "confidence_score": self.confidence_score,
        }


class FashionBrainService:
    """Elite AI fashion designer agent."""

    def __init__(self):
        self._api_key = settings.GROQ_API_KEY

    async def design_outfit(
        self,
        body_profile: dict,
        prompt: str,
        occasion: Optional[str] = None,
        style_preferences: Optional[list[str]] = None,
    ) -> OutfitDesign:
        """Generate a complete outfit design.

        Args:
            body_profile: User's body measurements, shape, skin tone, etc.
            prompt: User's style request (e.g., "wedding outfit", "casual summer")
            occasion: Optional explicit occasion
            style_preferences: Optional style keywords

        Returns:
            OutfitDesign with complete head-to-toe outfit
        """
        if not self._api_key:
            logger.error("GROQ_API_KEY not set")
            return OutfitDesign(raw_response="API key missing")

        # Build the user message with body context
        user_message = self._build_user_message(
            body_profile, prompt, occasion, style_preferences
        )

        try:
            response = await litellm.acompletion(
                model=DESIGNER_MODEL,
                messages=[
                    {"role": "system", "content": FASHION_BRAIN_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=2000,
                api_key=self._api_key,
            )

            raw_text = response.choices[0].message.content
            logger.info("Fashion Brain response length: %d chars", len(raw_text))

            return self._parse_design(raw_text)

        except Exception as e:
            logger.exception("Fashion Brain failed: %s", e)
            return OutfitDesign(
                outfit_name="Design Generation Failed",
                overall_look_description=f"Sorry, I couldn't generate a design right now. Error: {e}",
                raw_response=str(e),
            )

    def _build_user_message(
        self,
        body_profile: dict,
        prompt: str,
        occasion: Optional[str],
        style_preferences: Optional[list[str]],
    ) -> str:
        """Build the context-rich user message for the LLM."""
        parts = [f"DESIGN REQUEST: {prompt}"]

        if occasion:
            parts.append(f"OCCASION: {occasion}")

        if style_preferences:
            parts.append(f"STYLE PREFERENCES: {', '.join(style_preferences)}")

        # Body profile context
        if body_profile:
            profile_lines = ["", "USER BODY PROFILE:"]
            mappings = {
                "height_cm": "Height",
                "weight_kg": "Weight",
                "chest_cm": "Chest",
                "waist_cm": "Waist",
                "hip_cm": "Hip",
                "shoulder_width_cm": "Shoulder Width",
                "inseam_cm": "Inseam",
                "body_shape": "Body Shape",
                "skin_tone": "Skin Tone",
                "undertone": "Undertone",
                "gender_presentation": "Gender Presentation",
                "age_range": "Age Range",
            }
            for key, label in mappings.items():
                val = body_profile.get(key)
                if val is not None and val != "unknown" and val != "unspecified":
                    unit = " cm" if "cm" in key else (" kg" if "kg" in key else "")
                    profile_lines.append(f"  {label}: {val}{unit}")

            facial = body_profile.get("facial_features", {})
            if facial:
                if facial.get("face_shape", "unknown") != "unknown":
                    profile_lines.append(f"  Face Shape: {facial['face_shape']}")
                if facial.get("hair_type", "unknown") != "unknown":
                    profile_lines.append(f"  Hair Type: {facial['hair_type']}")
                if facial.get("hair_length", "unknown") != "unknown":
                    profile_lines.append(f"  Hair Length: {facial['hair_length']}")

            parts.extend(profile_lines)

        parts.append("")
        parts.append("Design a complete outfit from head to toe for this person.")

        return "\n".join(parts)

    def _parse_design(self, raw_text: str) -> OutfitDesign:
        """Parse LLM response into OutfitDesign."""
        try:
            text = raw_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
            else:
                raise ValueError("No JSON found")

            return OutfitDesign(
                outfit_name=data.get("outfit_name", "Custom Design"),
                occasion=data.get("occasion", ""),
                style_category=data.get("style_category", ""),
                color_palette=data.get("color_palette", {}),
                garments=data.get("garments", []),
                hair_suggestion=data.get("hair_suggestion", {}),
                makeup_suggestion=data.get("makeup_suggestion", {}),
                overall_look_description=data.get("overall_look_description", ""),
                body_shape_advice=data.get("body_shape_advice", ""),
                confidence_score=data.get("confidence_score", 0.5),
                raw_response=raw_text,
            )

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse fashion design JSON: %s", e)
            return OutfitDesign(
                outfit_name="Design Result",
                overall_look_description=raw_text[:500],
                raw_response=raw_text,
                confidence_score=0.2,
            )
