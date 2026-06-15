"""Pydantic v2 schemas for user, body profile, and style profile."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _BaseSchema(BaseModel):
    """Base schema with ORM mode enabled."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---- Auth Schemas ----

class UserCreate(BaseModel):
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(default="Fashion Enthusiast", max_length=100)
    language_preference: str = Field(default="en", max_length=5)


class UserLogin(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    language_preference: Optional[str] = Field(None, max_length=5)


class UserResponse(_BaseSchema):
    id: uuid.UUID
    email: Optional[str] = None
    phone: Optional[str] = None
    display_name: str
    language_preference: str
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    scopes: list[str] = []


# ---- Body Profile Schemas ----

class BodyProfileCreate(BaseModel):
    height_cm: Optional[float] = Field(None, ge=50, le=300)
    weight_kg: Optional[float] = Field(None, ge=20, le=500)
    chest_cm: Optional[float] = Field(None, ge=30, le=200)
    waist_cm: Optional[float] = Field(None, ge=30, le=200)
    hip_cm: Optional[float] = Field(None, ge=30, le=200)
    shoulder_width_cm: Optional[float] = Field(None, ge=20, le=100)
    inseam_cm: Optional[float] = Field(None, ge=40, le=120)
    body_shape: Optional[str] = None
    skin_tone: Optional[str] = None


class BodyProfileResponse(_BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    chest_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    shoulder_width_cm: Optional[float] = None
    inseam_cm: Optional[float] = None
    body_shape: str
    skin_tone: Optional[str] = None
    avatar_glb_url: Optional[str] = None
    created_at: datetime


# ---- Style Profile Schemas ----

class StyleProfileCreate(BaseModel):
    favorite_colors: list[str] = Field(default_factory=list)
    preferred_occasions: list[str] = Field(default_factory=list)
    budget_range_min: Optional[float] = Field(None, ge=0)
    budget_range_max: Optional[float] = Field(None, ge=0)
    cultural_preferences: list[str] = Field(default_factory=list)


class StyleProfileUpdate(BaseModel):
    favorite_colors: Optional[list[str]] = None
    preferred_occasions: Optional[list[str]] = None
    budget_range_min: Optional[float] = None
    budget_range_max: Optional[float] = None
    cultural_preferences: Optional[list[str]] = None


class StyleProfileResponse(_BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    favorite_colors: Optional[list] = None
    preferred_occasions: Optional[list] = None
    budget_range_min: Optional[float] = None
    budget_range_max: Optional[float] = None
    cultural_preferences: Optional[list] = None
    created_at: datetime
