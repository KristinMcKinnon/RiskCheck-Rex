from pathlib import Path

import streamlit as st

ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"
LOGO_ICON_PATH = ASSETS_DIR / "logo_icon.png"

DISCLAIMER_TEXT = (
    "**This is an AI-generated starting point only.** It has not been "
    "validated by a qualified risk practitioner and does not constitute a "
    "complete or compliant risk assessment. Review, validate, and "
    "supplement all outputs before use."
)

SENSITIVE_DATA_NOTICE = (
    "**Do not enter classified, personal, or otherwise sensitive "
    "information.** This tool is not authenticated and is not approved for "
    "security-classified or personal data - describe your project in "
    "general terms only."
)


def inject_noindex():
    # Best-effort: Streamlit doesn't give direct control over <head>, so this
    # is a secondary layer only. The unguessable per-assessment ID is the
    # real protection against a stray link being found or crawled.
    st.markdown(
        '<meta name="robots" content="noindex, nofollow">',
        unsafe_allow_html=True,
    )


def render_disclaimer():
    st.warning(DISCLAIMER_TEXT, icon="⚠️")


def render_sensitive_data_notice():
    st.error(SENSITIVE_DATA_NOTICE, icon="🔒")
