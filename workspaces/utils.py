from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.conf import settings
from django.contrib.staticfiles import finders

def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access files
    like CSS and images. It looks for files in STATICFILES_DIRS and STATIC_ROOT.
    """
    # use STATIC_URL to convert URI to a relative path
    if uri.startswith(settings.STATIC_URL):
        path = uri.replace(settings.STATIC_URL, "")
    else:
        return uri # handle absolute URIs and other cases

    result = finders.find(path)
    if result:
        return result[0] if isinstance(result, (list, tuple)) else result
    return uri # Return the original URI if not found

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    # The encoding is important for handling different languages
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, link_callback=link_callback)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

def format_duration_hms(duration):
    """Formats a timedelta object into a string like '1h 2m 3s'."""
    if not duration or duration.total_seconds() < 0:
        return "0s"
    
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
        
    return " ".join(parts)
