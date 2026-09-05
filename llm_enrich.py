from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal
import os
import re
import json
from pathlib import Path
from datetime import datetime, timezone
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PROMPT_PATH = Path(__file__).parent / "prompts" / "enrich-v1.md"
PROMPT_VERSION = "enrich-v1"
QUARANTINE_PATH = Path(__file__).parent / "logs" / "quarantine.jsonl"
QUARANTINE_PATH.parent.mkdir(exist_ok=True)


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


class EnrichmentFailed(Exception):
    """Raised when the model's output cannot be parsed/validated even after one repair attempt."""
    def __init__(self, message: str, raw_output: str):
        super().__init__(message)
        self.raw_output = raw_output


def enrich_stub(request: EnrichRequest) -> EnrichResponse:
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


def _raw_call(system_prompt: str, user_content: str) -> str:
    client = get_client()
    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content


def extract_json(text: str) -> dict:
    """Strip code fences / stray text and parse the first JSON object found. Raises ValueError if none found."""
    cleaned = text.strip()
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    # Find the first { ... } block, in case there's stray text around it
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))


def quarantine(request: EnrichRequest, raw_output: str, reason: str):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "input": request.model_dump(),
        "raw_output": raw_output,
        "reason": reason,
    }
    with open(QUARANTINE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def call_model(request: EnrichRequest) -> EnrichResponse:
    """Calls the model, parses and validates the output, repairs once on failure, quarantines on final failure."""
    system_prompt = load_prompt()
    user_content = json.dumps(request.model_dump())

    raw_output = _raw_call(system_prompt, user_content)

    try:
        parsed = extract_json(raw_output)
        validated = EnrichResponse.model_validate(parsed)
        return validated
    except (ValueError, ValidationError, json.JSONDecodeError) as first_error:
        # One repair attempt: send the broken output and the exact error back
        repair_user_content = (
            f"{user_content}\n\n"
            f"Your previous answer was rejected for this reason: {first_error}\n"
            f"Your previous answer was: {raw_output}\n"
            f"Return ONLY corrected JSON matching the required schema."
        )
        repaired_raw = _raw_call(system_prompt, repair_user_content)

        try:
            parsed = extract_json(repaired_raw)
            validated = EnrichResponse.model_validate(parsed)
            return validated
        except (ValueError, ValidationError, json.JSONDecodeError) as second_error:
            quarantine(request, repaired_raw, str(second_error))
            raise EnrichmentFailed(str(second_error), repaired_raw)