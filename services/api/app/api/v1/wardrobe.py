"""Wardrobe endpoints — manage user's virtual wardrobe."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_active_user
from app.database import get_db
from app.models.product import WardrobeItem
from app.models.user import User
from app.schemas.product import WardrobeItemCreate, WardrobeItemResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[WardrobeItemResponse])
async def list_wardrobe(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    category: str = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[WardrobeItemResponse]:
    """List all items in the user's wardrobe."""
    query = select(WardrobeItem).where(WardrobeItem.user_id == current_user.id)
    if category:
        query = query.where(WardrobeItem.category == category)
    query = query.order_by(WardrobeItem.created_at.desc()).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()
    return [WardrobeItemResponse.model_validate(item) for item in items]


@router.post("/", response_model=WardrobeItemResponse, status_code=status.HTTP_201_CREATED)
async def add_wardrobe_item(
    item_data: WardrobeItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WardrobeItemResponse:
    """Add an item to the user's wardrobe."""
    item = WardrobeItem(
        user_id=current_user.id,
        product_id=item_data.product_id,
        name=item_data.name,
        category=item_data.category,
        color=item_data.color,
        image_url=item_data.image_url,
        notes=item_data.notes,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    logger.info("Wardrobe item added: %s for user %s", item.name, current_user.id)
    return WardrobeItemResponse.model_validate(item)


@router.put("/{item_id}", response_model=WardrobeItemResponse)
async def update_wardrobe_item(
    item_id: uuid.UUID,
    item_data: WardrobeItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WardrobeItemResponse:
    """Update a wardrobe item."""
    result = await db.execute(
        select(WardrobeItem).where(
            WardrobeItem.id == item_id,
            WardrobeItem.user_id == current_user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")

    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)
    return WardrobeItemResponse.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wardrobe_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove an item from the wardrobe."""
    result = await db.execute(
        select(WardrobeItem).where(
            WardrobeItem.id == item_id,
            WardrobeItem.user_id == current_user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")

    await db.delete(item)
    logger.info("Wardrobe item deleted: %s", item_id)


@router.post("/suggest-outfit")
async def suggest_outfit_from_wardrobe(
    occasion: str = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Suggest an outfit combination from the user's existing wardrobe."""
    result = await db.execute(
        select(WardrobeItem).where(WardrobeItem.user_id == current_user.id)
    )
    items = result.scalars().all()

    if not items:
        return {"suggestion": None, "message": "Your wardrobe is empty. Add some items first!"}

    # Use LLM to suggest outfit combination
    try:
        from app.services.llm import LLMService
        llm = LLMService()
        items_desc = ", ".join([f"{i.name} ({i.category}, {i.color})" for i in items[:20]])
        response = await llm.chat_completion(
            messages=[
                {"role": "system", "content": "You are a fashion stylist. Suggest an outfit from the given wardrobe items."},
                {"role": "user", "content": f"Occasion: {occasion}. Wardrobe: {items_desc}. Suggest a complete outfit."},
            ],
            temperature=0.7,
        )
        return {"suggestion": response, "items_count": len(items)}
    except Exception:
        return {"suggestion": "Mix and match your items for a great look!", "items_count": len(items)}
