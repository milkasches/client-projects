"""Notification emails.

Sending happens AFTER the response has been delivered to the visitor
(see core.deferred), so a slow SMTP server never makes the form feel slow.
The admin notification is tracked on the record (notified_at / notify_attempts /
notify_error) and retried by `python manage.py maintenance`.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

log = logging.getLogger(__name__)

MAX_ATTACH_BYTES = 18 * 1024 * 1024  # Gmail limit is 25 MB incl. encoding overhead


def _send(subject, template, ctx, to, reply_to=None, attachments=()):
    ctx = {**ctx, "contact_email": settings.CONTACT_EMAIL}
    text = render_to_string(f"core/emails/{template}.txt", ctx)
    html = render_to_string(f"core/emails/{template}.html", ctx)
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, to, reply_to=reply_to)
    msg.attach_alternative(html, "text/html")
    for a in attachments:
        try:
            a.file.open("rb")
            msg.attach(a.original_name, a.file.read())
        except OSError:
            log.warning("Attachment %s is missing on disk", a.file.name)
        finally:
            a.file.close()
    msg.send(fail_silently=False)  # raises on failure, handled by the caller


def _base_url(base_url=None):
    return (base_url or settings.SITE_URL).rstrip("/")


def _order_admin(order, base_url):
    ctx = {"o": order, "admin_url": f"{_base_url(base_url)}/admin/core/order/{order.pk}/change/"}
    atts = list(order.attachments.all())
    if sum(a.size for a in atts) > MAX_ATTACH_BYTES:
        atts = []
    price = f" · {order.estimate_low:,}–{order.estimate_high:,} kr".replace(",", " ") if order.estimate_low else ""
    _send(f"New order #{order.pk} — {order.name}{price}", "order_admin", ctx,
          [settings.NOTIFY_EMAIL], reply_to=[order.email], attachments=atts)


def _order_client(order, base_url):
    _send("We received your request — Møbelsnekker I&W", "order_client", {"o": order}, [order.email])


def _consult_admin(c, base_url):
    ctx = {"c": c, "admin_url": f"{_base_url(base_url)}/admin/core/consultationrequest/{c.pk}/change/"}
    _send(f"Consultation request — {c.name} ({c.get_contact_method_display()})", "consult_admin", ctx,
          [settings.NOTIFY_EMAIL], reply_to=[c.email] if c.email else None)


def _consult_client(c, base_url):
    if c.email:
        _send("Your consultation request — Møbelsnekker I&W", "consult_client", {"c": c}, [c.email])


def _notify(obj, admin_fn, client_fn, base_url, with_client):
    """Send the admin notification (tracked) and, on first try, the client confirmation."""
    ok = True
    try:
        admin_fn(obj, base_url)
        obj.notified_at = timezone.now()
        obj.notify_error = ""
    except Exception as e:  # SMTP down, wrong password, timeout …
        ok = False
        obj.notify_error = f"{type(e).__name__}: {e}"[:500]
        log.exception("Admin notification failed for %s #%s", type(obj).__name__, obj.pk)
    obj.notify_attempts += 1
    type(obj).objects.filter(pk=obj.pk).update(
        notified_at=obj.notified_at, notify_error=obj.notify_error, notify_attempts=obj.notify_attempts)
    if with_client:
        try:
            client_fn(obj, base_url)
        except Exception:
            log.exception("Client confirmation failed for %s #%s", type(obj).__name__, obj.pk)
    return ok


def notify_order(order, base_url=None, with_client=True):
    return _notify(order, _order_admin, _order_client, base_url, with_client)


def notify_consultation(c, base_url=None, with_client=True):
    return _notify(c, _consult_admin, _consult_client, base_url, with_client)
