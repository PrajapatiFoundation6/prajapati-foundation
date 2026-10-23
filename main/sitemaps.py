from django.contrib.sitemaps import Sitemap
from django.urls import reverse

PAGES = {
    "home": 1.0,
    "news": 0.9,
    "donation": 0.9,
    "about": 0.8,
    "education": 0.8,
    "artisan_support": 0.7,
    "gallery": 0.7,
    "join": 0.7,
    "contact": 0.6,
    "volunteers": 0.5,
}


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        return list(PAGES)          # sirf url names (strings)

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return PAGES[item]