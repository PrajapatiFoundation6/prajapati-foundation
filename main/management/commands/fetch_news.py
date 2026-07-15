from django.core.management.base import BaseCommand

from main.news_fetcher import fetch_news


class Command(BaseCommand):
    help = "Fetch the latest Prajapati/Kumhar/Mitti-kala news from RSS sources and save new articles."

    def handle(self, *args, **options):
        self.stdout.write("Fetching news...")
        stats = fetch_news()
        self.stdout.write(self.style.SUCCESS(
            f"Done. Added: {stats['added']}, Skipped: {stats['skipped']}, Errors: {stats['errors']}"
        ))
