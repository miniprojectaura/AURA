"""Pydantic schemas for products and search."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=500)
    description: Optional[str] = None
    price_inr: float = Field(..., ge=0)
    category: str = Field(..., max_length=100)
    subcategory: Optional[str] = None
    color: Optional[str] = None
    brand: Optional[str] = None
    platform: str = Field(..., max_length=50)
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    affiliate_url: Optional[str] = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    price_inr: float
    currency: str
    category: str
    color: Optional[str] = None
    brand: Optional[str] = None
    platform: str
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    affiliate_url: Optional[str] = None
    is_active: bool
    created_at: datetime


class ProductSearchQuery(BaseModel):
    query: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    brand: Optional[str] = None
    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)
    platform: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=50)


class ProductSearchResult(BaseModel):
    product: ProductResponse
    similarity_score: float = Field(ge=0.0, le=1.0)
    match_source: str = "hybrid"  # dense, sparse, hybrid


class TailoringGuide(BaseModel):
    fabric_type: str
    fabric_yardage: float
    garment_type: str
    construction_steps: list[str]
    measurements: dict[str, float]
    iron_settings: Optional[str] = None
    finishing_details: Optional[str] = None
    estimated_cost_inr: Optional[float] = None


class WardrobeItemCreate(BaseModel):
    product_id: Optional[uuid.UUID] = None
    name: str = Field(..., max_length=255)
    category: str = Field(..., max_length=100)
    color: Optional[str] = None
    image_url: Optional[str] = None
    notes: Optional[str] = None


class WardrobeItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    category: str
    color: Optional[str] = None
    image_url: Optional[str] = None
    notes: Optional[str] = None
    is_favorite: bool
    created_at: datetime
