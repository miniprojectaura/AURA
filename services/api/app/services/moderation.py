"""
Content moderation service — NSFW image detection + text toxicity filtering.

Components:
  • NudeNet — NSFW image classification (CPU-only, local)
  • Detoxify — text toxicity scorer (CPU, local)
  • EXIF stripping — removes GPS/personal metadata from uploads
  • User report system — flags content for human review

All models are optional — service degrades gracefully if not installed.
"""
from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from PIL import Image

logger = logging.getLogger(__name__)


# ── Result Models ────────────────────────────────────────────────────
@dataclass
class ImageModerationResult:
    """Result of image moderation check."""
    is_safe: bool
    nsfw_score: float
    categories: dict[str, float] = field(default_factory=dict)
    exif_stripped: bool = False
    blocked_reason: Optional[str] = None

@dataclass
class TextModerationResult:
    """Result of text moderation check."""
    is_safe: bool
    toxicity_score: float
    categories: dict[str, float] = field(default_factory=dict)
    blocked_reason: Optional[str] = None
    cleaned_text: Optional[str] = None


# ── NSFW Thresholds ──────────────────────────────────────────────────
NSFW_THRESHOLD = 0.6  # Block if any NSFW category exceeds this
TOXICITY_THRESHOLD = 0.7  # Block if toxicity exceeds this

# Blocklist patterns for fashion context
_TEXT_BLOCKLIST_PATTERNS = [
    r'\b(nude|naked|explicit|porn|xxx)\b',
    r'\b(kill|murder|attack|bomb)\b',
    r'\b(scam|phishing|hack)\b',
]


