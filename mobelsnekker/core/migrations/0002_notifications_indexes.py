from django.db import migrations, models


def mark_existing_as_notified(apps, schema_editor):
    # records created before this migration were already emailed (or printed)
    for name in ("Order", "ConsultationRequest"):
        Model = apps.get_model("core", name)
        Model.objects.filter(notified_at__isnull=True).update(notified_at=models.F("created_at"), notify_attempts=1)


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.AddField("order", "notified_at", models.DateTimeField(blank=True, null=True, help_text="When the owner was emailed")),
        migrations.AddField("order", "notify_attempts", models.PositiveSmallIntegerField(default=0)),
        migrations.AddField("order", "notify_error", models.CharField(blank=True, max_length=500)),
        migrations.AddField("consultationrequest", "notified_at", models.DateTimeField(blank=True, null=True, help_text="When the owner was emailed")),
        migrations.AddField("consultationrequest", "notify_attempts", models.PositiveSmallIntegerField(default=0)),
        migrations.AddField("consultationrequest", "notify_error", models.CharField(blank=True, max_length=500)),
        migrations.AddIndex("order", models.Index(fields=["status", "-created_at"], name="order_status_created")),
        migrations.AddIndex("order", models.Index(fields=["notified_at"], name="order_notified")),
        migrations.AddIndex("consultationrequest", models.Index(fields=["status", "-created_at"], name="consult_status_created")),
        migrations.AddIndex("consultationrequest", models.Index(fields=["notified_at"], name="consult_notified")),
        migrations.RunPython(mark_existing_as_notified, migrations.RunPython.noop),
    ]
