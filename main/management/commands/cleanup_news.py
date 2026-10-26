from django.core.management.base import BaseCommand

from main.cleanup import cleanup_old_entries


class Command(BaseCommand):
    help = "Purani auto-fetched News aur SchemeUpdate entries delete karta hai."

    def add_arguments(self, parser):
        parser.add_argument("--news-days", type=int, default=90)
        parser.add_argument("--scheme-days", type=int, default=180)
        parser.add_argument("--dry-run", action="store_true", help="Sirf count dikhao, delete mat karo")

    def handle(self, *args, **opts):
        result = cleanup_old_entries(
            news_days=opts["news_days"],
            scheme_days=opts["scheme_days"],
            dry_run=opts["dry_run"],
        )
        verb = "Delete hoti" if opts["dry_run"] else "Delete hui"
        self.stdout.write(self.style.SUCCESS(
            f"{verb}: news={result['news']}, scheme_updates={result['scheme_updates']}"
        ))