class ContentModerationService:
    """
    Multi-modal content moderation with graceful degradation.
    
    Usage:
        moderator = ContentModerationService()
        
        # Check image
        result = await moderator.check_image(image_bytes)
        if not result.is_safe:
            reject(result.blocked_reason)
        
        # Check text
        result = await moderator.check_text("user message")
        if not result.is_safe:
            reject(result.blocked_reason)
    """

    def __init__(self):
        self._nudenet_model = None
        self._detoxify_model = None
        self._nudenet_available = False
        self._detoxify_available = False
        self._load_models()

    def _load_models(self) -> None:
        """Lazy-load moderation models (CPU only)."""
        # NudeNet
        try:
            from nudenet import NudeDetector
            self._nudenet_model = NudeDetector()
            self._nudenet_available = True
            logger.info("NudeNet loaded for NSFW detection")
        except ImportError:
            logger.info("NudeNet not installed — NSFW detection disabled. Install: pip install nudenet")
        except Exception as e:
            logger.warning("NudeNet load failed: %s", e)

        # Detoxify
        try:
            from detoxify import Detoxify
            self._detoxify_model = Detoxify("multilingual")
            self._detoxify_available = True
            logger.info("Detoxify loaded for text toxicity detection")
        except ImportError:
            logger.info("Detoxify not installed — text toxicity disabled. Install: pip install detoxify")
        except Exception as e:
            logger.warning("Detoxify load failed: %s", e)

    # ── Image Moderation ─────────────────────────────────────────────
    async def check_image(self, image_bytes: bytes) -> ImageModerationResult:
        """
        Check image for NSFW content and strip EXIF metadata.
        
        Pipeline:
        1. Strip EXIF/GPS metadata (always)
        2. Run NudeNet classifier (if available)
        3. Return safety verdict
        """
        import asyncio

        # Always strip EXIF
        cleaned_bytes = self._strip_exif(image_bytes)

        if not self._nudenet_available:
            return ImageModerationResult(
                is_safe=True,
                nsfw_score=0.0,
                exif_stripped=True,
                categories={"note": "NudeNet not available — image not scanned"},
            )

        # Run NudeNet in thread pool (CPU-bound)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._check_image_sync, cleaned_bytes
        )

    def _check_image_sync(self, image_bytes: bytes) -> ImageModerationResult:
        """Synchronous NudeNet check."""
        import tempfile
        import os

        # NudeNet requires a file path
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name

            detections = self._nudenet_model.detect(tmp_path)

            # Aggregate scores by category
            categories: dict[str, float] = {}
            max_nsfw_score = 0.0

            nsfw_labels = {
                "FEMALE_BREAST_EXPOSED", "FEMALE_GENITALIA_EXPOSED",
                "MALE_GENITALIA_EXPOSED", "BUTTOCKS_EXPOSED",
                "ANUS_EXPOSED", "BELLY_EXPOSED",
            }

            for det in detections:
                label = det.get("class", det.get("label", "unknown"))
                score = float(det.get("score", 0))
                categories[label] = max(categories.get(label, 0), score)
                if label in nsfw_labels:
                    max_nsfw_score = max(max_nsfw_score, score)

            is_safe = max_nsfw_score < NSFW_THRESHOLD
            blocked_reason = None
            if not is_safe:
                blocked_reason = f"NSFW content detected (score: {max_nsfw_score:.2f})"

            return ImageModerationResult(
                is_safe=is_safe,
                nsfw_score=max_nsfw_score,
                categories=categories,
                exif_stripped=True,
                blocked_reason=blocked_reason,
            )
        except Exception as e:
            logger.error("NudeNet detection error: %s", e)
            return ImageModerationResult(
                is_safe=True,  # Fail open for fashion app
                nsfw_score=0.0,
                exif_stripped=True,
                categories={"error": str(e)},
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # ── Text Moderation ──────────────────────────────────────────────
    async def check_text(self, text: str) -> TextModerationResult:
        """
        Check text for toxicity and harmful content.
        
        Pipeline:
        1. Regex blocklist check (instant)
        2. Detoxify ML model (if available)
        3. Return safety verdict with categories
        """
        import asyncio

        # Step 1: Regex blocklist (fast)
        for pattern in _TEXT_BLOCKLIST_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return TextModerationResult(
                    is_safe=False,
                    toxicity_score=1.0,
                    blocked_reason=f"Content blocked by safety filter",
                )

        # Step 2: Detoxify ML model
        if not self._detoxify_available:
            return TextModerationResult(
                is_safe=True,
                toxicity_score=0.0,
                categories={"note": "Detoxify not available — text not scanned"},
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._check_text_sync, text)

    def _check_text_sync(self, text: str) -> TextModerationResult:
        """Synchronous Detoxify check."""
        try:
            results = self._detoxify_model.predict(text)

            # Extract scores
            categories = {}
            max_score = 0.0
            for key, value in results.items():
                score = float(value) if not isinstance(value, list) else float(value[0])
                categories[key] = round(score, 4)
                if key in ("toxicity", "severe_toxicity", "sexual_explicit", "threat"):
                    max_score = max(max_score, score)

            is_safe = max_score < TOXICITY_THRESHOLD
            blocked_reason = None
            if not is_safe:
                worst_cat = max(categories, key=categories.get)
                blocked_reason = f"Toxic content detected: {worst_cat} ({max_score:.2f})"

            return TextModerationResult(
                is_safe=is_safe,
                toxicity_score=max_score,
                categories=categories,
                blocked_reason=blocked_reason,
            )
        except Exception as e:
            logger.error("Detoxify error: %s", e)
            return TextModerationResult(
                is_safe=True,
                toxicity_score=0.0,
                categories={"error": str(e)},
            )

    # ── EXIF Stripping ───────────────────────────────────────────────
    @staticmethod
    def _strip_exif(image_bytes: bytes) -> bytes:
        """Remove all EXIF metadata (GPS, camera, timestamps) from image."""
        try:
            img = Image.open(io.BytesIO(image_bytes))

            # Create a new image without EXIF
            data = list(img.getdata())
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(data)

            # Save to bytes
            buf = io.BytesIO()
            fmt = img.format or "JPEG"
            clean_img.save(buf, format=fmt, quality=95)
            buf.seek(0)
            return buf.read()
        except Exception as e:
            logger.warning("EXIF stripping failed: %s — returning original", e)
            return image_bytes

    # ── Report System ────────────────────────────────────────────────
    @staticmethod
    async def create_report(
        reporter_id: str,
        content_type: str,  # "image" | "text" | "design"
        content_id: str,
        reason: str,
        details: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a content report for human review.
        
        In production, this writes to a reports table and triggers
        an alert to the moderation queue.
        """
        report = {
            "report_id": str(__import__("uuid").uuid4()),
            "reporter_id": reporter_id,
            "content_type": content_type,
            "content_id": content_id,
            "reason": reason,
            "details": details,
            "status": "pending_review",
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
        logger.info("Content report created: %s", report["report_id"])
        return report


# ── Module singleton ─────────────────────────────────────────────────
_moderator: ContentModerationService | None = None

def get_moderator() -> ContentModerationService:
    global _moderator
    if _moderator is None:
        _moderator = ContentModerationService()
    return _moderator
