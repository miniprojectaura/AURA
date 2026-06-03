"""Design endpoints — outfit generation and virtual try-on."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.chat import DesignBrief, OutfitResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=OutfitResponse)
async def generate_outfit(
    brief: DesignBrief,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> OutfitResponse:
    """Generate outfit designs from a design brief.

    Constructs SDXL prompt from the brief, generates 4 variants
    with ControlNet conditioning, and filters by CLIP score.
    """
    logger.info("Generating outfit for user %s: %s", current_user.id, brief.occasion)

    try:
        from app.services.outfit_generator import OutfitGeneratorService
        generator = OutfitGeneratorService()
        results = await generator.generate_outfit(brief, body_params=None)

        return OutfitResponse(
            outfits=results,
            response_text=f"Here are {len(results)} outfit designs for your {brief.occasion or 'request'}!",
        )
    except Exception as e:
        logger.exception("Outfit generation failed")
        return OutfitResponse(
            outfits=[],
            response_text="I'm having trouble generating outfits right now. Please try again in a moment.",
        )


@router.post("/tryon")
async def virtual_tryon(
    outfit_image_url: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Apply virtual try-on using the user's avatar and a generated outfit."""
    logger.info("Virtual try-on for user %s", current_user.id)

    try:
        from app.services.tryon import TryOnService
        tryon = TryOnService()
        result = await tryon.virtual_tryon(
            outfit_image_url=outfit_image_url,
            user_photo_url=None,  # Fetched from body profile
            user_id=str(current_user.id),
        )
        return {
            "status": "completed",
            "tryon_image_url": result.get("image_url"),
            "confidence": result.get("confidence", 0.0),
        }
    except Exception as e:
        logger.exception("Virtual try-on failed")
        raise HTTPException(status_code=500, detail="Virtual try-on service unavailable")


@router.get("/gallery/{user_id}")
async def get_design_gallery(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get a user's generated design history."""
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # In production, fetch from a designs table
    return {"designs": [], "total": 0}
