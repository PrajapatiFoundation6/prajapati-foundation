from django import forms
from django.core.validators import RegexValidator

from .models import ContactMessage, StudentHelp, Volunteer

phone_validator = RegexValidator(
    regex=r'^\+?[0-9]{10,15}$',
    message="Enter a valid phone number (10-15 digits, optional leading +).",
)

MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class BasePhoneForm(forms.ModelForm):
    """Shared phone-field validation + consistent widget styling."""

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        phone_validator(phone)
        return phone

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter your full name.")
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
            "photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if not photo:
            raise forms.ValidationError("Please upload a photo.")
        if photo.size > MAX_PHOTO_SIZE:
            raise forms.ValidationError("Photo must be smaller than 5MB.")
        content_type = getattr(photo, "content_type", "")
        if content_type and content_type not in ALLOWED_IMAGE_TYPES:
            raise forms.ValidationError("Only JPG, PNG or WEBP images are allowed.")
        return photo


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

    def clean_message(self):
        message = self.cleaned_data.get("message", "").strip()
        if len(message) < 10:
            raise forms.ValidationError("Please describe your request in a bit more detail.")
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

    def clean_message(self):
        message = self.cleaned_data.get("message", "").strip()
        if len(message) < 5:
            raise forms.ValidationError("Message is too short.")
        return message
