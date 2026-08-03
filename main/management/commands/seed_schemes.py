from django.core.management.base import BaseCommand
from main.models import GovScheme

SCHEMES = [
    dict(
        name="PM Vishwakarma Yojana",
        category="artisan",
        department="Ministry of MSME",
        short_description="Kumhar samaj samet 18 traditional trades ke artisans/craftspeople ke liye end-to-end support — recognition, skill training, toolkit incentive aur collateral-free loans.",
        eligibility="18+ age, ek traditional family-based trade (jaise mitti/kumhar kaam) mein lage artisan/craftsperson.",
        benefits="₹15,000 tak toolkit incentive, skill training + stipend, ₹1 lakh + ₹2 lakh tak collateral-free loan (2 phase), digital transaction incentive, marketing support.",
        official_link="https://pmvishwakarma.gov.in",
        priority=100,
    ),
    dict(
        name="PMEGP — Prime Minister's Employment Generation Programme",
        category="artisan",
        department="KVIC / Ministry of MSME",
        short_description="Naya micro-enterprise/self-employment unit shuru karne ke liye credit-linked subsidy — Kumhar pottery units ke liye bhi applicable.",
        eligibility="18+ age, 8th pass (₹10L+ manufacturing / ₹5L+ service projects ke liye), naya unit (existing/already-subsidized unit eligible nahi).",
        benefits="Manufacturing ₹50 lakh tak, Service ₹20 lakh tak; margin money subsidy 15%–35%.",
        official_link="https://www.kviconline.gov.in/pmegpeportal/",
        priority=95,
    ),
    dict(
        name="myScheme — Government Schemes Search Portal",
        category="artisan",
        department="Digital India / NeGD",
        short_description="Central aur State ki 1000+ schemes ek jagah — apni details daalkar apne liye eligible schemes dhoondh sakte hain.",
        eligibility="Sabke liye — personalized results demographic details ke basis par.",
        benefits="Single search portal, eligibility checker, direct application links.",
        official_link="https://www.myscheme.gov.in",
        priority=80,
    ),
    dict(
        name="National Scholarship Portal (NSP)",
        category="scholarship",
        department="Ministry of Electronics & IT",
        short_description="Central aur State scholarships (pre-matric, post-matric, merit-cum-means, OBC/minority scholarships) ke liye single application portal.",
        eligibility="School/college students — scheme-wise category, income aur academic criteria alag-alag.",
        benefits="Direct Benefit Transfer se scholarship amount seedha bank account mein.",
        official_link="https://scholarships.gov.in",
        priority=90,
    ),
    dict(
        name="Startup India",
        category="startup",
        department="DPIIT, Ministry of Commerce & Industry",
        short_description="Naye business/startup ke liye recognition, tax benefits, funding access aur compliance support.",
        eligibility="Incorporated entity, 10 saal se kam purana, turnover ₹100 crore se kam, innovative product/service.",
        benefits="Tax exemption, self-certification compliance, IPR fast-tracking, funding schemes tak access.",
        official_link="https://www.startupindia.gov.in",
        priority=70,
    ),
    dict(
        name="Startup India Seed Fund Scheme (SISFS)",
        category="startup",
        department="DPIIT",
        short_description="Early-stage startups ke liye proof-of-concept, prototype development aur market entry ke liye seed funding.",
        eligibility="DPIIT-recognized startup — exact tenure/turnover criteria official site par check karein, yeh update hoti rehti hai.",
        benefits="₹20 lakh tak grant + ₹50 lakh tak debt/convertible debenture, incubator ke through disbursed.",
        official_link="https://seedfund.startupindia.gov.in",
        priority=65,
    ),
    dict(
        name="PM Mudra Yojana (PMMY)",
        category="startup",
        department="Dept. of Financial Services, Ministry of Finance",
        short_description="Chhoti business/artisan units (non-farm) ke liye collateral-free loans — Shishu, Kishore, Tarun categories mein.",
        eligibility="Koi bhi Indian citizen jiske paas non-farm income-generating business plan ho.",
        benefits="₹20 lakh tak collateral-free loan, bank/NBFC/MFI ke through.",
        official_link="https://www.mudra.org.in",
        priority=60,
    ),
    dict(
        name="Skill India Digital Hub (PMKVY 4.0)",
        category="youth",
        department="Ministry of Skill Development & Entrepreneurship",
        short_description="Free short-term skill training, certification aur job placement support — youth ke liye unified platform.",
        eligibility="15–45 age group, Aadhaar-linked mobile number.",
        benefits="Free training, certification, cash incentive (batch ke hisaab se), placement support.",
        official_link="https://www.skillindiadigital.gov.in/pmkvy-landing",
        priority=75,
    ),
]


class Command(BaseCommand):
    help = "Seed/update the curated Artisan Support gov-scheme list (safe to re-run)"

    def handle(self, *args, **options):
        created = updated = 0
        for data in SCHEMES:
            obj, was_created = GovScheme.objects.update_or_create(
                name=data["name"], defaults=data
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(self.style.SUCCESS(f"Schemes seeded — created: {created}, updated: {updated}"))