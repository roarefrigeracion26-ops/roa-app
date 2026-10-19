"""
URL configuration for ROA APP (SGMAA).
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include


def _media_patterns():
    if settings.DEBUG:
        return static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    return []


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('', include('inventory.urls')),
    path('', include('operations.urls')),
    path('', include('analytics.urls')),
]

urlpatterns += _media_patterns()
