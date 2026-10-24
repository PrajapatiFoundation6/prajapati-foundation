import json

from django.conf import settings

# settings.py me value na mile to ye defaults use honge (site crash nahi hogi)
_DEFAULTS = {
    "SITE_URL": "https://www.prajapatifoundation.in",
    "SITE_NAME": "Prajapati Foundation",
    "SITE_NAME_HI": "प्रजापति फाउंडेशन",
    "SITE_CITY": "Raebareli",
    "SITE_CITY_HI": "रायबरेली",
    "SITE_STATE": "Uttar Pradesh",
    "SITE_STATE_HI": "उत्तर प्रदेश",
    "SITE_PHONE": "+919839882438",
    "SITE_EMAIL": "info@prajapatifoundation.org",
    "SITE_FACEBOOK_URL": "",
    "SITE_INSTAGRAM_URL": "",
}


def site(request):
    v = {name: getattr(settings, name, default) for name, default in _DEFAULTS.items()}
    url = v["SITE_URL"].rstrip("/")
    phone = v["SITE_PHONE"]

    whatsapp_url = "https://wa.me/" + phone.lstrip("+") if phone else ""
    same_as = [u for u in (v["SITE_FACEBOOK_URL"], v["SITE_INSTAGRAM_URL"], whatsapp_url) if u]

    org = {
        "@type": "NGO",
        "@id": f"{url}/#organization",
        "name": v["SITE_NAME"],
        "alternateName": [v["SITE_NAME_HI"]],
        "url": f"{url}/",
        "logo": {
            "@type": "ImageObject",
            "url": f"{url}/favicon-192.png",
            "width": 192,
            "height": 192,
        },
        "description": (
            f"Prajapati Foundation ({v['SITE_CITY']}, {v['SITE_STATE']}) Kumhar (potter) samaj ke utthan "
            "ke liye samarpit ek sanstha hai — education, art preservation aur artisan support ke madhyam se."
        ),
        "telephone": phone,
        "address": {
            "@type": "PostalAddress",
            "addressLocality": v["SITE_CITY"],
            "addressRegion": v["SITE_STATE"],
            "addressCountry": "IN",
        },
        "areaServed": f"{v['SITE_CITY']}, {v['SITE_STATE']}, India",
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": phone,
            "contactType": "customer service",
            "areaServed": "IN",
            "availableLanguage": ["Hindi", "English"],
        },
        "sameAs": same_as,
    }
    graph = [org]

    # WebSite markup sirf homepage par (Google isi se site/brand name uthata hai)
    if request.path == "/":
        graph.append({
            "@type": "WebSite",
            "@id": f"{url}/#website",
            "url": f"{url}/",
            "name": v["SITE_NAME"],
            "alternateName": [v["SITE_NAME_HI"], f"{v['SITE_NAME']} {v['SITE_CITY']}"],
            "publisher": {"@id": f"{url}/#organization"},
        })

    jsonld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    jsonld = jsonld.replace("</", "<\\/")  # script tag band hone se bachao

    return {
        "site": {
            "name": v["SITE_NAME"],
            "name_hi": v["SITE_NAME_HI"],
            "city": v["SITE_CITY"],
            "city_hi": v["SITE_CITY_HI"],
            "state": v["SITE_STATE"],
            "state_hi": v["SITE_STATE_HI"],
            "phone": phone,
            "email": v["SITE_EMAIL"],
            "facebook_url": v["SITE_FACEBOOK_URL"],
            "instagram_url": v["SITE_INSTAGRAM_URL"],
            "jsonld": jsonld,
        }
    }