import uuid
from pathlib import PurePath

from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models

IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']


def donor_photo_path(instance, filename):
    return f"donors/{uuid.uuid4().hex}{PurePath(filename).suffix.lower()}"


def donor_proof_path(instance, filename):
    # random naam, taaki payment screenshot ka URL guess na ho sake
    return f"donation_proofs/{uuid.uuid4().hex}{PurePath(filename).suffix.lower()}"


class GalleryImage(models.Model):

    title = models.CharField(max_length=200)
    image = models.ImageField(
        upload_to='gallery/',
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title


class Volunteer(models.Model):

    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    city = models.CharField(max_length=100)
    contribution = models.TextField()
    photo = models.ImageField(
        upload_to='volunteers/',
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
    )
    approved = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.name


class StudentHelp(models.Model):

    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15)
    city = models.CharField(max_length=100)

    education_level = models.CharField(max_length=100, blank=True, default="")
    help_type = models.CharField(max_length=200, blank=True, default="")

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ContactMessage(models.Model):

    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Donation(models.Model):
    """Razorpay-based donations (abhi use me nahi, KYC ke baad wapas use hoga)."""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    amount = models.IntegerField()
    razorpay_order_id = models.CharField(max_length=200, blank=True, default="")
    payment_id = models.CharField(max_length=200, unique=True)
    show_public = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DonationProof(models.Model):
    """Manual UPI QR donations: donor details + screenshot, admin verify karta hai."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    amount = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    transaction_id = models.CharField(max_length=100, blank=True, default="")

    photo = models.ImageField(
        upload_to=donor_photo_path, blank=True,
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
    )
    screenshot = models.ImageField(
        upload_to=donor_proof_path,
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
    )

    wants_public = models.BooleanField(default=False)   # donor ki request
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending", db_index=True)
    show_public = models.BooleanField(default=False)    # admin decide karega
    admin_note = models.CharField(max_length=300, blank=True, default="")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.name} — ₹{self.amount} ({self.status})"


class GovScheme(models.Model):
    """Curated (admin-managed) list of real government schemes shown on
    the Artisan Support page. Manually verified so links are always
    genuine — auto-fetched updates (SchemeUpdate below) sit alongside
    these as fresh news."""

    CATEGORY_CHOICES = [
        ("artisan", "Artisan / Kumhar Samaj"),
        ("youth", "Youth / Skill Development"),
        ("startup", "Startup / Business"),
        ("scholarship", "Scholarship / Education"),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    department = models.CharField(max_length=200, blank=True, default="")
    short_description = models.TextField()
    eligibility = models.TextField(blank=True, default="")
    benefits = models.TextField(blank=True, default="")
    official_link = models.URLField()
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=0, help_text="Higher number shows first")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'name']

    def __str__(self):
        return self.name


class SchemeUpdate(models.Model):
    """Auto-fetched scheme-related announcements from PIB RSS
    (see main/scheme_fetcher.py) — keeps the Artisan Support page
    'automatically updating' without manual work."""

    title = models.CharField(max_length=500)
    source_link = models.URLField(unique=True, max_length=800)
    category = models.CharField(max_length=100, blank=True, default="")
    published_date = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_date']

    def __str__(self):
        return self.title


class News(models.Model):

    title = models.CharField(max_length=800)
    description = models.TextField(blank=True)
    image = models.URLField(blank=True)
    source_link = models.URLField(unique=True, max_length=800)
    category = models.CharField(max_length=100, blank=True, db_index=True)
    published_date = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_date']

    def __str__(self):
        return self.title