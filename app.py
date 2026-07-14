import random

import streamlit as st

from app_lib import db
from app_lib.components import LOGO_ICON_PATH, LOGO_PATH, inject_noindex
from app_lib.views_input import render_input_form
from app_lib.views_results import render_results_page

st.set_page_config(page_title="RiskCheck Rex", page_icon=str(LOGO_ICON_PATH), layout="wide")
inject_noindex()

conn = db.get_connection()

# Cheap opportunistic cleanup of drafts past their 30-day expiry - no need
# for a separate scheduled job for a low-traffic tool, so we just do it
# occasionally as a side effect of a normal page view.
if random.random() < 0.02:
    db.purge_expired(conn)

with st.sidebar:
    st.image(str(LOGO_PATH), use_container_width=True)
    st.caption("Preliminary, AI-assisted risk brainstorming for project teams.")
    if st.button("➕ Start a new blank assessment", use_container_width=True):
        st.query_params.clear()
        st.session_state["force_edit"] = False
        st.rerun()

assessment_id = st.query_params.get("id")
record = db.get_assessment(conn, assessment_id) if assessment_id else None

if assessment_id and record is None:
    st.warning(
        "We couldn't find that assessment - the link may be wrong, or it "
        "may have expired after 30 days of inactivity. Starting a new one "
        "below.",
        icon="ℹ️",
    )
    st.query_params.clear()

force_edit = st.session_state.get("force_edit", False)

if record and record["status"] == "generated" and not force_edit:
    render_results_page(conn, record)
else:
    render_input_form(conn, existing=record)
