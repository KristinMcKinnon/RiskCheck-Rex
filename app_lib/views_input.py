import streamlit as st

from app_lib import db
from app_lib.components import render_disclaimer, render_sensitive_data_notice
from app_lib.gemini_client import GenerationError, generate_assessment
from app_lib.ratelimit import allow_generation

FIELD_CONFIG = [
    {
        "key": "project_description",
        "label": "Project description",
        "help": (
            "What the project is, its objectives, key stakeholders, "
            "timeframe, and delivery context. The more concrete detail you "
            "give here, the more useful the AI's output will be."
        ),
        "min_chars": 80,
    },
    {
        "key": "in_scope",
        "label": "In-scope statement",
        "help": "What is explicitly included in the project.",
        "min_chars": 30,
    },
    {
        "key": "out_of_scope",
        "label": "Out-of-scope statement",
        "help": "What is explicitly excluded from the project.",
        "min_chars": 30,
    },
    {
        "key": "methodology",
        "label": "General methodology",
        "help": (
            "E.g. agile / waterfall / hybrid, procurement approach, key "
            "delivery phases."
        ),
        "min_chars": 20,
    },
    {
        "key": "change_impacts",
        "label": "Expected change impacts",
        "help": (
            "Who and what is affected by this project - people, process, "
            "technology, systems, service delivery, community - and the "
            "nature of that change."
        ),
        "min_chars": 30,
    },
]


def _word_char_caption(text: str, min_chars: int) -> str:
    words = len(text.split())
    chars = len(text)
    status = "✅" if chars >= min_chars else f"(minimum {min_chars} characters)"
    return f"{words} words, {chars} characters {status}"


def render_input_form(conn, existing: dict | None):
    is_edit = existing is not None
    values = existing or {}

    flash = st.session_state.pop("flash_message", None)
    if flash:
        st.success(flash, icon="💾")

    render_sensitive_data_notice()
    st.title("🦖 RiskCheck Rex")
    st.caption(
        "A preliminary, AI-assisted risk assessment to use as a "
        "brainstorming starting point - not a final or authoritative "
        "assessment."
    )
    render_disclaimer()

    if is_edit:
        st.info(
            "You're editing a saved draft. Bookmark this page's URL to "
            "come back to it later - drafts are kept for 30 days of "
            "inactivity.",
            icon="🔖",
        )

    st.subheader("Tell us about the project")

    field_values = {}
    all_valid = True
    for field in FIELD_CONFIG:
        current = values.get(field["key"], "")
        field_values[field["key"]] = st.text_area(
            field["label"],
            value=current,
            help=field["help"],
            height=140,
            key=f"input_{field['key']}",
        )
        st.caption(_word_char_caption(field_values[field["key"]], field["min_chars"]))
        if len(field_values[field["key"]].strip()) < field["min_chars"]:
            all_valid = False

    if not all_valid:
        st.caption(
            "Fill in every field above the minimum length shown to enable "
            "saving and generating."
        )

    col1, col2 = st.columns(2)
    save_clicked = col1.button(
        "💾 Save draft for later", disabled=not all_valid, use_container_width=True
    )
    generate_clicked = col2.button(
        "✨ Generate risk assessment",
        type="primary",
        disabled=not all_valid,
        use_container_width=True,
    )

    if save_clicked:
        _save_only(conn, existing, field_values)

    if generate_clicked:
        _save_and_generate(conn, existing, field_values)


def _save_only(conn, existing, field_values):
    if existing:
        db.update_inputs(conn, existing["id"], field_values)
        assessment_id = existing["id"]
    else:
        assessment_id = db.create_draft(conn, field_values)

    st.query_params["id"] = assessment_id
    st.session_state["flash_message"] = "Draft saved. This page's URL is now your link back to it."
    st.rerun()


def _save_and_generate(conn, existing, field_values):
    if not allow_generation(conn):
        st.error(
            "This tool has hit its shared daily limit for generating new "
            "assessments. Please try again tomorrow.",
            icon="🚫",
        )
        return

    if existing:
        db.update_inputs(conn, existing["id"], field_values)
        assessment_id = existing["id"]
    else:
        assessment_id = db.create_draft(conn, field_values)

    with st.spinner("Asking Gemini to draft a preliminary risk assessment..."):
        try:
            results = generate_assessment(field_values)
        except GenerationError:
            st.error(
                "The AI service didn't return a usable result just now. "
                "Your inputs have been saved as a draft - please try "
                "clicking Generate again in a moment.",
                icon="⚠️",
            )
            st.query_params["id"] = assessment_id
            return

    db.save_results(conn, assessment_id, results)
    st.session_state["force_edit"] = False
    st.query_params["id"] = assessment_id
    st.rerun()
