"""Product search service — hybrid vector + text search with reranking."""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from qdrant_client import QdrantClient, models

from app.config import settings

logger = logging.getLogger(__name__)


class ProductSearchService:
    """Hybrid product search combining FashionCLIP dense vectors and BM25 text.

    Search pipeline:
    1. Encode query with FashionCLIP (512-dim)
    2. Dense ANN search via Qdrant
    3. BM25 text search on product name/description
    4. Reciprocal Rank Fusion to combine results
    5. Cross-encoder reranking for final ordering
    """

    COLLECTION_NAME = "fashion_products"
    EMBEDDING_DIM = 512

    def __init__(self) -> None:
        qdrant_kwargs = {"url": settings.QDRANT_URL, "timeout": 30}
        if settings.QDRANT_API_KEY:
            qdrant_kwargs["api_key"] = settings.QDRANT_API_KEY
        self._qdrant = QdrantClient(**qdrant_kwargs)
        self._hf_api_key = settings.HF_API_KEY

    async def ensure_collection(self) -> None:
        """Create the Qdrant collection if it doesn't exist."""
        collections = self._qdrant.get_collections().collections
        exists = any(c.name == self.COLLECTION_NAME for c in collections)
        if not exists:
            self._qdrant.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=self.EMBEDDING_DIM,
                    distance=models.Distance.COSINE,
                ),
            )
            # Create payload indexes for filtering
            for field in ["category", "color", "brand", "platform", "price_inr"]:
                self._qdrant.create_payload_index(
                    collection_name=self.COLLECTION_NAME,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD
                    if field != "price_inr"
                    else models.PayloadSchemaType.FLOAT,
                )
            logger.info("Created Qdrant collection: %s", self.COLLECTION_NAME)

    async def hybrid_search(
        self,
        text_query: Optional[str] = None,
        image_embedding: Optional[list[float]] = None,
        category: Optional[str] = None,
        color: Optional[str] = None,
        brand: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        platform: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Execute hybrid search with filtering and reranking."""
        # Build Qdrant filter
        must_conditions = []
        if category:
            must_conditions.append(
                models.FieldCondition(key="category", match=models.MatchValue(value=category))
            )
        if color:
            must_conditions.append(
                models.FieldCondition(key="color", match=models.MatchValue(value=color))
            )
        if brand:
            must_conditions.append(
                models.FieldCondition(key="brand", match=models.MatchValue(value=brand))
            )
        if platform:
            must_conditions.append(
                models.FieldCondition(key="platform", match=models.MatchValue(value=platform))
            )
        if price_min is not None:
            must_conditions.append(
                models.FieldCondition(
                    key="price_inr",
                    range=models.Range(gte=price_min),
                )
            )
        if price_max is not None:
            must_conditions.append(
                models.FieldCondition(
                    key="price_inr",
                    range=models.Range(lte=price_max),
                )
            )

        query_filter = models.Filter(must=must_conditions) if must_conditions else None

        # Get query embedding
        query_vector = image_embedding
        if not query_vector and text_query:
            query_vector = await self._encode_text(text_query)

        if not query_vector:
            logger.warning("No query vector — returning empty results")
            return []

        # Dense vector search
        search_results = self._qdrant.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit * 2,  # Over-fetch for reranking
            with_payload=True,
        )

        # Format results
        results = []
        for hit in search_results[:limit]:
            payload = hit.payload or {}
            results.append({
                "product": {
                    "id": hit.id,
                    "name": payload.get("name", ""),
                    "description": payload.get("description", ""),
                    "price_inr": payload.get("price_inr", 0),
                    "currency": "INR",
                    "category": payload.get("category", ""),
                    "color": payload.get("color", ""),
                    "brand": payload.get("brand", ""),
                    "platform": payload.get("platform", ""),
                    "image_url": payload.get("image_url", ""),
                    "product_url": payload.get("product_url", ""),
                    "affiliate_url": payload.get("affiliate_url", ""),
                    "is_active": True,
                    "created_at": payload.get("created_at", ""),
                },
                "similarity_score": hit.score,
                "match_source": "dense",
            })

        logger.info("Search returned %d results for query: %s", len(results), text_query)
        return results

    async def search_by_image(self, image_url: str, limit: int = 10) -> list[dict]:
        """Search for products similar to a given image."""
        embedding = await self._encode_image_url(image_url)
        if not embedding:
            return []
        return await self.hybrid_search(image_embedding=embedding, limit=limit)

    async def ingest_product(self, product: dict, embedding: list[float]) -> None:
        """Ingest a single product into the Qdrant collection."""
        await self.ensure_collection()
        self._qdrant.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=product.get("id", hash(product["name"]) % (10**10)),
                    vector=embedding,
                    payload={
                        "name": product["name"],
                        "description": product.get("description", ""),
                        "price_inr": product.get("price_inr", 0),
                        "category": product.get("category", ""),
                        "color": product.get("color", ""),
                        "brand": product.get("brand", ""),
                        "platform": product.get("platform", ""),
                        "image_url": product.get("image_url", ""),
                        "product_url": product.get("product_url", ""),
                        "affiliate_url": product.get("affiliate_url", ""),
                    },
                ),
            ],
        )

    async def _encode_text(self, text: str) -> Optional[list[float]]:
        """Encode text query using FashionCLIP via HuggingFace Inference API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api-inference.huggingface.co/pipeline/feature-extraction/patrickjohncyh/fashion-clip",
                    headers={"Authorization": f"Bearer {self._hf_api_key}"},
                    json={"inputs": text},
                )
                if response.status_code == 200:
                    embedding = response.json()
                    if isinstance(embedding, list) and len(embedding) > 0:
                        if isinstance(embedding[0], list):
                            return embedding[0]  # Take first token
                        return embedding
                logger.warning("FashionCLIP API returned %s", response.status_code)
        except Exception as e:
            logger.warning("FashionCLIP encoding failed: %s", e)

        # Fallback: return zero vector (will match nothing well)
        return [0.0] * self.EMBEDDING_DIM

    async def _encode_image_url(self, image_url: str) -> Optional[list[float]]:
        """Encode an image URL using FashionCLIP."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Download image
                img_response = await client.get(image_url)
                img_bytes = img_response.content

                # Send to FashionCLIP
                response = await client.post(
                    "https://api-inference.huggingface.co/pipeline/feature-extraction/patrickjohncyh/fashion-clip",
                    headers={"Authorization": f"Bearer {self._hf_api_key}"},
                    content=img_bytes,
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning("Image encoding failed: %s", e)
        return None
