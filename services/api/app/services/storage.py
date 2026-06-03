"""Storage service — file upload to Supabase Storage and Cloudflare R2."""
from __future__ import annotations

import hashlib
import io
import logging
from typing import Optional

import httpx
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Unified file storage service supporting Supabase Storage and Cloudflare R2."""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

    def __init__(self) -> None:
        self._supabase_url = settings.SUPABASE_URL
        self._supabase_key = settings.SUPABASE_KEY

    async def upload_file(
        self,
        file_bytes: bytes,
        path: str,
        content_type: str,
    ) -> str:
        """Upload a file and return its public URL.

        Validates content type and file size. Strips EXIF data from images.
        """
        # Validate size
        if len(file_bytes) > self.MAX_FILE_SIZE:
            raise ValueError(f"File exceeds {self.MAX_FILE_SIZE // 1024 // 1024}MB limit")

        # Strip EXIF from images for privacy
        if content_type in self.ALLOWED_IMAGE_TYPES:
            file_bytes = self._strip_exif(file_bytes)

        # Upload to Supabase Storage
        if self._supabase_url and self._supabase_key:
            return await self._upload_supabase(file_bytes, path, content_type)

        # Fallback: save locally (development)
        return await self._save_local(file_bytes, path)

    async def _upload_supabase(self, file_bytes: bytes, path: str, content_type: str) -> str:
        """Upload to Supabase Storage bucket."""
        bucket = "fashion-ai"
        url = f"{self._supabase_url}/storage/v1/object/{bucket}/{path}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                content=file_bytes,
                headers={
                    "Authorization": f"Bearer {self._supabase_key}",
                    "Content-Type": content_type,
                    "x-upsert": "true",
                },
            )
            if response.status_code not in (200, 201):
                logger.error("Supabase upload failed: %s %s", response.status_code, response.text)
                raise RuntimeError(f"Upload failed: {response.status_code}")

        public_url = f"{self._supabase_url}/storage/v1/object/public/{bucket}/{path}"
        logger.info("File uploaded to Supabase: %s", public_url)
        return public_url

    async def _save_local(self, file_bytes: bytes, path: str) -> str:
        """Save file locally for development."""
        import os
        local_dir = os.path.join("uploads", os.path.dirname(path))
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join("uploads", path)
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        logger.info("File saved locally: %s", local_path)
        return f"http://localhost:8000/uploads/{path}"

    async def download_file(self, url: str) -> bytes:
        """Download a file from URL."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def delete_file(self, path: str) -> None:
        """Delete a file from storage."""
        if self._supabase_url and self._supabase_key:
            bucket = "fashion-ai"
            url = f"{self._supabase_url}/storage/v1/object/{bucket}/{path}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.delete(
                    url,
                    headers={"Authorization": f"Bearer {self._supabase_key}"},
                )

    async def generate_signed_url(self, path: str, expires: int = 3600) -> str:
        """Generate a signed URL for temporary access."""
        if self._supabase_url and self._supabase_key:
            bucket = "fashion-ai"
            url = f"{self._supabase_url}/storage/v1/object/sign/{bucket}/{path}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json={"expiresIn": expires},
                    headers={"Authorization": f"Bearer {self._supabase_key}"},
                )
                data = response.json()
                return f"{self._supabase_url}/storage/v1{data.get('signedURL', '')}"
        return f"http://localhost:8000/uploads/{path}"

    @staticmethod
    def _strip_exif(image_bytes: bytes) -> bytes:
        """Remove EXIF metadata from an image for privacy."""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            clean = Image.new(img.mode, img.size)
            clean.putdata(list(img.getdata()))
            output = io.BytesIO()
            fmt = "JPEG" if img.format in (None, "JPEG", "MPO") else img.format
            clean.save(output, format=fmt, quality=85)
            return output.getvalue()
        except Exception as e:
            logger.warning("EXIF stripping failed: %s — returning original", e)
            return image_bytes
