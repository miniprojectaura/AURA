"""
TTS (Text-to-Speech) service.

Primary:  Kokoro-82M via local inference
Fallback: gTTS (Google Text-to-Speech)
Output:   24 kHz WAV (mono, 16-bit PCM)
Languages: English (en), Hindi (hi), Telugu (te)
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import os
import struct
import time
import wave
from collections import OrderedDict
from threading import Lock
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OUTPUT_SAMPLE_RATE = 24_000
MAX_TEXT_LENGTH = 2000
CACHE_MAX_SIZE = 256  # number of cached phrases

VOICE_MAP = {
    "en": {"default": "af_heart", "male": "am_adam", "female": "af_heart"},
    "hi": {"default": "hf_alpha", "male": "hm_alpha", "female": "hf_alpha"},
    "te": {"default": "tf_alpha", "male": "tm_alpha", "female": "tf_alpha"},
}


class TTSError(Exception):
    """Base exception for TTS operations."""


# ---------------------------------------------------------------------------
# Phrase cache (LRU)
# ---------------------------------------------------------------------------

class _PhraseCache:
    """Thread-safe LRU cache for frequently synthesized phrases."""

    def __init__(self, max_size: int = CACHE_MAX_SIZE):
        self._max_size = max_size
        self._store: OrderedDict[str, bytes] = OrderedDict()
        self._lock = Lock()

    @staticmethod
    def _key(text: str, language: str, voice: str) -> str:
        raw = f"{language}:{voice}:{text}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, text: str, language: str, voice: str) -> Optional[bytes]:
        key = self._key(text, language, voice)
        with self._lock:
            val = self._store.get(key)
            if val is not None:
                self._store.move_to_end(key)
            return val

    def put(self, text: str, language: str, voice: str, audio: bytes) -> None:
        key = self._key(text, language, voice)
        with self._lock:
            self._store[key] = audio
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)


# ---------------------------------------------------------------------------
# WAV helper
# ---------------------------------------------------------------------------

def _numpy_to_wav(samples: np.ndarray, sample_rate: int = OUTPUT_SAMPLE_RATE) -> bytes:
    """Convert float32 numpy array to 16-bit PCM WAV bytes."""
    # Clip and convert
    samples = np.clip(samples, -1.0, 1.0)
    pcm = (samples * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


# ---------------------------------------------------------------------------
# TTS Service
# ---------------------------------------------------------------------------

class TTSService:
    """
    Text-to-speech with Kokoro-82M primary, gTTS fallback.

    Results are cached in an LRU phrase cache to avoid re-synthesizing
    frequently requested texts (e.g. greeting phrases).
    """

    def __init__(
        self,
        kokoro_model_path: Optional[str] = None,
        device: str = "cpu",
    ):
        self._kokoro_model_path = kokoro_model_path or os.getenv(
            "KOKORO_MODEL_PATH", "kokoro-82m"
        )
        self._device = device
        self._kokoro_pipeline: object = None
        self._kokoro_available = False
        self._cache = _PhraseCache()
        logger.info("TTSService initialised (device=%s)", device)

    # -- lifecycle ---------------------------------------------------------

    async def connect(self) -> None:
        """Attempt to load Kokoro-82M model."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self._load_kokoro)
            self._kokoro_available = True
            logger.info("Kokoro-82M loaded successfully")
        except Exception:
            self._kokoro_available = False
            logger.warning(
                "Kokoro-82M unavailable – will use gTTS fallback", exc_info=True
            )

    async def disconnect(self) -> None:
        self._kokoro_pipeline = None
        logger.info("TTSService disconnected")

    def _load_kokoro(self) -> None:
        """Load the Kokoro-82M pipeline synchronously."""
        try:
            from kokoro import KPipeline

            self._kokoro_pipeline = KPipeline(lang_code="a", device=self._device)
        except ImportError:
            raise RuntimeError(
                "kokoro package not installed. Install with: pip install kokoro"
            )

    # -- public API --------------------------------------------------------

    async def synthesize_speech(
        self,
        text: str,
        language: str = "en",
        voice: str = "default",
    ) -> bytes:
        """
        Synthesize *text* to 24 kHz WAV audio bytes.

        Returns cached audio if the same text/language/voice was recently
        synthesized.
        """
        if not text or not text.strip():
            raise TTSError("Text must not be empty")
        if len(text) > MAX_TEXT_LENGTH:
            raise TTSError(
                f"Text length {len(text)} exceeds max {MAX_TEXT_LENGTH}"
            )

        # Resolve voice name
        lang_voices = VOICE_MAP.get(language, VOICE_MAP["en"])
        voice_id = lang_voices.get(voice, lang_voices["default"])

        # Check cache
        cached = self._cache.get(text, language, voice_id)
        if cached is not None:
            logger.debug("TTS cache HIT for text hash")
            return cached

        start = time.perf_counter()

        # Try Kokoro first
        if self._kokoro_available:
            try:
                audio = await self._synthesize_kokoro(text, language, voice_id)
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(
                    "Kokoro TTS: %d chars → %d bytes in %.0f ms",
                    len(text),
                    len(audio),
                    elapsed,
                )
                self._cache.put(text, language, voice_id, audio)
                return audio
            except Exception:
                logger.warning("Kokoro synthesis failed – falling back to gTTS", exc_info=True)

        # Fallback to gTTS
        audio = await self._synthesize_gtts(text, language)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "gTTS fallback: %d chars → %d bytes in %.0f ms",
            len(text),
            len(audio),
            elapsed,
        )
        self._cache.put(text, language, voice_id, audio)
        return audio

    # -- Kokoro-82M --------------------------------------------------------

    async def _synthesize_kokoro(
        self, text: str, language: str, voice_id: str
    ) -> bytes:
        """Run Kokoro-82M in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._kokoro_sync, text, language, voice_id
        )

    def _kokoro_sync(self, text: str, language: str, voice_id: str) -> bytes:
        """Synchronous Kokoro synthesis."""
        assert self._kokoro_pipeline is not None

        # Map language to Kokoro lang_code
        lang_code_map = {"en": "a", "hi": "h", "te": "t"}
        lang_code = lang_code_map.get(language, "a")

        # Generate audio chunks and concatenate
        all_samples: list[np.ndarray] = []
        for _, _, audio_chunk in self._kokoro_pipeline(  # type: ignore[union-attr]
            text, voice=voice_id, speed=1.0, lang=lang_code
        ):
            if audio_chunk is not None:
                all_samples.append(audio_chunk)

        if not all_samples:
            raise TTSError("Kokoro produced no audio output")

        combined = np.concatenate(all_samples)
        return _numpy_to_wav(combined, sample_rate=OUTPUT_SAMPLE_RATE)

    # -- gTTS fallback -----------------------------------------------------

    async def _synthesize_gtts(self, text: str, language: str) -> bytes:
        """Fallback synthesis using Google TTS (requires internet)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._gtts_sync, text, language
        )

    def _gtts_sync(self, text: str, language: str) -> bytes:
        """Synchronous gTTS synthesis."""
        try:
            from gtts import gTTS
        except ImportError:
            raise TTSError(
                "gTTS not installed. Install with: pip install gTTS"
            )

        # gTTS language codes
        gtts_lang_map = {"en": "en", "hi": "hi", "te": "te"}
        lang = gtts_lang_map.get(language, "en")

        mp3_buf = io.BytesIO()
        tts = gTTS(text=text, lang=lang)
        tts.write_to_fp(mp3_buf)
        mp3_buf.seek(0)

        # Convert MP3 → WAV at 24 kHz
        return self._mp3_to_wav(mp3_buf.read())

    @staticmethod
    def _mp3_to_wav(mp3_bytes: bytes) -> bytes:
        """Convert MP3 bytes to 24 kHz 16-bit PCM WAV."""
        try:
            import soundfile as sf
            from scipy.signal import resample_poly
            from math import gcd

            # soundfile can read MP3 with libsndfile >= 1.1
            data, sr = sf.read(io.BytesIO(mp3_bytes), dtype="float32")
            if data.ndim > 1:
                data = data.mean(axis=1)

            if sr != OUTPUT_SAMPLE_RATE:
                g = gcd(sr, OUTPUT_SAMPLE_RATE)
                up = OUTPUT_SAMPLE_RATE // g
                down = sr // g
                data = resample_poly(data, up, down).astype(np.float32)

            return _numpy_to_wav(data, OUTPUT_SAMPLE_RATE)
        except Exception:
            logger.warning(
                "MP3→WAV conversion failed – returning raw MP3", exc_info=True
            )
            return mp3_bytes
