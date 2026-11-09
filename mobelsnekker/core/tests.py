import json
import shutil
import tempfile

from datetime import timedelta
from pathlib import Path

from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend
from django.core.management import call_command
from django.utils import timezone
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest import skipUnless

from django.test import TestCase, override_settings
from django.urls import reverse

from . import maintenance, pricing
from .images import HAS_PIL
from .models import Attachment, ConsultationRequest, Order

MEDIA = tempfile.mkdtemp()
BACKUPS = tempfile.mkdtemp()


class FailingBackend(BaseEmailBackend):
    def send_messages(self, messages):
        raise ConnectionRefusedError("SMTP down")


class PricingTests(TestCase):
    def test_defaults_for_every_type(self):
        for key in pricing.TYPES:
            e = pricing.estimate({"type": key})
            self.assertGreater(e["total"], 0)
            self.assertLessEqual(e["low"], e["total"])
            self.assertGreaterEqual(e["high"], e["total"])
            self.assertEqual(e["total"], e["subtotal"] + e["vat"])

    def test_better_material_costs_more(self):
        cheap = pricing.estimate({"type": "wardrobe", "material": "chipboard"})["total"]
        oak = pricing.estimate({"type": "wardrobe", "material": "solid_oak"})["total"]
        self.assertGreater(oak, cheap)

    def test_bigger_costs_more(self):
        a = pricing.estimate({"type": "kitchen", "width": 200})["total"]
        b = pricing.estimate({"type": "kitchen", "width": 500})["total"]
        self.assertGreater(b, a)

    def test_minimum_price(self):
        e = pricing.estimate({"type": "shelf", "width": 20, "depth": 10, "installation": False, "delivery": "pickup"})
        self.assertEqual(e["subtotal"], pricing.TYPES["shelf"]["min"])

    def test_limits_are_clamped(self):
        e = pricing.estimate({"type": "wardrobe", "width": 99999, "drawers": 999})
        self.assertEqual(e["input"]["width"], pricing.LIMITS["width"][1])
        self.assertEqual(e["input"]["drawers"], pricing.EXTRAS["drawers"]["max"])

    def test_invalid_choice(self):
        with self.assertRaises(pricing.EstimateError):
            pricing.estimate({"type": "spaceship"})


