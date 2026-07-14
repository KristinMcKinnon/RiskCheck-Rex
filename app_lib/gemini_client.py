import json
import logging
import random
import time

import streamlit as st
from google import genai
from google.genai import types

from app_lib.prompts import RESPONSE_SCHEMA, SYSTEM_INSTRUCTION, build_user_prompt
from app_lib.ratelimit import allow_generation

MODEL_NAME = "gemini-3.5-flash"
MAX_OUTPUT_TOKENS = 8192
MAX_ATTEMPTS = 5
RETRY_BACKOFF_SECONDS = 2

logger = logging.getLogger("riskcheck_rex")


class GenerationError(Exception):
    """Raised when Gemini can't be reached, or its output can't be parsed,
    after all retries. The caller should show a friendly message and keep
    the user's saved input intact (never discard it)."""


@st.cache_resource
def _get_client() -> genai.Client:
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def generate_assessment(inputs: dict, conn) -> dict:
    """Calls Gemini and returns a dict shaped like RESPONSE_SCHEMA, with our
    own sequential IDs stamped onto each risk/opportunity.

    The caller's pre-flight `allow_generation` check covers the first
    attempt; each retry beyond that re-checks and counts against the same
    per-IP daily cap, so a string of retries can't multiply real Gemini
    traffic past the cap."""
    client = _get_client()
    user_prompt = build_user_prompt(inputs)

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt > 1 and not allow_generation(conn):
            logger.warning("Stopping Gemini retries at attempt %s: daily rate limit reached", attempt)
            break
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    temperature=0.5,
                ),
            )
            parsed = json.loads(response.text)
            return _stamp_ids(parsed)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            last_error = exc
            logger.warning("Gemini response parse failure on attempt %s: %s", attempt, type(exc).__name__)
        except Exception as exc:  # network/timeout/API errors from the SDK
            last_error = exc
            logger.warning("Gemini call failed on attempt %s: %s: %s", attempt, type(exc).__name__, exc)

        if attempt < MAX_ATTEMPTS:
            base_delay = RETRY_BACKOFF_SECONDS * 2 ** (attempt - 1)
            time.sleep(random.uniform(base_delay * 0.5, base_delay * 1.5))

    raise GenerationError(
        "Gemini didn't return a usable result after several attempts."
    ) from last_error


def _stamp_ids(parsed: dict) -> dict:
    risks = parsed.get("risks", [])
    for i, risk in enumerate(risks, start=1):
        risk["id"] = f"R{i}"
        risk.setdefault("suggested_controls", [])
        risk.setdefault("assumptions", [])

    opportunities = parsed.get("opportunities", [])
    for i, opp in enumerate(opportunities, start=1):
        opp["id"] = f"O{i}"
        opp.setdefault("suggested_actions", [])
        opp.setdefault("assumptions", [])

    return {
        "risks": risks,
        "opportunities": opportunities,
        "probing_questions": parsed.get("probing_questions", []),
    }
