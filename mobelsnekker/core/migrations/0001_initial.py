import django.db.models.deletion
from django.db import migrations, models

import core.models

STATUS = [("new", "New"), ("contacted", "Contacted"), ("quoted", "Quote sent"),
          ("won", "Accepted / in work"), ("done", "Done"), ("lost", "Lost / cancelled")]


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("status", models.CharField(choices=STATUS, default="new", max_length=20)),
                ("source", models.CharField(choices=[("form", "Contact form"), ("calculator", "Price calculator")], default="form", max_length=20)),
                ("name", models.CharField(max_length=120)),
                ("email", models.EmailField(max_length=200)),
                ("phone", models.CharField(max_length=40)),
                ("preferred_time", models.CharField(blank=True, max_length=120)),
                ("description", models.TextField(blank=True, max_length=4000)),
                ("delivery", models.BooleanField(default=False)),
                ("address", models.CharField(blank=True, max_length=300)),
                ("estimate", models.JSONField(blank=True, null=True)),
                ("estimate_low", models.PositiveIntegerField(blank=True, null=True)),
                ("estimate_high", models.PositiveIntegerField(blank=True, null=True)),
                ("internal_notes", models.TextField(blank=True, help_text="Only visible in admin")),
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ConsultationRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("status", models.CharField(choices=STATUS, default="new", max_length=20)),
                ("name", models.CharField(max_length=120)),
                ("phone", models.CharField(max_length=40)),
                ("email", models.EmailField(blank=True, max_length=200)),
                ("contact_method", models.CharField(choices=[("phone", "Phone call"), ("email", "Email"), ("sms", "SMS"), ("workshop", "Visit the workshop")], default="phone", max_length=20)),
                ("preferred_date", models.DateField(blank=True, null=True)),
                ("preferred_slot", models.CharField(choices=[("any", "Any time"), ("morning", "09:00–12:00"), ("midday", "12:00–15:00"), ("afternoon", "15:00–18:00")], default="any", max_length=20)),
                ("topic", models.CharField(blank=True, choices=[("kitchen", "Kitchen"), ("wardrobe", "Wardrobe"), ("bookshelf", "Bookshelf / TV wall"), ("table", "Table / bench"), ("cabinet", "Sideboard / cabinet"), ("panels", "Wall panelling / built-ins"), ("other", "Something else")], max_length=20)),
                ("message", models.TextField(blank=True, max_length=2000)),
                ("internal_notes", models.TextField(blank=True)),
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Attachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to=core.models.attachment_path)),
                ("original_name", models.CharField(max_length=255)),
                ("size", models.PositiveIntegerField(default=0)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attachments", to="core.order")),
            ],
        ),
    ]
