"""Avatar endpoints — body photo analysis, measurements, and profile management.

Replaces the previous Supabase/Celery-dependent routes with direct
Groq Vision analysis that works on free Render (no GPU, no external storage).
"""
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

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/analyze", status_code=status.HTTP_200_OK)
async def analyze_body_photo(
    photo: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a body photo and get AI-analyzed measurements.

    The photo is analyzed by Groq Vision LLM to extract:
    - Body measurements (height, chest, waist, hip, shoulder, inseam)
    - Body shape classification
    - Skin tone + undertone
    - Facial features (face shape, hair type)

    Results are saved to the user's BodyProfile.
    """
    # Validate file
    if photo.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photo must be JPEG, PNG, or WebP",
        )

    contents = await photo.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Photo exceeds 10MB limit",
        )

    # Analyze with Groq Vision
    from app.services.body_analysis import BodyAnalysisService
    analyzer = BodyAnalysisService()
    result = await analyzer.analyze_with_skin_tone(contents)

    if result.confidence < 0.1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not analyze the photo. Please upload a clear full-body photo.",
        )

    # Save to BodyProfile
    stmt = select(BodyProfile).where(BodyProfile.user_id == current_user.id)
    db_result = await db.execute(stmt)
    profile = db_result.scalar_one_or_none()

    if not profile:
        profile = BodyProfile(user_id=current_user.id)
        db.add(profile)

    # Update measurements
    if result.height_cm:
        profile.height_cm = result.height_cm
    if result.weight_kg:
        profile.weight_kg = result.weight_kg
    if result.chest_cm:
        profile.chest_cm = result.chest_cm
    if result.waist_cm:
        profile.waist_cm = result.waist_cm
    if result.hip_cm:
        profile.hip_cm = result.hip_cm
    if result.shoulder_width_cm:
        profile.shoulder_width_cm = result.shoulder_width_cm
    if result.inseam_cm:
        profile.inseam_cm = result.inseam_cm

    profile.body_shape = result.body_shape
    profile.skin_tone = result.skin_tone

    # Store full analysis in smplx_params JSON field
    profile.smplx_params = {
        "analysis": result.to_dict(),
        "source": "groq_vision",
    }

    await db.flush()
    await db.refresh(profile)

    logger.info("Body analysis saved for user %s: shape=%s, confidence=%.2f",
                current_user.id, result.body_shape, result.confidence)

    return {
        "status": "completed",
        "measurements": {
            "height_cm": result.height_cm,
            "weight_kg": result.weight_kg,
            "chest_cm": result.chest_cm,
            "waist_cm": result.waist_cm,
            "hip_cm": result.hip_cm,
            "shoulder_width_cm": result.shoulder_width_cm,
            "inseam_cm": result.inseam_cm,
        },
        "body_shape": result.body_shape,
        "skin_tone": result.skin_tone,
        "undertone": result.undertone,
        "facial_features": result.facial_features,
        "gender_presentation": result.gender_presentation,
        "age_range": result.age_range,
        "confidence": result.confidence,
    }


@router.get("/profile")
async def get_body_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the current user's body profile."""
    stmt = select(BodyProfile).where(BodyProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        return {"has_profile": False}

    analysis = (profile.smplx_params or {}).get("analysis", {})

    return {
        "has_profile": True,
        "measurements": {
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
            "chest_cm": profile.chest_cm,
            "waist_cm": profile.waist_cm,
            "hip_cm": profile.hip_cm,
            "shoulder_width_cm": profile.shoulder_width_cm,
            "inseam_cm": profile.inseam_cm,
        },
        "body_shape": profile.body_shape.value if hasattr(profile.body_shape, 'value') else str(profile.body_shape),
        "skin_tone": profile.skin_tone,
        "facial_features": analysis.get("facial_features", {}),
        "gender_presentation": analysis.get("gender_presentation", "unspecified"),
        "age_range": analysis.get("age_range", "adult"),
        "undertone": analysis.get("undertone", "neutral"),
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


@router.post("/measurements", response_model=BodyProfileResponse)
async def update_measurements(
    measurements: BodyProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> BodyProfileResponse:
    """Manually enter or update body measurements."""
    stmt = select(BodyProfile).where(BodyProfile.user_id == current_user.id)
    result = await db.execute(stmt)
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
