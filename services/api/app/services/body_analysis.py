"""Body Analysis Service — extract measurements from photo using Groq Vision LLM.

Pipeline:
  1. User uploads a full-body photo
  2. Groq Vision (llama-3.2-11b-vision) analyzes the photo
  3. Returns: estimated measurements, body shape, skin tone, facial features
  4. Results stored in BodyProfile DB model

No GPU required — uses cloud Groq API (free tier: 30 req/min).
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from typing import Optional

import litellm

from app.config import settings

logger = logging.getLogger(__name__)

# Groq Vision model (free tier)
VISION_MODEL = "groq/llama-3.2-11b-vision-preview"


@dataclass
class BodyAnalysisResult:
    """Structured result from body photo analysis."""
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    chest_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    shoulder_width_cm: Optional[float] = None
    inseam_cm: Optional[float] = None
    body_shape: str = "unknown"
    skin_tone: str = "medium"
    skin_tone_hex: str = "#C8A888"
    fitzpatrick_type: int = 3
    undertone: str = "neutral"
    facial_features: dict = None
    gender_presentation: str = "unspecified"
    age_range: str = "adult"
    confidence: float = 0.0
    raw_analysis: str = ""

    def __post_init__(self):
        if self.facial_features is None:
            self.facial_features = {}

    def to_dict(self) -> dict:
        return {
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "chest_cm": self.chest_cm,
            "waist_cm": self.waist_cm,
            "hip_cm": self.hip_cm,
            "shoulder_width_cm": self.shoulder_width_cm,
            "inseam_cm": self.inseam_cm,
            "body_shape": self.body_shape,
            "skin_tone": self.skin_tone,
            "skin_tone_hex": self.skin_tone_hex,
            "fitzpatrick_type": self.fitzpatrick_type,
            "undertone": self.undertone,
            "facial_features": self.facial_features,
            "gender_presentation": self.gender_presentation,
            "age_range": self.age_range,
            "confidence": self.confidence,
        }


# Body shape classification from measurements
def classify_body_shape(
    chest: Optional[float],
    waist: Optional[float],
    hip: Optional[float],
    shoulder: Optional[float],
) -> str:
    """Rule-based body shape classification from measurements."""
    if not all([chest, waist, hip]):
        return "unknown"

    waist_hip = waist / hip if hip else 1.0
    chest_hip = chest / hip if hip else 1.0
    shoulder_hip = shoulder / hip if shoulder and hip else 1.0

    # Classification rules (standard fashion industry)
    if waist_hip <= 0.75 and abs(chest_hip - 1.0) < 0.05:
        return "hourglass"
    elif hip > chest * 1.05 and waist_hip < 0.8:
        return "pear"
    elif chest > hip * 1.05 and waist > hip * 0.9:
        return "apple"
    elif shoulder_hip > 1.1 and waist_hip > 0.8:
        return "inverted_triangle"
    else:
        return "rectangle"


ANALYSIS_PROMPT = """You are an expert body measurement analyst. Analyze this full-body photo and provide ESTIMATED body measurements and characteristics.

IMPORTANT: These are ESTIMATES for fashion/clothing purposes, not medical measurements. Provide your best reasonable guess based on visual proportions.

Return a JSON object with EXACTLY this structure (all measurements in centimeters):
{
  "height_cm": <number 140-210>,
  "weight_kg": <number 35-150>,
  "chest_cm": <number 60-140>,
  "waist_cm": <number 55-130>,
  "hip_cm": <number 65-140>,
  "shoulder_width_cm": <number 30-60>,
  "inseam_cm": <number 60-95>,
  "skin_tone": "<fair/light/medium/olive/tan/brown/dark>",
  "undertone": "<warm/cool/neutral>",
  "gender_presentation": "<male/female/androgynous>",
  "age_range": "<teen/young_adult/adult/middle_aged/senior>",
  "face_shape": "<oval/round/square/heart/oblong/diamond>",
  "hair_type": "<straight/wavy/curly/coily>",
  "hair_length": "<short/medium/long>",
  "confidence": <0.0-1.0 how confident you are>
}

