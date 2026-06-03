"""User, BodyProfile, and StyleProfile ORM models."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BodyShape(str, enum.Enum):
    """Body shape classification."""
    PEAR = "pear"
    APPLE = "apple"
    HOURGLASS = "hourglass"
    RECTANGLE = "rectangle"
    INVERTED_TRIANGLE = "inverted_triangle"
    UNKNOWN = "unknown"


class User(Base):
    """Application user account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(100), default="Fashion Enthusiast")
    language_preference: Mapped[str] = mapped_column(String(5), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    body_profile: Mapped[Optional["BodyProfile"]] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )
    style_profile: Mapped[Optional["StyleProfile"]] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )
    sessions: Mapped[list["Session"]] = relationship(back_populates="user", lazy="selectin")
    wardrobe_items: Mapped[list["WardrobeItem"]] = relationship(
        back_populates="user", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User {self.email or self.phone}>"


class BodyProfile(Base):
    """User body measurements and 3D avatar data."""

    __tablename__ = "body_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    height_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    chest_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    waist_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hip_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shoulder_width_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    inseam_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    body_shape: Mapped[BodyShape] = mapped_column(
        Enum(BodyShape), default=BodyShape.UNKNOWN
    )
    skin_tone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    smplx_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    avatar_glb_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photos_front_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photos_side_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="body_profile")

    def __repr__(self) -> str:
        return f"<BodyProfile user={self.user_id}>"


class StyleProfile(Base):
    """User fashion preferences and style vector."""

    __tablename__ = "style_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    preference_vector: Mapped[Optional[list]] = mapped_column(
        ARRAY(Float, dimensions=1), nullable=True
    )
    favorite_colors: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    preferred_occasions: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    budget_range_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    budget_range_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cultural_preferences: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    disliked_styles: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    body_type_preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="style_profile")

    def __repr__(self) -> str:
        return f"<StyleProfile user={self.user_id}>"
