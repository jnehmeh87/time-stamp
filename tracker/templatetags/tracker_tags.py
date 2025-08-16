from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def human_duration(value):
    if not isinstance(value, timedelta):
        return value
    
    total_seconds = int(value.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return f'{hours}h {minutes}m {seconds}s'
