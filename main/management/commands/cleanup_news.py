from django.core.management.base import BaseCommand

from main.cleanup import SCHEME_RETENTION_DAYS, cleanup_old_entries, purge_irrelevant_news
from main.news_sources import RETENTION_DAYS


class Command(BaseCommand):
    help = (
        f"{RETENTION_DAYS} din se purani News aur purane SchemeUpdate delete karta hai. "
        "--purge-irrelevant: non-Prajapati news bhi hatata hai aur categories normalize karta hai."
    )

    def add_arguments(self, parser):
        parser.add_argument("--news-days", type=int, default=RETENTION_DAYS)
        parser.add_argument("--scheme-days", type=int, default=SCHEME_RETENTION_DAYS)
        parser.add_argument("--purge-irrelevant", action="store_true",
                            help="Ek-baar ki safai: non-Prajapati news delete + categories normalize")
        parser.add_argument("--dry-run", action="store_true", help="Sirf count dikhao, delete mat karo")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        verb = "Delete hoti" if dry else "Delete hui"

        if opts["purge_irrelevant"]:
            r = purge_irrelevant_news(dry_run=dry)
            self.stdout.write(self.style.SUCCESS(
                f"Irrelevant news {verb.lower()}: {r['deleted']}, category badli: {r['recategorized']}"
            ))

        result = cleanup_old_entries(
            news_days=opts["news_days"],
            scheme_days=opts["scheme_days"],
            dry_run=dry,
        )
        self.stdout.write(self.style.SUCCESS(
            f"{verb}: news={result['news']}, scheme_updates={result['scheme_updates']}"
        ))