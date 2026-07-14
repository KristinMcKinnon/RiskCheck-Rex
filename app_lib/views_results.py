import pandas as pd
import streamlit as st

from app_lib import db
from app_lib.components import LOGO_ICON_PATH, render_disclaimer
from app_lib.export import build_workbook


def _list_to_lines(items) -> str:
    return "\n".join(items or [])


def _lines_to_list(text) -> list:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def render_results_page(conn, record: dict):
    results = record["results"]

    icon_col, title_col = st.columns([1, 9], vertical_alignment="center")
    icon_col.image(str(LOGO_ICON_PATH))
    title_col.title("RiskCheck Rex - Preliminary Results")
    render_disclaimer()

    st.info(
        "This page's URL is your link back to this assessment for the "
        "next 30 days of inactivity. Bookmark it if you want to return.",
        icon="🔖",
    )

    if st.button("✏️ Edit project inputs & regenerate"):
        st.session_state["force_edit"] = True
        st.rerun()

    st.divider()
    st.subheader("Risks")
    st.caption(
        "Each description follows the format: X (threat/cause) causes Y "
        "(risk event) resulting in Z (consequence). No likelihood, "
        "consequence, or overall rating is provided - rating against your "
        "organisation's own risk criteria is a separate, later step."
    )
    risk_rows = [
        {
            "ID": r.get("id", ""),
            "Category": r.get("category", ""),
            "Description": r.get("description", ""),
            "Suggested controls": _list_to_lines(r.get("suggested_controls")),
        }
        for r in results.get("risks", [])
    ]
    risk_df = pd.DataFrame(risk_rows, columns=["ID", "Category", "Description", "Suggested controls"])
    edited_risks = st.data_editor(
        risk_df,
        num_rows="dynamic",
        width="stretch",
        key="risk_editor",
        column_config={
            "Description": st.column_config.TextColumn(width="large"),
            "Suggested controls": st.column_config.TextColumn(
                width="large", help="One control per line"
            ),
        },
    )

    st.subheader("Opportunities")
    st.caption("Potential positive effects of uncertainty worth pursuing deliberately.")
    opp_rows = [
        {
            "ID": o.get("id", ""),
            "Description": o.get("description", ""),
            "Suggested actions": _list_to_lines(o.get("suggested_actions")),
        }
        for o in results.get("opportunities", [])
    ]
    opp_df = pd.DataFrame(opp_rows, columns=["ID", "Description", "Suggested actions"])
    edited_opps = st.data_editor(
        opp_df,
        num_rows="dynamic",
        width="stretch",
        key="opp_editor",
        column_config={
            "Description": st.column_config.TextColumn(width="large"),
            "Suggested actions": st.column_config.TextColumn(
                width="large", help="One action per line"
            ),
        },
    )

    st.subheader("Probing Questions for Further Consideration")
    st.caption(
        "Open questions to help you surface risks the AI may have missed, "
        "given the limits of the input it was given."
    )
    question_df = pd.DataFrame(
        {"Question": results.get("probing_questions", [])}
    )
    edited_questions = st.data_editor(
        question_df,
        num_rows="dynamic",
        width="stretch",
        key="question_editor",
        column_config={"Question": st.column_config.TextColumn(width="large")},
    )

    st.divider()
    col1, col2 = st.columns(2)

    updated_results = {
        "risks": [
            {
                "id": row["ID"] or f"R{i}",
                "category": row["Category"],
                "description": row["Description"],
                "suggested_controls": _lines_to_list(row["Suggested controls"]),
                "assumptions": next(
                    (r.get("assumptions", []) for r in results.get("risks", []) if r.get("id") == row["ID"]),
                    [],
                ),
            }
            for i, row in enumerate(edited_risks.to_dict("records"), start=1)
            if row.get("Description")
        ],
        "opportunities": [
            {
                "id": row["ID"] or f"O{i}",
                "description": row["Description"],
                "suggested_actions": _lines_to_list(row["Suggested actions"]),
                "assumptions": next(
                    (o.get("assumptions", []) for o in results.get("opportunities", []) if o.get("id") == row["ID"]),
                    [],
                ),
            }
            for i, row in enumerate(edited_opps.to_dict("records"), start=1)
            if row.get("Description")
        ],
        "probing_questions": [
            row["Question"]
            for row in edited_questions.to_dict("records")
            if row.get("Question")
        ],
    }

    if col1.button("💾 Save my edits", width="stretch"):
        db.save_results(conn, record["id"], updated_results)
        st.success("Changes saved.")

    workbook = build_workbook(updated_results)
    col2.download_button(
        "⬇️ Export to Excel (.xlsx)",
        data=workbook,
        file_name="riskcheck-rex-preliminary-risk-register.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

    render_disclaimer()
