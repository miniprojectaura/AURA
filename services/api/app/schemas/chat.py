"""Pydantic schemas for chat, intent, and design."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Intent(str, enum.Enum):
    GREETING = "greeting"
    DESIGN_REQUEST = "design_request"
    STYLE_ADVICE = "style_advice"
    PRODUCT_SEARCH = "product_search"
    BODY_SCAN = "body_scan"
    VIRTUAL_TRYON = "virtual_tryon"
    WARDROBE_MANAGE = "wardrobe_manage"
    TAILORING = "tailoring"
    GENERAL_CHAT = "general_chat"
    FEEDBACK = "feedback"
    UNKNOWN = "unknown"


class ChatMessageIn(BaseModel):
    """Incoming chat message from client."""
    content: str = Field(..., min_length=1, max_length=4000)
    language: str = Field(default="en", max_length=5)


class ChatMessageOut(BaseModel):
    """Outgoing chat message to client."""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    role: str
    content: str
    audio_url: Optional[str] = None
    intent: Optional[str] = None
    metadata_json: Optional[dict] = None
    created_at: datetime


class ChatSessionCreate(BaseModel):
    language: str = Field(default="en", max_length=5)


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    language: str
    title: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    message_count: int = 0


class IntentClassification(BaseModel):
    """Result of intent classification."""
    intent: Intent
    confidence: float = Field(ge=0.0, le=1.0)
    sub_intent: Optional[str] = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class DesignBrief(BaseModel):
    """Extracted design parameters from user request."""
    occasion: Optional[str] = None
    body_type: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    colors: list[str] = Field(default_factory=list)
    fabric_preferences: list[str] = Field(default_factory=list)
    cultural_context: Optional[str] = None
    garment_types: list[str] = Field(default_factory=list)
    style_keywords: list[str] = Field(default_factory=list)


class OutfitResult(BaseModel):
    """A single generated outfit design."""
    image_url: str
    description: str
    clip_score: float
    design_brief: DesignBrief


class OutfitResponse(BaseModel):
    """Response containing generated outfits and related data."""
    outfits: list[OutfitResult] = Field(default_factory=list)
    products: list[dict] = Field(default_factory=list)
    tailoring_guide: Optional[dict] = None
    response_text: str
    audio_url: Optional[str] = None


class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="en", max_length=5)
    voice: str = Field(default="default")
