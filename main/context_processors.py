import json

from django.conf import settings


def site(request):
    s = settings
    url = s.SITE_URL
    whatsapp_url = "https://wa.me/" + s.SITE_PHONE.lstrip("+") if s.SITE_PHONE else ""
    same_as = [u for u in (s.SITE_FACEBOOK_URL, s.SITE_INSTAGRAM_URL, whatsapp_url) if u]

    org = {
        "@type": "NGO",
        "@id": f"{url}/#organization",
        "name": s.SITE_NAME,
        "alternateName": [s.SITE_NAME_HI],
        "url": f"{url}/",
        "logo": {
            "@type": "ImageObject",
            "url": f"{url}/favicon-192.png",
            "width": 192,
            "height": 192,
        },
        "description": (
            f"Prajapati Foundation ({s.SITE_CITY}, {s.SITE_STATE}) Kumhar (potter) samaj ke utthan "
            "ke liye samarpit ek sanstha hai — education, art preservation aur artisan support ke madhyam se."
        ),
        "telephone": s.SITE_PHONE,
        "address": {
            "@type": "PostalAddress",
            "addressLocality": s.SITE_CITY,
            "addressRegion": s.SITE_STATE,
            "addressCountry": "IN",
        },
        "areaServed": f"{s.SITE_CITY}, {s.SITE_STATE}, India",
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": s.SITE_PHONE,
            "contactType": "customer service",
            "areaServed": "IN",
            "availableLanguage": ["Hindi", "English"],
        },
        "sameAs": same_as,
    }
    graph = [org]

    # WebSite markup sirf homepage par (Google isi se brand/site name uthata hai)
    if request.path == "/":
        graph.append({
            "@type": "WebSite",
            "@id": f"{url}/#website",
            "url": f"{url}/",
            "name": s.SITE_NAME,
            "alternateName": [s.SITE_NAME_HI, f"{s.SITE_NAME} {s.SITE_CITY}"],
            "publisher": {"@id": f"{url}/#organization"},
        })

    jsonld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    jsonld = jsonld.replace("</", "<\\/")  # script tag band hone se bachao

    return {
        "site": {
            "name": s.SITE_NAME,
            "name_hi": s.SITE_NAME_HI,
            "city": s.SITE_CITY,
            "city_hi": s.SITE_CITY_HI,
            "state": s.SITE_STATE,
            "state_hi": s.SITE_STATE_HI,
            "phone": s.SITE_PHONE,
            "email": s.SITE_EMAIL,
            "facebook_url": s.SITE_FACEBOOK_URL,
            "instagram_url": s.SITE_INSTAGRAM_URL,
            "jsonld": jsonld,
        }
    }