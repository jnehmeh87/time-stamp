from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def human_duration(duration):
    """
    Formats a timedelta object into a human-readable string like:
    - 1h 3m 20s
    - 2m 30s
    - 13s
    """
    if not isinstance(duration, timedelta):
        return ""

    total_seconds = int(duration.total_seconds())
    
    if total_seconds < 0:
        return "0s"

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts: # Always show seconds if it's the only unit
        parts.append(f"{seconds}s")

    return " ".join(parts)
