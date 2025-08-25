from django import template
from datetime import timedelta
from decimal import Decimal

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Replaces or adds query parameters to the current URL.
    e.g. {% url_replace page=5 %}
    """
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()

@register.simple_tag(takes_context=True)
def sort_url(context, field):
    """
    Generates a URL for sorting a table column, toggling the direction.
    e.g. {% sort_url 'title' %}
    """
    query = context['request'].GET.copy()
    current_sort_by = query.get('sort_by')
    current_sort_dir = query.get('sort_dir')

    query['sort_by'] = field
    if current_sort_by == field and current_sort_dir == 'asc':
        query['sort_dir'] = 'desc'
    else:
        query['sort_dir'] = 'asc'
        
    return query.urlencode()

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
