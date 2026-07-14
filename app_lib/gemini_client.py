import json
import logging
import time

import streamlit as st
from google import genai
from google.genai import types

from app_lib.prompts import RESPONSE_SCHEMA, SYSTEM_INSTRUCTION, build_user_prompt

MODEL_NAME = "gemini-2.5-flash"
MAX_OUTPUT_TOKENS = 8192
MAX_ATTEMPTS = 3

logger = logging.getLogger("riskcheck_rex")


class GenerationError(Exception):
    """Raised when Gemini can't be reached, or its output can't be parsed,
    after all retries. The caller should show a friendly message and keep
    the user's saved input intact (never discard it)."""


@st.cache_resource
def _get_client() -> genai.Client:
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def generate_assessment(inputs: dict) -> dict:
    """Calls Gemini and returns a dict shaped like RESPONSE_SCHEMA, with our
    own sequential IDs stamped onto each risk/opportunity."""
    client = _get_client()
    user_prompt = build_user_prompt(inputs)

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
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
            time.sleep(1.5 * attempt)

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
