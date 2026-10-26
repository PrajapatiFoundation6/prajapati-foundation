from datetime import timedelta

from django.utils import timezone

from .models import News, SchemeUpdate

KEEP_LATEST_NEWS = 100   # itni latest news kabhi delete nahi hogi (page khaali na ho)


def cleanup_old_entries(news_days=90, scheme_days=180, dry_run=False):
    """
    Purani auto-fetched entries delete karo.
    created_at (jab hamare DB me aayi) use karte hain, published_date nahi,
    warna RSS me bachi purani khabar har fetch pe wapas aati aur delete hoti rehti.
    """
    now = timezone.now()

    keep_ids = list(
        News.objects.order_by("-published_date").values_list("id", flat=True)[:KEEP_LATEST_NEWS]
    )
    news_qs = News.objects.filter(
        created_at__lt=now - timedelta(days=news_days)
    ).exclude(id__in=keep_ids)

    scheme_qs = SchemeUpdate.objects.filter(
        created_at__lt=now - timedelta(days=scheme_days)
    )

    result = {"news": news_qs.count(), "scheme_updates": scheme_qs.count()}

    if not dry_run:
        news_qs.delete()
        scheme_qs.delete()

    return result