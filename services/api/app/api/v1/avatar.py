"""Avatar endpoints — photo upload, body reconstruction, and mesh retrieval."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_active_user
from app.database import get_db
from app.models.user import BodyProfile, User
from app.schemas.user import BodyProfileCreate, BodyProfileResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Max upload size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/upload-photos", status_code=status.HTTP_202_ACCEPTED)
async def upload_photos(
    front_photo: UploadFile = File(...),
    side_photo: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload front and side photos for body reconstruction.

    Photos are validated for type and size, then stored in Supabase Storage.
    Body reconstruction is triggered as an async Celery task.
    """
    for photo, label in [(front_photo, "front"), (side_photo, "side")]:
        if photo.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{label} photo must be JPEG, PNG, or WebP",
            )
        contents = await photo.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{label} photo exceeds 10MB limit",
            )
        await photo.seek(0)

    # Store photos via storage service
    try:
        from app.services.storage import StorageService
        storage = StorageService()
        front_bytes = await front_photo.read()
        side_bytes = await side_photo.read()
        front_url = await storage.upload_file(
            front_bytes,
            f"avatars/{current_user.id}/front.jpg",
            front_photo.content_type,
        )
        side_url = await storage.upload_file(
            side_bytes,
            f"avatars/{current_user.id}/side.jpg",
            side_photo.content_type,
        )
    except Exception as e:
        logger.exception("Photo upload failed")
        raise HTTPException(status_code=500, detail="Photo upload failed")

    # Create or update body profile
    result = await db.execute(
        select(BodyProfile).where(BodyProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = BodyProfile(user_id=current_user.id)
        db.add(profile)
    profile.photos_front_url = front_url
    profile.photos_side_url = side_url
    await db.flush()

    # Trigger async reconstruction
    task_id = str(uuid.uuid4())
    try:
        from app.workers.tasks import reconstruct_body_task
        reconstruct_body_task.delay(
            user_id=str(current_user.id),
            front_url=front_url,
            side_url=side_url,
            task_id=task_id,
        )
    except Exception as e:
        logger.warning("Celery not available: %s — reconstruction queued for later", e)

    logger.info("Photos uploaded for user %s, reconstruction task: %s", current_user.id, task_id)
    return {
        "status": "processing",
        "task_id": task_id,
        "message": "Photos uploaded. Body reconstruction is in progress.",
    }


@router.get("/status/{task_id}")
async def get_reconstruction_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Check the status of an async body reconstruction task."""
    try:
        from app.workers.tasks import reconstruct_body_task
        result = reconstruct_body_task.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() else None,
        }
    except Exception:
        return {"task_id": task_id, "status": "UNKNOWN"}


@router.get("/{user_id}/measurements", response_model=BodyProfileResponse)
async def get_measurements(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> BodyProfileResponse:
    """Get body measurements for a user."""
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(BodyProfile).where(BodyProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Body profile not found")

    return BodyProfileResponse.model_validate(profile)


@router.post("/measurements", response_model=BodyProfileResponse)
async def update_measurements(
    measurements: BodyProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> BodyProfileResponse:
    """Manually enter or update body measurements."""
    result = await db.execute(
        select(BodyProfile).where(BodyProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = BodyProfile(user_id=current_user.id)
        db.add(profile)

    update_data = measurements.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.flush()
    await db.refresh(profile)
    return BodyProfileResponse.model_validate(profile)
