import os


def configured_admin_emails() -> set[str]:
    """Return normalized admin addresses from current and legacy env vars."""
    configured_values = (
        os.getenv("ADMIN_EMAILS", ""),
        os.getenv("ADMIN_EMAIL", ""),
    )
    return {
        email.strip().casefold()
        for value in configured_values
        for email in value.split(",")
        if email.strip()
    }
