"""Design endpoints — full AI fashion pipeline.

Pipeline: User prompt + Body profile → Fashion Brain → Outfit Design → Visualization
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_active_user
from app.database import get_db
from app.models.user import BodyProfile, User
from app.schemas.chat import DesignBrief, OutfitResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate")
async def generate_outfit(
    brief: DesignBrief,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate personalized outfit designs using the full AI pipeline.

    1. Fetches user's body profile (if exists)
    2. Sends to Fashion Brain agent for head-to-toe design
    3. Generates outfit visualization image (if HF token available)
    4. Returns complete design with garments, colors, styling tips
    """
    logger.info("Generating outfit for user %s: %s", current_user.id, brief.occasion)

    # Step 1: Get body profile
    body_profile = {}
    stmt = select(BodyProfile).where(BodyProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if profile:
        body_profile = {
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
            "chest_cm": profile.chest_cm,
            "waist_cm": profile.waist_cm,
            "hip_cm": profile.hip_cm,
            "shoulder_width_cm": profile.shoulder_width_cm,
            "inseam_cm": profile.inseam_cm,
            "body_shape": profile.body_shape.value if hasattr(profile.body_shape, 'value') else str(profile.body_shape),
            "skin_tone": profile.skin_tone,
        }
        # Add analysis data if available
        analysis = (profile.smplx_params or {}).get("analysis", {})
        body_profile.update({
            "undertone": analysis.get("undertone", "neutral"),
            "facial_features": analysis.get("facial_features", {}),
            "gender_presentation": analysis.get("gender_presentation", "unspecified"),
            "age_range": analysis.get("age_range", "adult"),
        })

    # Step 2: Build prompt from brief
    prompt_parts = []
    if brief.style_keywords:
        prompt_parts.append(" ".join(brief.style_keywords))
    if brief.occasion:
        prompt_parts.append(f"for {brief.occasion}")
    if brief.colors:
        prompt_parts.append(f"in {', '.join(brief.colors)}")
    if brief.garment_types:
        prompt_parts.append(f"including {', '.join(brief.garment_types)}")
    if brief.cultural_context:
        prompt_parts.append(f"({brief.cultural_context} style)")

    prompt = " ".join(prompt_parts) if prompt_parts else "a stylish outfit"

    # Step 3: Fashion Brain designs the outfit
    try:
        from app.services.fashion_brain import FashionBrainService
        brain = FashionBrainService()
        design = await brain.design_outfit(
            body_profile=body_profile,
            prompt=prompt,
            occasion=brief.occasion,
            style_preferences=brief.style_keywords,
        )
    except Exception as e:
        logger.exception("Fashion Brain failed: %s", e)
        return {
            "response_text": "I'm having trouble designing right now. Please try again.",
            "outfits": [],
            "design": None,
            "visualization_url": None,
            "body_profile_used": bool(body_profile),
        }

    # Step 4: Generate visualization image (non-blocking, best-effort)
    visualization_b64 = None
    try:
        from app.services.outfit_visualizer import OutfitVisualizerService
        visualizer = OutfitVisualizerService()
        visualization_b64 = await visualizer.generate_outfit_image(
            outfit_design=design.to_dict(),
            body_profile=body_profile,
        )
        await visualizer.close()
    except Exception as e:
        logger.warning("Outfit visualization failed (non-critical): %s", e)

    # Step 5: Build response
    # Convert garments to the OutfitResponse format for backward compat
    outfits = []
    for garment in design.garments:
        outfits.append({
            "type": garment.get("type", ""),
            "name": garment.get("name", ""),
            "description": garment.get("description", ""),
            "color": garment.get("color", ""),
            "fabric": garment.get("fabric", ""),
            "fit_notes": garment.get("fit_notes", ""),
            "styling_tip": garment.get("styling_tip", ""),
            "estimated_price_inr": garment.get("estimated_price_inr"),
            "search_keywords": garment.get("search_keywords", ""),
        })

    response_text = design.overall_look_description or f"Here's your personalized {design.outfit_name}!"

    return {
        "response_text": response_text,
        "outfits": outfits,
        "design": design.to_dict(),
        "visualization_b64": visualization_b64,
        "body_profile_used": bool(body_profile),
        "body_shape_advice": design.body_shape_advice,
    }


@router.get("/gallery/{user_id}")
async def get_design_gallery(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get a user's generated design history."""
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    # Future: fetch from a designs table
    return {"designs": [], "total": 0}
