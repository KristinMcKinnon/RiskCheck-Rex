import hashlib

import streamlit as st

from app_lib.db import increment_and_check_rate_limit

DAILY_LIMIT_PER_IP = 50


def _hashed_ip() -> str | None:
    """We hash the IP rather than storing it raw - we only need to tell
    'same visitor' apart from 'different visitor', not know who they are."""
    ip = getattr(st.context, "ip_address", None)
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def allow_generation(conn) -> bool:
    """Generous safety-net cap so a scraped/widely-shared link can't run up
    an unbounded Gemini bill. Fails open (allows the request) if the
    visitor's IP can't be determined, rather than blocking real users."""
    ip_hash = _hashed_ip()
    if ip_hash is None:
        return True
    return increment_and_check_rate_limit(conn, ip_hash, DAILY_LIMIT_PER_IP)
