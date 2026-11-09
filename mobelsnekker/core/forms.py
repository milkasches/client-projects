import os

from django import forms
from django.conf import settings

from .models import ConsultationRequest, Order

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".gif", ".pdf"}


class HoneypotMixin(forms.Form):
    website = forms.CharField(required=False)  # bots fill this in
    consent = forms.BooleanField(required=True, error_messages={"required": "Please accept the privacy terms."})

    def is_bot(self):
        return bool(self.data.get("website"))


class OrderForm(HoneypotMixin, forms.ModelForm):
    estimate = forms.CharField(required=False)  # JSON from the calculator (re-computed server side)

    class Meta:
        model = Order
        fields = ["name", "email", "phone", "preferred_time", "description", "delivery", "address"]

    def clean(self):
        data = super().clean()
        if not data.get("description") and not self.data.get("estimate"):
            self.add_error("description", "Please describe your project.")
        if data.get("delivery") and not data.get("address"):
            self.add_error("address", "Please enter the delivery address.")
        return data


def validate_files(files):
    errors = []
    if len(files) > settings.MAX_ATTACHMENTS:
        errors.append(f"Max {settings.MAX_ATTACHMENTS} files.")
    for f in files:
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in ALLOWED_EXT:
            errors.append(f"{f.name}: file type not allowed.")
        if f.size > settings.MAX_ATTACHMENT_MB * 1024 * 1024:
            errors.append(f"{f.name}: larger than {settings.MAX_ATTACHMENT_MB} MB.")
    return errors


class ConsultationForm(HoneypotMixin, forms.ModelForm):
    class Meta:
        model = ConsultationRequest
        fields = ["name", "phone", "email", "contact_method", "preferred_date", "preferred_slot", "topic", "message"]

    def clean(self):
        data = super().clean()
        if data.get("contact_method") == "email" and not data.get("email"):
            self.add_error("email", "Enter your email if you want us to answer by email.")
        return data
