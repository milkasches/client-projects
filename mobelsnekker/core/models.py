import os
import uuid

from django.db import models


class Status(models.TextChoices):
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    QUOTED = "quoted", "Quote sent"
    WON = "won", "Accepted / in work"
    DONE = "done", "Done"
    LOST = "lost", "Lost / cancelled"


class Order(models.Model):
    class Source(models.TextChoices):
        CONTACT_FORM = "form", "Contact form"
        CALCULATOR = "calculator", "Price calculator"

    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.CONTACT_FORM)

    name = models.CharField(max_length=120)
    email = models.EmailField(max_length=200)
    phone = models.CharField(max_length=40)
    preferred_time = models.CharField(max_length=120, blank=True)
    description = models.TextField(max_length=4000, blank=True)
    delivery = models.BooleanField(default=False)
    address = models.CharField(max_length=300, blank=True)

    estimate = models.JSONField(null=True, blank=True)
    estimate_low = models.PositiveIntegerField(null=True, blank=True)
    estimate_high = models.PositiveIntegerField(null=True, blank=True)

    internal_notes = models.TextField(blank=True, help_text="Only visible in admin")
    ip = models.GenericIPAddressField(null=True, blank=True)

    # notification tracking (filled by core.emails)
    notified_at = models.DateTimeField(null=True, blank=True, help_text="When the owner was emailed")
    notify_attempts = models.PositiveSmallIntegerField(default=0)
    notify_error = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="order_status_created"),
            models.Index(fields=["notified_at"], name="order_notified"),
        ]

    def __str__(self):
        return f"#{self.pk} {self.name} ({self.created_at:%d.%m.%Y})"


def attachment_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()[:8]
    return f"orders/{instance.order_id}/{uuid.uuid4().hex[:12]}{ext}"


class Attachment(models.Model):
    order = models.ForeignKey(Order, related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to=attachment_path)
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.original_name


class ConsultationRequest(models.Model):
    class Method(models.TextChoices):
        PHONE = "phone", "Phone call"
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        WORKSHOP = "workshop", "Visit the workshop"

    class Slot(models.TextChoices):
        ANY = "any", "Any time"
        MORNING = "morning", "09:00–12:00"
        MIDDAY = "midday", "12:00–15:00"
        AFTERNOON = "afternoon", "15:00–18:00"

    class Topic(models.TextChoices):
        KITCHEN = "kitchen", "Kitchen"
        WARDROBE = "wardrobe", "Wardrobe"
        BOOKSHELF = "bookshelf", "Bookshelf / TV wall"
        TABLE = "table", "Table / bench"
        CABINET = "cabinet", "Sideboard / cabinet"
        PANELS = "panels", "Wall panelling / built-ins"
        OTHER = "other", "Something else"

    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)

    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40)
    email = models.EmailField(max_length=200, blank=True)
    contact_method = models.CharField(max_length=20, choices=Method.choices, default=Method.PHONE)
    preferred_date = models.DateField(null=True, blank=True)
    preferred_slot = models.CharField(max_length=20, choices=Slot.choices, default=Slot.ANY)
    topic = models.CharField(max_length=20, choices=Topic.choices, blank=True)
    message = models.TextField(max_length=2000, blank=True)

    internal_notes = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    # notification tracking (filled by core.emails)
    notified_at = models.DateTimeField(null=True, blank=True, help_text="When the owner was emailed")
    notify_attempts = models.PositiveSmallIntegerField(default=0)
    notify_error = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="consult_status_created"),
            models.Index(fields=["notified_at"], name="consult_notified"),
        ]

    def __str__(self):
        return f"{self.name} — {self.get_topic_display() or 'consultation'}"
