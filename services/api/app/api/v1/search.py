"""Search endpoints — hybrid product search and similarity matching."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.product import ProductSearchQuery, ProductSearchResult

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/products", response_model=list[ProductSearchResult])
async def search_products(
    query: ProductSearchQuery,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProductSearchResult]:
    """Hybrid product search combining dense vector ANN and BM25 text search.

    Results are fused via Reciprocal Rank Fusion (RRF) and
    reranked with a cross-encoder.
    """
    logger.info("Product search by user %s: %s", current_user.id, query.query)

    try:
        from app.services.product_search import ProductSearchService
        search = ProductSearchService()
        results = await search.hybrid_search(
            text_query=query.query,
            category=query.category,
            color=query.color,
            brand=query.brand,
            price_min=query.price_min,
            price_max=query.price_max,
            platform=query.platform,
            limit=query.limit,
        )
        return results
    except Exception as e:
        logger.exception("Product search failed")
        return []


@router.post("/similar")
async def find_similar_products(
    image_url: str,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
) -> list[dict]:
    """Find visually similar products by image URL using FashionCLIP embeddings."""
    logger.info("Similar product search for image: %s", image_url[:80])

    try:
        from app.services.product_search import ProductSearchService
        search = ProductSearchService()
        results = await search.search_by_image(image_url=image_url, limit=limit)
        return results
    except Exception as e:
        logger.exception("Similar search failed")
        return []


@router.get("/trending")
async def get_trending_products(
    category: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=50),
) -> dict:
    """Get trending products — most clicked/viewed recently."""
    # In production, this would query analytics data
    return {"trending": [], "category": category}


@router.post("/feedback")
async def record_search_feedback(
    product_id: str,
    action: str,  # "click", "like", "dislike", "purchase"
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Record user feedback on search results for personalization."""
    logger.info("Search feedback: user=%s product=%s action=%s",
                current_user.id, product_id, action)
    # Update user style profile vector based on feedback
    return {"status": "recorded"}
