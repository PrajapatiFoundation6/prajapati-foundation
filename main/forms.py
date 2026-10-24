import io
import re
from pathlib import Path

from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.validators import MaxLengthValidator, RegexValidator
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import ContactMessage, StudentHelp, Volunteer

PHONE_DB_MAX = 15  # models me phone max_length=15 hai

phone_validator = RegexValidator(
    regex=r"^\+?[0-9]{10,15}$",
    message="Valid phone number daalein (10-15 digits, shuru me + optional).",
)

MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB
MAX_PHOTO_DIMENSION = 1600        # lambi side px; R2 storage bhi bachta hai
IMAGE_FORMATS = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
}


def sanitize_image(upload):
    """
    Upload ko asli image se verify karta hai (client ke content_type par
    bharosa nahi), EXIF/GPS metadata hata deta hai, orientation sahi karta hai
    aur bahut badi photo ko chhota kar deta hai.
    """
    try:
        upload.seek(0)
        img = Image.open(upload)
        fmt = (img.format or "").upper()
        if fmt not in IMAGE_FORMATS:
            raise forms.ValidationError("Sirf JPG, PNG ya WEBP images allowed hain.")
        img.load()
    except forms.ValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise forms.ValidationError("Yeh valid image file nahi hai.")

    img = ImageOps.exif_transpose(img)
    img.thumbnail((MAX_PHOTO_DIMENSION, MAX_PHOTO_DIMENSION))

    out = io.BytesIO()
    if fmt == "JPEG":
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(out, "JPEG", quality=85, optimize=True)
    elif fmt == "PNG":
        img.save(out, "PNG", optimize=True)
    else:
        img.save(out, "WEBP", quality=85)

    ext, content_type = IMAGE_FORMATS[fmt]
    stem = Path(upload.name).stem[:60] or "photo"
    return SimpleUploadedFile(f"{stem}{ext}", out.getvalue(), content_type=content_type)


class BasePhoneForm(forms.ModelForm):
    """Shared phone/name validation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        phone = self.fields.get("phone")
        if phone:
            # "+91 98398-82438" jaisa input chalega; spaces/dashes clean_phone me hatenge.
            phone.validators = [v for v in phone.validators if not isinstance(v, MaxLengthValidator)]
            phone.max_length = None
            phone.widget.attrs["maxlength"] = "20"

    def clean_phone(self):
        raw = self.cleaned_data.get("phone", "") or ""
        phone = re.sub(r"[\s\-().]", "", raw)
        if len(phone) > PHONE_DB_MAX:
            raise forms.ValidationError("Phone number bahut lamba hai.")
        phone_validator(phone)
        return phone

    def clean_name(self):
        name = (self.cleaned_data.get("name", "") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Kripya apna poora naam daalein.")
        return name


class VolunteerForm(BasePhoneForm):
    class Meta:
        model = Volunteer
        fields = ["name", "email", "phone", "city", "contribution", "photo"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input-field", "placeholder": "Aapka poora naam", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"class": "input-field", "placeholder": "Email address", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"class": "input-field", "placeholder": "Mobile number", "autocomplete": "tel", "inputmode": "tel"}),
            "city": forms.TextInput(attrs={"class": "input-field", "placeholder": "Aapka shahar", "autocomplete": "address-level2"}),
            "contribution": forms.Textarea(attrs={"class": "input-field", "placeholder": "Teaching / Events / Fundraising / Social Media..."}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Template me email ke saamne * nahi hai, isliye optional rakha.
        self.fields["email"].required = False

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if not photo:
            raise forms.ValidationError("Kripya apni photo upload karein.")
        if photo.size > MAX_PHOTO_SIZE:
            raise forms.ValidationError("Photo 5MB se chhoti honi chahiye.")
        return sanitize_image(photo)


class StudentHelpForm(BasePhoneForm):
    class Meta:
        model = StudentHelp
        fields = ["name", "email", "phone", "city", "education_level", "help_type", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input-field", "placeholder": "Aapka naam", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"class": "input-field", "placeholder": "Email address", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"class": "input-field", "placeholder": "Mobile number", "autocomplete": "tel", "inputmode": "tel"}),
            "city": forms.TextInput(attrs={"class": "input-field", "placeholder": "Aapka shahar", "autocomplete": "address-level2"}),
            "education_level": forms.TextInput(attrs={"class": "input-field", "placeholder": "e.g. Class 12 / B.Tech / B.Pharm"}),
            "help_type": forms.TextInput(attrs={"class": "input-field", "placeholder": "Scholarship / Career / Admission..."}),
            "message": forms.Textarea(attrs={"class": "input-field", "placeholder": "Aapki problem ya request detail mein likhein..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Template me ye dono * ke saath hain, par model me blank=True tha.
        self.fields["education_level"].required = True
        self.fields["help_type"].required = True

    def clean_message(self):
        message = (self.cleaned_data.get("message", "") or "").strip()
        if len(message) < 10:
            raise forms.ValidationError("Kripya apni request thodi detail me likhein.")
        return message


class ContactForm(BasePhoneForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "subject", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input-field", "placeholder": "Aapka naam", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"class": "input-field", "placeholder": "Email address", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"class": "input-field", "placeholder": "Mobile number", "autocomplete": "tel", "inputmode": "tel"}),
            "subject": forms.TextInput(attrs={"class": "input-field", "placeholder": "Vishay kya hai?"}),
            "message": forms.Textarea(attrs={"class": "input-field", "placeholder": "Apni baat likhein..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = False  # template me email optional dikhta hai

    def clean_message(self):
        message = (self.cleaned_data.get("message", "") or "").strip()
        if len(message) < 5:
            raise forms.ValidationError("Message bahut chhota hai.")
        return message


# ── Admin bulk upload (admin.py ye import karta hai, isliye rakha hai) ─────
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return single_file_clean(data, initial)


class BulkGalleryUploadForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "vTextField", "placeholder": "Sabhi images ke liye common title"}),
    )
    images = MultipleFileField(
        widget=MultipleFileInput(attrs={"multiple": True, "accept": "image/*"}),
        label="Select multiple images",
    )