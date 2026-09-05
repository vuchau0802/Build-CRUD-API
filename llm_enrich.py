from pydantic import BaseModel, Field
from typing import Optional, Literal
import os

class EnrichRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = Field(None, max_length=2000)
    price_gbp: float
    availability_text: str = Field(..., min_length=1)


class EnrichResponse(BaseModel):
    category: Literal["fiction", "nonfiction", "poetry", "childrens", "other"]
    summary: str
    quality_flags: list[Literal["missing_description", "vague_title", "price_outlier"]]
    confidence: float = Field(..., ge=0.0, le=1.0)


def enrich_stub(request: EnrichRequest) -> EnrichResponse:
    """Stub mode: returns a fixed, schema-valid response without calling any model."""
    flags = []
    if request.description is None:
        flags.append("missing_description")
    return EnrichResponse(
        category="other",
        summary="Stub summary — no model was called.",
        quality_flags=flags,
        confidence=0.5
    )