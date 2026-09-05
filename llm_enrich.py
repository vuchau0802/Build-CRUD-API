from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal
import os
import re
import json
import time
import random
from pathlib import Path
from datetime import datetime, timezone
from openai import (
    OpenAI,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
    AuthenticationError,
    PermissionDeniedError,
    BadRequestError,
)
from dotenv import load_dotenv

load_dotenv()

PROMPT_PATH = Path(__file__).parent / "prompts" / "enrich-v1.md"
PROMPT_VERSION = "enrich-v1"
QUARANTINE_PATH = Path(__file__).parent / "logs" / "quarantine.jsonl"
QUARANTINE_PATH.parent.mkdir(exist_ok=True)

TIMEOUT_SECONDS = 30.0
MAX_ATTEMPTS = 3  # 1 initial + up to 2 retries, for retryable errors only


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
    def __init__(self, message: str, raw_output: str):
        super().__init__(message)
        self.raw_output = raw_output


class EnrichmentTimedOut(Exception):
    pass


class EnrichmentDisabled(Exception):
    pass


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
    # max_retries=0: we implement our own explicit retry policy below,
    # rather than relying on the SDK's silent default of retrying twice.
    return OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        timeout=TIMEOUT_SECONDS,
        max_retries=0,
    )


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def log_cost(model: str, input_tokens: int, output_tokens: int, duration_ms: float, repaired: bool):
    """One structured log line per call, written to stdout per twelve-factor logging."""
    entry = {
        "event": "llm_call",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": round(duration_ms, 1),
        "repaired": repaired,
    }
    print(json.dumps(entry))


def _call_with_retry(system_prompt: str, user_content: str) -> tuple[str, dict]:
    """Makes one model call with retry-on-the-right-errors. Returns (text, usage_info)."""
    client = get_client()
    model = os.environ["LLM_MODEL"]
    attempt = 0
    last_exception = None

    while attempt < MAX_ATTEMPTS:
        attempt += 1
        start = time.time()
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            duration_ms = (time.time() - start) * 1000
            usage = {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
                "duration_ms": duration_ms,
                "model": model,
            }
            return response.choices[0].message.content, usage

        except APITimeoutError as e:
            raise EnrichmentTimedOut(str(e))

        except (RateLimitError, InternalServerError) as e:
            # Retryable: 429 (rate limit) and 5xx (server error). Back off with jitter.
            last_exception = e
            if attempt >= MAX_ATTEMPTS:
                break
            wait = (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            time.sleep(wait)
            continue

        except (AuthenticationError, PermissionDeniedError, BadRequestError) as e:
            # Never retry: a bad key, forbidden request, or malformed request will not
            # fix itself by trying again, and retrying just burns quota.
            raise

    raise last_exception


def extract_json(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
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
    if os.environ.get("LLM_ENABLED", "true").lower() == "false":
        raise EnrichmentDisabled("LLM_ENABLED is false")

    system_prompt = load_prompt()
    user_content = json.dumps(request.model_dump())

    raw_output, usage = _call_with_retry(system_prompt, user_content)
    repaired = False

    try:
        parsed = extract_json(raw_output)
        validated = EnrichResponse.model_validate(parsed)
        log_cost(usage["model"], usage["input_tokens"], usage["output_tokens"], usage["duration_ms"], repaired)
        return validated
    except (ValueError, ValidationError, json.JSONDecodeError) as first_error:
        repaired = True
        repair_user_content = (
            f"{user_content}\n\n"
            f"Your previous answer was rejected for this reason: {first_error}\n"
            f"Your previous answer was: {raw_output}\n"
            f"Return ONLY corrected JSON matching the required schema."
        )
        repaired_raw, repair_usage = _call_with_retry(system_prompt, repair_user_content)
        total_duration = usage["duration_ms"] + repair_usage["duration_ms"]
        total_input = usage["input_tokens"] + repair_usage["input_tokens"]
        total_output = usage["output_tokens"] + repair_usage["output_tokens"]

        try:
            parsed = extract_json(repaired_raw)
            validated = EnrichResponse.model_validate(parsed)
            log_cost(usage["model"], total_input, total_output, total_duration, repaired)
            return validated
        except (ValueError, ValidationError, json.JSONDecodeError) as second_error:
            log_cost(usage["model"], total_input, total_output, total_duration, repaired)
            quarantine(request, repaired_raw, str(second_error))
            raise EnrichmentFailed(str(second_error), repaired_raw)