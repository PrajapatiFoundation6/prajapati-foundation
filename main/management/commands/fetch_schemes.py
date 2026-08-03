from django.core.management.base import BaseCommand
from main.scheme_fetcher import fetch_scheme_updates


class Command(BaseCommand):
    help = "Fetch latest government scheme announcements from PIB RSS feed"

    def handle(self, *args, **options):
        stats = fetch_scheme_updates()
        self.stdout.write(self.style.SUCCESS(
            f"Scheme updates fetched — added: {stats['added']}, "
            f"skipped: {stats['skipped']}, errors: {stats['errors']}"
        ))