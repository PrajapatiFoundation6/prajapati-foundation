from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        # (url_name, priority)
        return [
            ("home", 1.0),
            ("about", 0.8),
            ("education", 0.8),
            ("gallery", 0.7),
            ("news", 0.9),
            ("donation", 0.9),
            ("join", 0.7),
            ("contact", 0.6),
            (""artisan_support", 0.7")
        ]

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]