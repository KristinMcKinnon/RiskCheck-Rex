import secrets


def new_assessment_id() -> str:
    """Unguessable, non-sequential ID safe to put in a URL."""
    return secrets.token_urlsafe(16)