Rules:
- Return ONLY the JSON object, no other text
- Use reasonable estimates based on visible proportions
- If the photo is unclear, still provide best estimates with lower confidence
- If no person is visible, return all null values with confidence 0.0"""


class BodyAnalysisService:
    """Analyze body photos using Groq Vision LLM."""

    def __init__(self):
        self._api_key = settings.GROQ_API_KEY

    async def analyze_photo(self, photo_bytes: bytes) -> BodyAnalysisResult:
        """Analyze a full-body photo and extract measurements.

        Args:
            photo_bytes: Raw image bytes (JPEG/PNG/WebP)

        Returns:
            BodyAnalysisResult with estimated measurements
        """
        if not self._api_key:
            logger.error("GROQ_API_KEY not set — cannot analyze photo")
            return BodyAnalysisResult(confidence=0.0, raw_analysis="API key missing")

        try:
            b64_image = base64.b64encode(photo_bytes).decode("utf-8")

            response = await litellm.acompletion(
                model=VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": ANALYSIS_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64_image}",
                                },
                            },
                        ],
                    }
                ],
                temperature=0.1,
                max_tokens=800,
                api_key=self._api_key,
            )

            raw_text = response.choices[0].message.content
            logger.info("Body analysis raw response: %s", raw_text[:200])

            return self._parse_response(raw_text)

        except Exception as e:
            logger.exception("Body analysis failed: %s", e)
            return BodyAnalysisResult(
                confidence=0.0,
                raw_analysis=f"Analysis failed: {e}",
            )

    def _parse_response(self, raw_text: str) -> BodyAnalysisResult:
        """Parse Groq Vision response into structured result."""
        try:
            # Extract JSON from response
            text = raw_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            # Find JSON object
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
            else:
                raise ValueError("No JSON found in response")

            # Extract facial features
            facial_features = {
                "face_shape": data.get("face_shape", "unknown"),
                "hair_type": data.get("hair_type", "unknown"),
                "hair_length": data.get("hair_length", "unknown"),
            }

            # Classify body shape from measurements
            body_shape = classify_body_shape(
                data.get("chest_cm"),
                data.get("waist_cm"),
                data.get("hip_cm"),
                data.get("shoulder_width_cm"),
            )

            return BodyAnalysisResult(
                height_cm=data.get("height_cm"),
                weight_kg=data.get("weight_kg"),
                chest_cm=data.get("chest_cm"),
                waist_cm=data.get("waist_cm"),
                hip_cm=data.get("hip_cm"),
                shoulder_width_cm=data.get("shoulder_width_cm"),
                inseam_cm=data.get("inseam_cm"),
                body_shape=body_shape,
                skin_tone=data.get("skin_tone", "medium"),
                undertone=data.get("undertone", "neutral"),
                gender_presentation=data.get("gender_presentation", "unspecified"),
                age_range=data.get("age_range", "adult"),
                facial_features=facial_features,
                confidence=data.get("confidence", 0.5),
                raw_analysis=raw_text,
            )

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse body analysis JSON: %s", e)
            return BodyAnalysisResult(
                confidence=0.1,
                raw_analysis=raw_text,
            )

    async def analyze_with_skin_tone(self, photo_bytes: bytes) -> BodyAnalysisResult:
        """Analyze photo with enhanced skin tone using vision.py fallback."""
        result = await self.analyze_photo(photo_bytes)

        # Enhance skin tone with existing VisionService if available
        try:
            from app.services.vision import VisionService
            vision = VisionService()
            skin = vision._skin_tone_sync(photo_bytes)
            result.skin_tone_hex = skin.hex_color
            result.fitzpatrick_type = skin.fitzpatrick_type
            result.undertone = skin.undertone
        except Exception as e:
            logger.warning("Enhanced skin tone failed, using LLM estimate: %s", e)

        return result
