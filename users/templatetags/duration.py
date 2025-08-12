from django import template

register = template.Library()

@register.filter
def human_duration(value):
    if not value:
        return ""
    total = int(getattr(value, 'total_seconds', lambda: 0)())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s"
