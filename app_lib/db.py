import json
import os
from datetime import datetime, timedelta, timezone

import libsql
import streamlit as st

DRAFT_EXPIRY_DAYS = 30


@st.cache_resource
def get_connection():
    """One shared connection per running app instance.

    Uses a real Turso database in production (via secrets), or falls back
    to a local SQLite file for local development if Turso secrets aren't
    configured yet.
    """
    db_url = st.secrets.get("TURSO_DATABASE_URL", "")
    auth_token = st.secrets.get("TURSO_AUTH_TOKEN", "")

    if db_url:
        conn = libsql.connect(database=db_url, auth_token=auth_token)
    else:
        os.makedirs(".local_data", exist_ok=True)
        conn = libsql.connect(database="file:.local_data/riskcheck_dev.db")

    _init_schema(conn)
    return conn


def _init_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS assessments (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            project_description TEXT NOT NULL DEFAULT '',
            in_scope TEXT NOT NULL DEFAULT '',
            out_of_scope TEXT NOT NULL DEFAULT '',
            methodology TEXT NOT NULL DEFAULT '',
            change_impacts TEXT NOT NULL DEFAULT '',
            results_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_limits (
            ip_hash TEXT NOT NULL,
            day TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (ip_hash, day)
        )
        """
    )
    conn.commit()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


FIELDS = (
    "project_description",
    "in_scope",
    "out_of_scope",
    "methodology",
    "change_impacts",
)


def create_draft(conn, inputs: dict) -> str:
    from app_lib.ids import new_assessment_id

    assessment_id = new_assessment_id()
    now = _now_iso()
    conn.execute(
        """
        INSERT INTO assessments
            (id, created_at, updated_at, status,
             project_description, in_scope, out_of_scope, methodology, change_impacts)
        VALUES (?, ?, ?, 'draft', ?, ?, ?, ?, ?)
        """,
        (
            assessment_id,
            now,
            now,
            inputs.get("project_description", ""),
            inputs.get("in_scope", ""),
            inputs.get("out_of_scope", ""),
            inputs.get("methodology", ""),
            inputs.get("change_impacts", ""),
        ),
    )
    conn.commit()
    return assessment_id


def update_inputs(conn, assessment_id: str, inputs: dict) -> None:
    conn.execute(
        """
        UPDATE assessments
        SET updated_at = ?, project_description = ?, in_scope = ?,
            out_of_scope = ?, methodology = ?, change_impacts = ?
        WHERE id = ?
        """,
        (
            _now_iso(),
            inputs.get("project_description", ""),
            inputs.get("in_scope", ""),
            inputs.get("out_of_scope", ""),
            inputs.get("methodology", ""),
            inputs.get("change_impacts", ""),
            assessment_id,
        ),
    )
    conn.commit()


def save_results(conn, assessment_id: str, results: dict) -> None:
    conn.execute(
        """
        UPDATE assessments
        SET updated_at = ?, status = 'generated', results_json = ?
        WHERE id = ?
        """,
        (_now_iso(), json.dumps(results), assessment_id),
    )
    conn.commit()


def touch(conn, assessment_id: str) -> None:
    """Bump updated_at (e.g. after the user edits results) to extend expiry."""
    conn.execute(
        "UPDATE assessments SET updated_at = ? WHERE id = ?",
        (_now_iso(), assessment_id),
    )
    conn.commit()


def get_assessment(conn, assessment_id: str):
    cur = conn.execute(
        """
        SELECT id, created_at, updated_at, status,
               project_description, in_scope, out_of_scope, methodology, change_impacts,
               results_json
        FROM assessments WHERE id = ?
        """,
        (assessment_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None

    updated_at = datetime.fromisoformat(row[2])
    if datetime.now(timezone.utc) - updated_at > timedelta(days=DRAFT_EXPIRY_DAYS):
        return None

    record = {
        "id": row[0],
        "created_at": row[1],
        "updated_at": row[2],
        "status": row[3],
        "project_description": row[4],
        "in_scope": row[5],
        "out_of_scope": row[6],
        "methodology": row[7],
        "change_impacts": row[8],
        "results": json.loads(row[9]) if row[9] else None,
    }
    return record


def purge_expired(conn) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=DRAFT_EXPIRY_DAYS)).isoformat()
    cur = conn.execute("DELETE FROM assessments WHERE updated_at < ?", (cutoff,))
    conn.commit()
    return cur.rowcount if cur.rowcount is not None else 0


def increment_and_check_rate_limit(conn, ip_hash: str, limit: int) -> bool:
    """Returns True if this request is allowed under today's cap."""
    today = datetime.now(timezone.utc).date().isoformat()
    conn.execute(
        """
        INSERT INTO rate_limits (ip_hash, day, count) VALUES (?, ?, 1)
        ON CONFLICT(ip_hash, day) DO UPDATE SET count = count + 1
        """,
        (ip_hash, today),
    )
    conn.commit()
    cur = conn.execute(
        "SELECT count FROM rate_limits WHERE ip_hash = ? AND day = ?",
        (ip_hash, today),
    )
    row = cur.fetchone()
    count = row[0] if row else 1
    return count <= limit
