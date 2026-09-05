from pydantic import BaseModel, Field
from typing import Optional, Literal
import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PROMPT_PATH = Path(__file__).parent / "prompts" / "enrich-v1.md"
PROMPT_VERSION = "enrich-v1"


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


def get_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
    )


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def call_model(request: EnrichRequest) -> str:
    """Calls the real model and returns its raw text response (not yet parsed/validated — Stage 3)."""
    client = get_client()
    system_prompt = load_prompt()
    user_content = json.dumps(request.model_dump())

    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content