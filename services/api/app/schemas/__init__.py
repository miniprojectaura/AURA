"""
Schemas package – re-exports all Pydantic models.
"""

from app.schemas.chat import (  # noqa: F401
    ChatMessageIn,
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionResponse,
    ClassifyRequest,
    DesignBrief,
    IntentClassification,
    Intent,
    OutfitResponse,
    SynthesizeRequest,
)
from app.schemas.product import (  # noqa: F401
    ProductCreate,
    ProductResponse,
    ProductSearchQuery,
    ProductSearchResult,
    TailoringGuide,
    WardrobeItemCreate,
    WardrobeItemResponse,
)
from app.schemas.user import (  # noqa: F401
    BodyProfileCreate,
    BodyProfileResponse,
    StyleProfileCreate,
    StyleProfileResponse,
    StyleProfileUpdate,
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # user
    "UserCreate", "UserLogin", "UserUpdate", "UserResponse",
    "BodyProfileCreate", "BodyProfileResponse",
    "StyleProfileCreate", "StyleProfileUpdate", "StyleProfileResponse",
    "Token", "TokenData",
    
    # chat
    "ChatMessageIn", "ChatMessageOut", 
    "ChatSessionCreate", "ChatSessionResponse",
    "ClassifyRequest", "SynthesizeRequest",
    "IntentClassification", "Intent",
    "DesignBrief", "OutfitResponse",
    
    # product
    "ProductCreate", "ProductResponse",
    "ProductSearchQuery", "ProductSearchResult", 
    "WardrobeItemCreate", "WardrobeItemResponse",
    "TailoringGuide",
]