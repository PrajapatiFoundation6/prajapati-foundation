import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from main.sitemaps import StaticViewSitemap

sitemaps = {"static": StaticViewSitemap}

# Default /admin/ par bots roz attack karte hain. Railway me ADMIN_URL set karo,
# e.g. ADMIN_URL=pf-manage-7x2k/  (end me / zaroori hai)
ADMIN_URL = os.environ.get("ADMIN_URL", "admin/")

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path('', include('main.urls')),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain"), name='robots_txt'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)