from django.core.management.base import BaseCommand

from main.news_fetcher import run_news_job


class Command(BaseCommand):
    help = "Prajapati samaj ki latest news fetch karta hai aur 15 din se purani news delete karta hai."

    def handle(self, *args, **options):
        self.stdout.write("News fetch ho rahi hai...")
        stats = run_news_job()
        self.stdout.write(self.style.SUCCESS(
            f"Done. Added: {stats.get('added', 0)}, Skipped: {stats.get('skipped', 0)}, "
            f"Errors: {stats.get('errors', 0)}, Cleanup: {stats.get('cleanup')}"
        ))