@override_settings(MEDIA_ROOT=MEDIA, NOTIFY_EMAIL="owner@example.com", AUTO_MAINTENANCE=False,
                   BACKUP_DIR=BACKUPS, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)
        shutil.rmtree(BACKUPS, ignore_errors=True)

    def setUp(self):
        cache.clear()

    def test_pages(self):
        for name in ("index", "calculator", "privacy"):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)
        self.assertContains(self.client.get(reverse("calculator")), 'id="calc-options"')

    def test_estimate_api(self):
        r = self.client.post(reverse("api_estimate"), json.dumps({"type": "bookshelf", "doors": 2}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        r = self.client.post(reverse("api_estimate"), "{bad", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def order_data(self, **kw):
        d = {"name": "Ola Nordmann", "email": "ola@example.com", "phone": "+47 900 00 000",
             "description": "Wardrobe in the hallway", "delivery": "false", "consent": "on"}
        d.update(kw)
        return d

    def test_order_with_file_and_emails(self):
        img = SimpleUploadedFile("room.jpg", b"\xff\xd8\xff" + b"0" * 100, content_type="image/jpeg")
        r = self.client.post(reverse("api_order"), {**self.order_data(), "attachments": [img]})
        self.assertEqual(r.status_code, 200, r.content)
        o = Order.objects.get()
        self.assertEqual(o.attachments.count(), 1)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])
        self.assertEqual(mail.outbox[0].reply_to, ["ola@example.com"])
        self.assertEqual(len(mail.outbox[0].attachments), 1)
        self.assertEqual(mail.outbox[1].to, ["ola@example.com"])

    def test_order_estimate_is_recomputed(self):
        fake = {"input": {"type": "kitchen", "width": 300}, "total": 1}
        r = self.client.post(reverse("api_order"), self.order_data(description="", estimate=json.dumps(fake)))
        self.assertEqual(r.status_code, 200, r.content)
        o = Order.objects.get()
        self.assertEqual(o.source, "calculator")
        self.assertGreater(o.estimate["total"], 1000)
        self.assertIn(str(o.estimate_low), mail.outbox[0].body)

    def test_order_validation(self):
        r = self.client.post(reverse("api_order"), self.order_data(email="nope", consent=""))
        self.assertEqual(r.status_code, 400)
        errs = r.json()["errors"]
        self.assertIn("email", errs)
        self.assertIn("consent", errs)
        r = self.client.post(reverse("api_order"), self.order_data(delivery="true"))
        self.assertIn("address", r.json()["errors"])
        bad = SimpleUploadedFile("x.exe", b"MZ", content_type="application/octet-stream")
        r = self.client.post(reverse("api_order"), {**self.order_data(), "attachments": [bad]})
        self.assertIn("attachments", r.json()["errors"])
        self.assertEqual(Order.objects.count(), 0)

    def test_honeypot(self):
        r = self.client.post(reverse("api_order"), self.order_data(website="http://spam"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)

    def test_consultation(self):
        r = self.client.post(reverse("api_consultation"), {
            "name": "Kari", "phone": "+47 911 11 111", "email": "kari@example.com",
            "contact_method": "phone", "preferred_date": "2030-01-10", "preferred_slot": "morning",
            "topic": "kitchen", "message": "New kitchen", "consent": "on"})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(ConsultationRequest.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 2)

    def test_consultation_email_required_for_email_contact(self):
        r = self.client.post(reverse("api_consultation"), {
            "name": "Kari", "phone": "+47 911 11 111", "contact_method": "email", "preferred_slot": "any", "consent": "on"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.json()["errors"])

    @override_settings(FORM_RATE_LIMIT=2)
    def test_rate_limit(self):
        for _ in range(2):
            self.client.post(reverse("api_order"), self.order_data())
        r = self.client.post(reverse("api_order"), self.order_data())
        self.assertEqual(r.status_code, 429)

    def test_csrf_enforced(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse("api_order"), self.order_data())
        self.assertEqual(r.status_code, 403)

    # ---------------------------------------------------------- optimisation
    def test_notification_tracked(self):
        self.client.post(reverse("api_order"), self.order_data())
        o = Order.objects.get()
        self.assertIsNotNone(o.notified_at)
        self.assertEqual(o.notify_attempts, 1)

    def test_failed_email_is_saved_and_retried(self):
        with override_settings(EMAIL_BACKEND="core.tests.FailingBackend"):
            r = self.client.post(reverse("api_order"), self.order_data())
        self.assertEqual(r.status_code, 200)  # visitor still gets success
        o = Order.objects.get()
        self.assertIsNone(o.notified_at)
        self.assertIn("SMTP down", o.notify_error)
        Order.objects.update(created_at=timezone.now() - timedelta(minutes=10))
        sent, failed = maintenance.retry_notifications()
        self.assertEqual((sent, failed), (1, 0))
        o.refresh_from_db()
        self.assertIsNotNone(o.notified_at)
        self.assertEqual(len(mail.outbox), 1)  # only the owner email is resent

    @skipUnless(HAS_PIL, "Pillow not installed")
    def test_photo_is_compressed(self):
        from io import BytesIO
        from PIL import Image
        buf = BytesIO()
        Image.effect_noise((3000, 2000), 40).save(buf, "PNG")
        big = SimpleUploadedFile("photo.png", buf.getvalue(), content_type="image/png")
        self.client.post(reverse("api_order"), {**self.order_data(), "attachments": [big]})
        a = Attachment.objects.get()
        self.assertTrue(a.file.name.endswith(".jpg"))
        self.assertLess(a.size, len(buf.getvalue()))
        with Image.open(a.file.path) as im:
            self.assertLessEqual(max(im.size), 2000)

    def test_backup_and_purge(self):
        self.client.post(reverse("api_order"), self.order_data())
        o = Order.objects.get()
        Order.objects.update(status="lost", created_at=timezone.now() - timedelta(days=400))
        self.assertEqual(maintenance.purge_old(), (1, 0))
        self.assertFalse(Order.objects.exists())
        call_command("maintenance", "--backup", stdout=open("/dev/null", "w"))
        backups = list(Path(BACKUPS).glob("backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "media.zip").exists())  # db copy is skipped inside the test transaction

    def test_attachment_file_deleted_with_order(self):
        img = SimpleUploadedFile("plan.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        self.client.post(reverse("api_order"), {**self.order_data(), "attachments": [img]})
        path = Path(Attachment.objects.get().file.path)
        self.assertTrue(path.exists())
        Order.objects.get().delete()
        self.assertFalse(path.exists())
