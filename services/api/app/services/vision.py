"""
Vision service for fashion image analysis.

Components:
  • Qwen2.5-VL via HF Inference API – garment analysis & description
  • FashionCLIP – fashion-specific embeddings (512-d)
  • SAM 2 – garment segmentation
  • Skin-tone estimation – from face/hand region pixels
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class FashionAnalysis:
    """Result of full image analysis."""
    description: str
    garment_types: list[str]
    colors: list[str]
    patterns: list[str]
    style: str
    occasion_suitability: list[str]
    fabric_guess: str
    confidence: float
    provider: str
    processing_time_ms: float = 0.0
    raw_response: str = ""


@dataclass
class GarmentSegment:
    """A segmented garment region."""
    label: str
    mask: np.ndarray  # boolean mask H×W
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    area_ratio: float  # fraction of image area


@dataclass
class SkinTone:
    """Estimated skin tone from image."""
    hex_color: str
    rgb: tuple[int, int, int]
    fitzpatrick_type: int  # I–VI
    undertone: str  # warm / cool / neutral
    confidence: float


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HF_VISION_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_VISION_MODEL}"
FASHION_CLIP_MODEL = "patrickjohncyh/fashion-clip"
EMBEDDING_DIM = 512

# Fitzpatrick scale mapping (simplified L* thresholds in CIE-Lab)
_FITZPATRICK_THRESHOLDS = [
    (80, 1),  # I – very light
    (70, 2),  # II – light
    (60, 3),  # III – medium
    (50, 4),  # IV – olive
    (40, 5),  # V – brown
    (0,  6),  # VI – dark
]


# ---------------------------------------------------------------------------
# Vision Service
# ---------------------------------------------------------------------------

class VisionService:
    """
    Computer-vision pipeline for fashion analysis, embedding,
    segmentation, and skin-tone estimation.
    """

    def __init__(
        self,
        hf_token: Optional[str] = None,
        device: str = "cpu",
    ):
        self._hf_token = hf_token or os.getenv("HF_TOKEN", "")
        self._device = device

        # Lazy-loaded models
        self._clip_model: object = None
        self._clip_processor: object = None
        self._sam_predictor: object = None
        self._http: Optional[httpx.AsyncClient] = None

        logger.info("VisionService initialised (device=%s)", device)

    # -- lifecycle ---------------------------------------------------------

    async def connect(self) -> None:
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        # Pre-load FashionCLIP in background
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self._load_fashion_clip)
            logger.info("FashionCLIP loaded")
        except Exception:
            logger.warning("FashionCLIP failed to load", exc_info=True)

    async def disconnect(self) -> None:
        if self._http:
            await self._http.aclose()

    def _load_fashion_clip(self) -> None:
        """Load FashionCLIP model and processor."""
        try:
            from transformers import CLIPModel, CLIPProcessor

            self._clip_processor = CLIPProcessor.from_pretrained(FASHION_CLIP_MODEL)
            self._clip_model = CLIPModel.from_pretrained(FASHION_CLIP_MODEL)
            self._clip_model.eval()  # type: ignore[union-attr]
            if self._device != "cpu":
                self._clip_model.to(self._device)  # type: ignore[union-attr]
        except ImportError:
            raise RuntimeError("transformers is required – pip install transformers")

    def _load_sam(self) -> None:
        """Load SAM 2 predictor."""
        try:
            from segment_anything import sam_model_registry, SamPredictor

            sam_checkpoint = os.getenv("SAM_CHECKPOINT", "sam_vit_h_4b8939.pth")
            model_type = os.getenv("SAM_MODEL_TYPE", "vit_h")
            sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
            sam.to(self._device)
            self._sam_predictor = SamPredictor(sam)
        except (ImportError, FileNotFoundError):
            logger.warning("SAM model unavailable – segmentation will use fallback")

    # -- public API: analyse_image -----------------------------------------

    async def analyze_image(self, image_bytes: bytes) -> FashionAnalysis:
        """
        Analyse a fashion image using Qwen2.5-VL via HF Inference API.

        Falls back to a simpler CLIP-based analysis if the VL model is
        unavailable.
        """
        start = time.perf_counter()

        try:
            result = await self._analyze_hf(image_bytes)
            result.processing_time_ms = (time.perf_counter() - start) * 1000
            return result
        except Exception:
            logger.warning("HF Vision API failed – using CLIP fallback", exc_info=True)

        result = await self._analyze_clip_fallback(image_bytes)
        result.processing_time_ms = (time.perf_counter() - start) * 1000
        return result

    async def _analyze_hf(self, image_bytes: bytes) -> FashionAnalysis:
        """Call Qwen2.5-VL via HF Inference API."""
        import base64

        assert self._http is not None
        b64 = base64.b64encode(image_bytes).decode()

        payload = {
            "inputs": {
                "image": b64,
                "question": (
                    "Analyze this fashion image in detail. Provide: "
                    "1) garment types, 2) colors, 3) patterns, 4) style category, "
                    "5) occasion suitability, 6) likely fabric. "
                    "Format as JSON with keys: garment_types, colors, patterns, "
                    "style, occasions, fabric, description."
                ),
            },
        }
        headers = {"Authorization": f"Bearer {self._hf_token}"}

        resp = await self._http.post(HF_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        # Parse response (HF VL models return free-form text)
        raw_text = ""
        if isinstance(data, list) and data:
            raw_text = data[0].get("generated_text", str(data))
        elif isinstance(data, dict):
            raw_text = data.get("generated_text", str(data))
        else:
            raw_text = str(data)

        return self._parse_analysis(raw_text)

    @staticmethod
    def _parse_analysis(raw_text: str) -> FashionAnalysis:
        """Best-effort parsing of VL model output into structured analysis."""
        import json as _json

        # Try JSON extraction
        try:
            # Find JSON block in response
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = _json.loads(raw_text[start:end])
                return FashionAnalysis(
                    description=parsed.get("description", raw_text[:200]),
                    garment_types=parsed.get("garment_types", []),
                    colors=parsed.get("colors", []),
                    patterns=parsed.get("patterns", []),
                    style=parsed.get("style", "unknown"),
                    occasion_suitability=parsed.get("occasions", []),
                    fabric_guess=parsed.get("fabric", "unknown"),
                    confidence=0.85,
                    provider="hf_qwen_vl",
                    raw_response=raw_text,
                )
        except _json.JSONDecodeError:
            pass

        # Fallback – return raw text as description
        return FashionAnalysis(
            description=raw_text[:500],
            garment_types=[],
            colors=[],
            patterns=[],
            style="unknown",
            occasion_suitability=[],
            fabric_guess="unknown",
            confidence=0.5,
            provider="hf_qwen_vl",
            raw_response=raw_text,
        )

    async def _analyze_clip_fallback(self, image_bytes: bytes) -> FashionAnalysis:
        """Simple CLIP zero-shot classification as fallback."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._clip_classify, image_bytes
        )

    def _clip_classify(self, image_bytes: bytes) -> FashionAnalysis:
        """CLIP zero-shot classification (sync)."""
        if self._clip_model is None or self._clip_processor is None:
            return FashionAnalysis(
                description="Analysis unavailable",
                garment_types=[],
                colors=[],
                patterns=[],
                style="unknown",
                occasion_suitability=[],
                fabric_guess="unknown",
                confidence=0.0,
                provider="none",
            )

        import torch

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        garment_labels = [
            "dress", "t-shirt", "jeans", "saree", "kurta", "jacket",
            "skirt", "blouse", "trousers", "coat", "lehenga", "shirt",
        ]
        style_labels = ["casual", "formal", "traditional", "sporty", "party", "wedding"]
        color_labels = [
            "red", "blue", "green", "black", "white", "yellow",
            "pink", "purple", "orange", "brown", "gold", "silver",
        ]

        def _classify(labels: list[str]) -> list[tuple[str, float]]:
            inputs = self._clip_processor(  # type: ignore[union-attr]
                text=labels, images=img, return_tensors="pt", padding=True
            )
            with torch.no_grad():
                outputs = self._clip_model(**inputs)  # type: ignore[union-attr]
                logits = outputs.logits_per_image[0]
                probs = logits.softmax(dim=-1).cpu().numpy()
            return sorted(
                zip(labels, probs.tolist()), key=lambda x: x[1], reverse=True
            )

        garment_scores = _classify(garment_labels)
        style_scores = _classify(style_labels)
        color_scores = _classify(color_labels)

        return FashionAnalysis(
            description=f"Detected {garment_scores[0][0]} in {color_scores[0][0]}, "
                        f"{style_scores[0][0]} style",
            garment_types=[g[0] for g in garment_scores[:3] if g[1] > 0.1],
            colors=[c[0] for c in color_scores[:3] if c[1] > 0.1],
            patterns=[],
            style=style_scores[0][0],
            occasion_suitability=[],
            fabric_guess="unknown",
            confidence=float(garment_scores[0][1]),
            provider="fashion_clip",
        )

    # -- public API: encode_image ------------------------------------------

    async def encode_image(self, image_bytes: bytes) -> list[float]:
        """
        Generate a FashionCLIP embedding (512-d) for an image.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._encode_sync, image_bytes
        )

    def _encode_sync(self, image_bytes: bytes) -> list[float]:
        """Synchronous CLIP image encoding."""
        if self._clip_model is None or self._clip_processor is None:
            raise RuntimeError("FashionCLIP model not loaded")

        import torch

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        inputs = self._clip_processor(images=img, return_tensors="pt")  # type: ignore[union-attr]

        with torch.no_grad():
            embeds = self._clip_model.get_image_features(**inputs)  # type: ignore[union-attr]
            embeds = embeds / embeds.norm(dim=-1, keepdim=True)

        return embeds[0].cpu().numpy().tolist()

    # -- public API: encode text -------------------------------------------

    async def encode_text(self, text: str) -> list[float]:
        """Generate a FashionCLIP text embedding."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._encode_text_sync, text)

    def _encode_text_sync(self, text: str) -> list[float]:
        if self._clip_model is None or self._clip_processor is None:
            raise RuntimeError("FashionCLIP model not loaded")

        import torch

        inputs = self._clip_processor(text=[text], return_tensors="pt", padding=True)  # type: ignore[union-attr]
        with torch.no_grad():
            embeds = self._clip_model.get_text_features(**inputs)  # type: ignore[union-attr]
            embeds = embeds / embeds.norm(dim=-1, keepdim=True)
        return embeds[0].cpu().numpy().tolist()

    # -- public API: segment_garment ---------------------------------------

    async def segment_garment(self, image_bytes: bytes) -> list[GarmentSegment]:
        """
        Segment garments in the image using SAM 2.

        Falls back to a simple bounding-box approach if SAM is unavailable.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._segment_sync, image_bytes
        )

    def _segment_sync(self, image_bytes: bytes) -> list[GarmentSegment]:
        """Synchronous garment segmentation."""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(img)
        h, w = img_array.shape[:2]
        total_area = h * w

        # Try SAM
        if self._sam_predictor is not None:
            return self._segment_with_sam(img_array, h, w, total_area)

        # Lazy load SAM
        try:
            self._load_sam()
            if self._sam_predictor is not None:
                return self._segment_with_sam(img_array, h, w, total_area)
        except Exception:
            logger.warning("SAM unavailable – using grid-based fallback")

        # Fallback: divide image into regions
        return self._segment_fallback(img_array, h, w, total_area)

    def _segment_with_sam(
        self,
        img_array: np.ndarray,
        h: int,
        w: int,
        total_area: int,
    ) -> list[GarmentSegment]:
        """Segment using SAM predictor with automatic point prompts."""
        self._sam_predictor.set_image(img_array)  # type: ignore[union-attr]

        # Generate a grid of point prompts across the image
        points = np.array([
            [w * 0.5, h * 0.35],  # upper body
            [w * 0.5, h * 0.65],  # lower body
            [w * 0.3, h * 0.5],   # left side
            [w * 0.7, h * 0.5],   # right side
        ])
        labels = np.array([1, 1, 1, 1])

        masks, scores, _ = self._sam_predictor.predict(  # type: ignore[union-attr]
            point_coords=points,
            point_labels=labels,
            multimask_output=True,
        )

        segments: list[GarmentSegment] = []
        region_labels = ["upper_body", "lower_body", "full_body"]
        for i, (mask, score) in enumerate(zip(masks, scores)):
            if score < 0.5:
                continue
            ys, xs = np.where(mask)
            if len(ys) == 0:
                continue
            bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
            label = region_labels[i] if i < len(region_labels) else f"region_{i}"
            segments.append(
                GarmentSegment(
                    label=label,
                    mask=mask,
                    bbox=bbox,
                    confidence=float(score),
                    area_ratio=float(mask.sum()) / total_area,
                )
            )

        return segments

    @staticmethod
    def _segment_fallback(
        img_array: np.ndarray,
        h: int,
        w: int,
        total_area: int,
    ) -> list[GarmentSegment]:
        """Simple region-based fallback when SAM is unavailable."""
        segments = []

        # Upper body region
        upper_mask = np.zeros((h, w), dtype=bool)
        upper_mask[int(h * 0.15) : int(h * 0.55), int(w * 0.2) : int(w * 0.8)] = True
        segments.append(
            GarmentSegment(
                label="upper_body",
                mask=upper_mask,
                bbox=(int(w * 0.2), int(h * 0.15), int(w * 0.8), int(h * 0.55)),
                confidence=0.4,
                area_ratio=float(upper_mask.sum()) / total_area,
            )
        )

        # Lower body region
        lower_mask = np.zeros((h, w), dtype=bool)
        lower_mask[int(h * 0.5) : int(h * 0.95), int(w * 0.2) : int(w * 0.8)] = True
        segments.append(
            GarmentSegment(
                label="lower_body",
                mask=lower_mask,
                bbox=(int(w * 0.2), int(h * 0.5), int(w * 0.8), int(h * 0.95)),
                confidence=0.4,
                area_ratio=float(lower_mask.sum()) / total_area,
            )
        )

        return segments

    # -- public API: estimate_skin_tone ------------------------------------

    async def estimate_skin_tone(self, image_bytes: bytes) -> SkinTone:
        """
        Estimate skin tone from a photo of a person.

        Samples skin-coloured pixels, converts to CIE-Lab for Fitzpatrick
        scale mapping, and determines undertone.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._skin_tone_sync, image_bytes
        )

    def _skin_tone_sync(self, image_bytes: bytes) -> SkinTone:
        """Synchronous skin-tone estimation."""
        from scipy import ndimage

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img, dtype=np.float32)

        # Simple skin-colour detection in normalised RGB space
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        total = r + g + b + 1e-6
        rn, gn = r / total, g / total

        # Skin pixel criteria (relaxed thresholds)
        skin_mask = (
            (rn > 0.3) & (rn < 0.6)
            & (gn > 0.2) & (gn < 0.5)
            & (r > 50) & (g > 30) & (b > 15)
            & (r > g) & (r > b)
            & (np.abs(r - g) > 10)
        )

        # Focus on face region (upper 40% of image, central 60%)
        h, w = skin_mask.shape
        face_mask = np.zeros_like(skin_mask)
        face_mask[
            int(h * 0.05) : int(h * 0.45),
            int(w * 0.2) : int(w * 0.8),
        ] = True
        combined = skin_mask & face_mask

        # Fall back to full skin mask if face region has too few pixels
        if combined.sum() < 100:
            combined = skin_mask

        if combined.sum() < 50:
            # Not enough skin pixels detected
            return SkinTone(
                hex_color="#C8A888",
                rgb=(200, 168, 136),
                fitzpatrick_type=3,
                undertone="neutral",
                confidence=0.2,
            )

        # Compute median skin colour
        skin_pixels = arr[combined]
        median_r = int(np.median(skin_pixels[:, 0]))
        median_g = int(np.median(skin_pixels[:, 1]))
        median_b = int(np.median(skin_pixels[:, 2]))

        hex_color = f"#{median_r:02X}{median_g:02X}{median_b:02X}"

        # Convert to CIE-Lab for Fitzpatrick mapping
        l_star = self._rgb_to_lab_l(median_r, median_g, median_b)

        fitzpatrick = 3
        for threshold, fitz in _FITZPATRICK_THRESHOLDS:
            if l_star >= threshold:
                fitzpatrick = fitz
                break

        # Undertone from a*/b* channels
        undertone = self._determine_undertone(median_r, median_g, median_b)

        return SkinTone(
            hex_color=hex_color,
            rgb=(median_r, median_g, median_b),
            fitzpatrick_type=fitzpatrick,
            undertone=undertone,
            confidence=min(1.0, combined.sum() / 5000),
        )

    @staticmethod
    def _rgb_to_lab_l(r: int, g: int, b: int) -> float:
        """Approximate CIE-Lab L* from sRGB."""
        # Linearize sRGB
        def _lin(c: float) -> float:
            c /= 255.0
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

        rl, gl, bl = _lin(r), _lin(g), _lin(b)
        # Y component (D65 illuminant)
        y = 0.2126 * rl + 0.7152 * gl + 0.0722 * bl
        # L*
        if y > 0.008856:
            return 116 * (y ** (1 / 3)) - 16
        return 903.3 * y

    @staticmethod
    def _determine_undertone(r: int, g: int, b: int) -> str:
        """Classify undertone as warm / cool / neutral."""
        # Warm: higher red/yellow, Cool: higher blue/pink
        warmth = (r - b) / max(r, 1)
        if warmth > 0.2:
            return "warm"
        elif warmth < 0.05:
            return "cool"
        return "neutral"
