"""
ASR (Automatic Speech Recognition) service.

Primary:  Hugging Face Inference API → Whisper Large v3
Fallback: Local faster-whisper
Features: circuit breaker, exponential-backoff retries, language detection,
           automatic resampling to 16 kHz mono WAV.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import struct
import time
import wave
from dataclasses import dataclass, field
from typing import Optional

import httpx
import numpy as np
import pybreaker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TranscriptionResult:
    """Structured result from ASR."""
    text: str
    language: str  # ISO 639-1
    confidence: float
    duration_seconds: float
    provider: str  # "hf_whisper" | "faster_whisper"
    processing_time_ms: float
    segments: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HF_API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
SUPPORTED_LANGUAGES = {"en", "hi", "te"}  # English, Hindi, Telugu
TARGET_SAMPLE_RATE = 16_000
MAX_AUDIO_DURATION_SECONDS = 120  # 2 minutes


# ---------------------------------------------------------------------------
# Circuit breaker for HF API
# ---------------------------------------------------------------------------
_hf_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=60,
    name="hf_whisper_asr",
)


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _read_wav_info(audio_bytes: bytes) -> tuple[int, int, int]:
    """Return (sample_rate, channels, sample_width) from WAV header."""
    with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
        return wf.getframerate(), wf.getnchannels(), wf.getsampwidth()


def _convert_to_16khz_mono_wav(audio_bytes: bytes, source_format: str = "wav") -> bytes:
    """
    Ensure audio is 16 kHz, mono, 16-bit PCM WAV.

    Uses scipy for resampling when the input rate differs from 16 kHz.
    For non-WAV formats the raw bytes are written and processed via soundfile.
    """
    try:
        import soundfile as sf
        from scipy.signal import resample_poly
        from math import gcd

        # Read audio with soundfile (handles wav, flac, ogg, etc.)
        data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")

        # Convert to mono if stereo
        if data.ndim > 1:
            data = data.mean(axis=1)

        # Resample if necessary
        if sr != TARGET_SAMPLE_RATE:
            g = gcd(sr, TARGET_SAMPLE_RATE)
            up = TARGET_SAMPLE_RATE // g
            down = sr // g
            data = resample_poly(data, up, down).astype(np.float32)

        # Write to 16-bit PCM WAV
        buf = io.BytesIO()
        sf.write(buf, data, TARGET_SAMPLE_RATE, format="WAV", subtype="PCM_16")
        buf.seek(0)
        return buf.read()

    except Exception:
        logger.warning(
            "Audio conversion failed – returning raw bytes", exc_info=True
        )
        return audio_bytes


def _audio_duration(wav_bytes: bytes) -> float:
    """Duration in seconds of a WAV file."""
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / rate if rate > 0 else 0.0
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# ASR Service
# ---------------------------------------------------------------------------

class ASRService:
    """Automatic Speech Recognition with HF Whisper + local fallback."""

    def __init__(
        self,
        hf_token: Optional[str] = None,
        local_model_size: str = "large-v3",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self._hf_token = hf_token or os.getenv("HF_TOKEN", "")
        self._local_model_size = local_model_size
        self._device = device
        self._compute_type = compute_type
        self._local_model: object = None  # Lazy-loaded faster-whisper model
        self._http: Optional[httpx.AsyncClient] = None
        logger.info("ASRService initialised (device=%s)", device)

    # -- lifecycle ---------------------------------------------------------

    async def connect(self) -> None:
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(120.0))

    async def disconnect(self) -> None:
        if self._http:
            await self._http.aclose()

    # -- public API --------------------------------------------------------

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        format: str = "wav",
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.

        1. Convert to 16 kHz mono WAV
        2. Try HF Inference API (circuit-breaker protected)
        3. On failure, fall back to local faster-whisper
        """
        start = time.perf_counter()

        # Pre-process audio
        wav_bytes = _convert_to_16khz_mono_wav(audio_bytes, source_format=format)
        duration = _audio_duration(wav_bytes)

        if duration > MAX_AUDIO_DURATION_SECONDS:
            raise ValueError(
                f"Audio duration {duration:.1f}s exceeds max {MAX_AUDIO_DURATION_SECONDS}s"
            )

        logger.info("Transcribing audio: %.1fs, %d bytes", duration, len(wav_bytes))

        # Attempt HF API first
        try:
            result = await self._transcribe_hf(wav_bytes, duration)
            result.processing_time_ms = (time.perf_counter() - start) * 1000
            return result
        except (pybreaker.CircuitBreakerError, Exception) as exc:
            logger.warning("HF Whisper failed (%s), falling back to local", exc)

        # Fallback to local faster-whisper
        result = await self._transcribe_local(wav_bytes, duration)
        result.processing_time_ms = (time.perf_counter() - start) * 1000
        return result

    # -- HF Inference API --------------------------------------------------

    async def _transcribe_hf(
        self, wav_bytes: bytes, duration: float
    ) -> TranscriptionResult:
        """Call Hugging Face Inference API with circuit breaker + retries."""

        @_hf_breaker
        async def _call() -> TranscriptionResult:
            return await self._hf_request(wav_bytes, duration)

        # Exponential backoff retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await _call()
            except pybreaker.CircuitBreakerError:
                raise
            except Exception as exc:
                if attempt == max_retries - 1:
                    raise
                wait = (2 ** attempt) + 0.5
                logger.warning(
                    "HF Whisper attempt %d/%d failed: %s – retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)

        raise RuntimeError("HF Whisper: all retries exhausted")

    async def _hf_request(
        self, wav_bytes: bytes, duration: float
    ) -> TranscriptionResult:
        """Raw HF API request."""
        if self._http is None:
            await self.connect()
        assert self._http is not None

        headers = {"Authorization": f"Bearer {self._hf_token}"}
        resp = await self._http.post(
            HF_API_URL,
            content=wav_bytes,
            headers=headers,
        )

        if resp.status_code == 503:
            # Model loading
            body = resp.json()
            estimated = body.get("estimated_time", 30)
            logger.info("HF model loading – waiting %.0fs", estimated)
            await asyncio.sleep(min(estimated, 60))
            resp = await self._http.post(
                HF_API_URL, content=wav_bytes, headers=headers
            )

        resp.raise_for_status()
        data = resp.json()

        text: str = data.get("text", "").strip()
        language = self._detect_language(text)

        return TranscriptionResult(
            text=text,
            language=language,
            confidence=0.95,  # HF API doesn't return per-word confidence
            duration_seconds=duration,
            provider="hf_whisper",
            processing_time_ms=0.0,
        )

    # -- Local faster-whisper fallback -------------------------------------

    async def _transcribe_local(
        self, wav_bytes: bytes, duration: float
    ) -> TranscriptionResult:
        """Run faster-whisper locally in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._transcribe_local_sync, wav_bytes, duration
        )

    def _transcribe_local_sync(
        self, wav_bytes: bytes, duration: float
    ) -> TranscriptionResult:
        """Synchronous local transcription."""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            logger.error("faster-whisper not installed – cannot fall back")
            raise RuntimeError(
                "faster-whisper is not installed. "
                "Install with: pip install faster-whisper"
            )

        if self._local_model is None:
            logger.info(
                "Loading faster-whisper model %s on %s",
                self._local_model_size,
                self._device,
            )
            self._local_model = WhisperModel(
                self._local_model_size,
                device=self._device,
                compute_type=self._compute_type,
            )

        import soundfile as sf

        data, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)

        segments_iter, info = self._local_model.transcribe(  # type: ignore[union-attr]
            data,
            beam_size=5,
            language=None,  # auto-detect
            vad_filter=True,
        )

        segments_list = list(segments_iter)
        full_text = " ".join(seg.text.strip() for seg in segments_list)
        detected_lang = info.language if info.language in SUPPORTED_LANGUAGES else "en"
        avg_confidence = (
            sum(seg.avg_logprob for seg in segments_list) / len(segments_list)
            if segments_list
            else 0.0
        )
        # Convert logprob to pseudo-probability
        import math

        confidence = min(1.0, max(0.0, math.exp(avg_confidence)))

        return TranscriptionResult(
            text=full_text,
            language=detected_lang,
            confidence=confidence,
            duration_seconds=duration,
            provider="faster_whisper",
            processing_time_ms=0.0,
            segments=[
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                }
                for seg in segments_list
            ],
        )

    # -- Language detection ------------------------------------------------

    @staticmethod
    def _detect_language(text: str) -> str:
        """
        Simple script-based language detection for Telugu / Hindi / English.

        Telugu: Unicode block U+0C00–U+0C7F
        Hindi (Devanagari): Unicode block U+0900–U+097F
        """
        if not text:
            return "en"

        telugu_chars = sum(1 for ch in text if "\u0C00" <= ch <= "\u0C7F")
        hindi_chars = sum(1 for ch in text if "\u0900" <= ch <= "\u097F")
        total = len(text.replace(" ", "")) or 1

        if telugu_chars / total > 0.3:
            return "te"
        if hindi_chars / total > 0.3:
            return "hi"
        return "en"
