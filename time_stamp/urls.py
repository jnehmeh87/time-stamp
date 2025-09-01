from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from tracker.views import CustomLoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Override the default allauth login URL with our custom view.
    # This MUST come BEFORE the include('allauth.urls') line.
    path('accounts/login/', CustomLoginView.as_view(), name='account_login'),

    # Include the rest of the allauth URLs for signup, password reset, etc.
    path('accounts/', include('allauth.urls')),

    # Include your main application's URLs
    path('', include('tracker.urls', namespace='tracker')),
]

# This is standard practice for serving media files during development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

