from django import template
from datetime import timedelta
from decimal import Decimal

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

@register.simple_tag
def url_replace(request, field, value, direction_field):
    """
    A template tag to help with building sorting URLs that preserve other GET parameters.
    """
    dict_ = request.GET.copy()
    
    # If the sort field is the same as the current one, toggle the direction
    if dict_.get(field) == value:
        if dict_.get(direction_field) == 'asc':
            dict_[direction_field] = 'desc'
        else:
            dict_[direction_field] = 'asc'
    # Otherwise, set a new sort field and default to ascending
    else:
        dict_[field] = value
        dict_[direction_field] = 'asc'
        
    return dict_.urlencode()

@register.simple_tag
def calculate_entry_price(entry, hourly_rate):
    """
    Calculate the price for a single time entry based on its worked duration and the project's hourly rate.
    """
    if not hourly_rate or not hasattr(entry, 'worked_duration'):
        return "0.00"
    
    hourly_rate = Decimal(hourly_rate)
    worked_hours = Decimal(entry.worked_duration.total_seconds()) / Decimal(3600)
    price = worked_hours * hourly_rate
    return f"{price:.2f}"
