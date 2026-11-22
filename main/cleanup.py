from datetime import timedelta

from django.utils import timezone

from .models import News, SchemeUpdate
from .news_sources import RETENTION_DAYS, classify, is_relevant

SCHEME_RETENTION_DAYS = 180


def cleanup_old_entries(news_days=RETENTION_DAYS, scheme_days=SCHEME_RETENTION_DAYS, dry_run=False):
    """
    News: published_date `news_days` (default 15) din se purani -> delete.
      Fetcher bhi itni purani news kabhi save nahi karta, isliye woh wapas nahi aati.
    SchemeUpdate: created_at `scheme_days` se purani -> delete (scheme_fetcher ka
      apna MAX_AGE_DAYS cutoff alag chalta hai).
    """
    now = timezone.now()

    news_qs = News.objects.filter(published_date__lt=now - timedelta(days=news_days))
    scheme_qs = SchemeUpdate.objects.filter(created_at__lt=now - timedelta(days=scheme_days))

    result = {"news": news_qs.count(), "scheme_updates": scheme_qs.count()}

    if not dry_run:
        news_qs.delete()
        scheme_qs.delete()

    return result


def purge_irrelevant_news(dry_run=False):
    """
    Ek-baar ka safai: purani broad filters se aayi non-Prajapati news hatao,
    aur bachi hui ki category naye 3 chips (रायबरेली / प्रजापति समाज / कुम्हार समाज)
    me normalize karo.
    """
    delete_ids = []
    recategorized = 0

    for n in News.objects.only("id", "title", "description", "category"):
        text = f"{n.title} {n.description}"
        if not is_relevant(text):
            delete_ids.append(n.id)
            continue
        new_cat = classify(text)
        if new_cat != n.category:
            recategorized += 1
            if not dry_run:
                News.objects.filter(pk=n.pk).update(category=new_cat)

    if delete_ids and not dry_run:
        News.objects.filter(id__in=delete_ids).delete()

    return {"deleted": len(delete_ids), "recategorized": recategorized}