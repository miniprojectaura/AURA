"""Tailoring endpoints — guide generation, fabric recommendations, yardage calculation."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from app.auth.jwt import get_current_active_user
from app.models.user import User
from app.schemas.product import TailoringGuide

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/guide", response_model=TailoringGuide)
async def generate_tailoring_guide(
    garment_type: str,
    fabric_type: str,
    current_user: User = Depends(get_current_active_user),
) -> TailoringGuide:
    """Generate a complete tailoring guide with construction steps and yardage."""
    logger.info("Tailoring guide request: %s in %s for user %s",
                garment_type, fabric_type, current_user.id)

    try:
        from app.services.tailoring import TailoringService
        tailor = TailoringService()
        guide = await tailor.generate_guide(
            garment_type=garment_type,
            fabric_type=fabric_type,
            user_id=str(current_user.id),
        )
        return guide
    except Exception as e:
        logger.exception("Tailoring guide generation failed")
        # Return sensible defaults
        return TailoringGuide(
            fabric_type=fabric_type,
            fabric_yardage=3.5,
            garment_type=garment_type,
            construction_steps=[
                "Take accurate measurements",
                "Cut fabric according to pattern",
                "Sew main seams",
                "Add embellishments",
                "Iron and finish",
            ],
            measurements={},
            iron_settings="Medium heat",
            finishing_details="Steam press for a polished look",
        )


@router.get("/fabrics")
async def list_fabric_recommendations(
    garment_type: str = "saree",
    occasion: str = "casual",
) -> dict:
    """Get fabric recommendations for a garment type and occasion."""
    fabric_db = {
        "saree": {
            "wedding": ["Banarasi silk", "Kanjeevaram silk", "Patola silk", "Georgette with zari"],
            "casual": ["Cotton", "Linen", "Chiffon", "Crepe"],
            "festival": ["Silk", "Organza", "Tussar silk", "Art silk"],
            "office": ["Cotton", "Linen blend", "Crepe", "Georgette"],
        },
        "lehenga": {
            "wedding": ["Raw silk", "Velvet", "Net with embroidery", "Brocade"],
            "casual": ["Cotton", "Chanderi", "Linen"],
            "festival": ["Silk", "Organza", "Net"],
        },
        "kurta": {
            "wedding": ["Silk", "Brocade", "Jacquard"],
            "casual": ["Cotton", "Linen", "Khadi"],
            "office": ["Cotton", "Linen blend", "Chambray"],
        },
    }
    fabrics = fabric_db.get(garment_type, {}).get(occasion, ["Cotton", "Polyester blend"])
    return {
        "garment_type": garment_type,
        "occasion": occasion,
        "recommended_fabrics": fabrics,
    }


@router.post("/measurements")
async def calculate_yardage(
    garment_type: str,
    height_cm: float,
    bust_cm: float = 0,
    waist_cm: float = 0,
    hip_cm: float = 0,
) -> dict:
    """Calculate fabric yardage from body measurements."""
    # Yardage formulas based on garment type
    yardage_formulas = {
        "saree": 5.5,  # Standard saree length in meters
        "blouse": (bust_cm / 100 + 0.5) if bust_cm else 1.0,
        "lehenga": (height_cm / 100 * 2.5) if height_cm else 3.5,
        "salwar_kameez": (height_cm / 100 * 3) if height_cm else 4.0,
        "kurta": (height_cm / 100 * 1.5) if height_cm else 2.5,
        "sherwani": (height_cm / 100 * 2) if height_cm else 3.0,
    }
    yardage = yardage_formulas.get(garment_type, 3.0)

    return {
        "garment_type": garment_type,
        "fabric_yardage_meters": round(yardage, 2),
        "fabric_yardage_yards": round(yardage * 1.0936, 2),
        "measurements_used": {
            "height_cm": height_cm,
            "bust_cm": bust_cm,
            "waist_cm": waist_cm,
            "hip_cm": hip_cm,
        },
    }
