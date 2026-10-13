from datetime import datetime

from src import settings


def format_rate_time(timestamp: str) -> str:
    """Convert the source timestamp, not the time the user sent the command."""
    observed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if observed.tzinfo is None:
        raise ValueError("Timestamp must include a UTC offset.")
    local = observed.astimezone(settings.DISPLAY_ZONE)
    offset = local.strftime("%z")
    offset = offset[:3] + ":" + offset[3:]
    return f"{local:%d/%m/%Y %H:%M:%S} ({settings.DISPLAY_TIMEZONE}, UTC{offset})"
