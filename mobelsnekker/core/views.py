import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from . import pricing
from .deferred import DeferredJsonResponse
from .emails import notify_consultation, notify_order
from .forms import ConsultationForm, OrderForm, validate_files
from .images import compress
from .maintenance import maybe_daily
from .models import Attachment, Order

log = logging.getLogger(__name__)


def _ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    return (fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")) or None


def _rate_limited(request, bucket):
    key = f"rl:{bucket}:{_ip(request)}"
    n = cache.get(key, 0)
    if n >= settings.FORM_RATE_LIMIT:
        return True
    cache.set(key, n + 1, settings.FORM_RATE_WINDOW)
    return False


def _errors(form, extra=None):
    errs = {k: [str(e) for e in v] for k, v in form.errors.items()}
    if extra:
        errs.setdefault("attachments", []).extend(extra)
    return JsonResponse({"ok": False, "errors": errs}, status=400)


# ------------------------------------------------------------------ pages ---
@ensure_csrf_cookie
def index(request):
    return render(request, "core/index.html")


@ensure_csrf_cookie
def calculator(request):
    return render(request, "core/calculator.html", {
        "options": pricing.options(),
        "initial_type": request.GET.get("type", "wardrobe"),
    })


def privacy(request):
    return render(request, "core/privacy.html")


# -------------------------------------------------------------------- api ---
@require_GET
def api_options(request):
    return JsonResponse(pricing.options())


@require_POST
def api_estimate(request):
    try:
        data = json.loads(request.body or "{}")
        return JsonResponse({"ok": True, "estimate": pricing.estimate(data)})
    except (ValueError, pricing.EstimateError) as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


@require_POST
def api_order(request):
    form = OrderForm(request.POST)
    if form.is_bot():
        return JsonResponse({"ok": True})
    if _rate_limited(request, "order"):
        return JsonResponse({"ok": False, "error": "Too many requests. Please call us instead."}, status=429)

    files = request.FILES.getlist("attachments")
    file_errors = validate_files(files)
    if not form.is_valid() or file_errors:
        return _errors(form, file_errors)

    estimate = None
    raw = form.cleaned_data.get("estimate")
    if raw:
        try:
            # never trust prices from the browser: recompute from the inputs
            estimate = pricing.estimate(json.loads(raw).get("input", json.loads(raw)))
        except (ValueError, AttributeError, pricing.EstimateError):
            estimate = None

    with transaction.atomic():
        order = form.save(commit=False)
        order.ip = _ip(request)
        if estimate:
            order.source = Order.Source.CALCULATOR
            order.estimate = estimate
            order.estimate_low, order.estimate_high = estimate["low"], estimate["high"]
        order.save()
        for f in files:
            content, name = compress(f)
            att = Attachment(order=order, original_name=name[:255])
            att.file.save(name, content, save=False)
            att.size = att.file.size
            att.save()

    log.info("New order #%s from %s", order.pk, order.email)
    base = request.build_absolute_uri("/")
    # answer the visitor immediately; emails + housekeeping run after the response
    return DeferredJsonResponse({"ok": True, "id": order.pk},
                                after=[lambda: notify_order(order, base), maybe_daily])


@require_POST
def api_consultation(request):
    form = ConsultationForm(request.POST)
    if form.is_bot():
        return JsonResponse({"ok": True})
    if _rate_limited(request, "consult"):
        return JsonResponse({"ok": False, "error": "Too many requests. Please call us instead."}, status=429)
    if not form.is_valid():
        return _errors(form)
    c = form.save(commit=False)
    c.ip = _ip(request)
    c.save()
    base = request.build_absolute_uri("/")
    return DeferredJsonResponse({"ok": True, "id": c.pk},
                                after=[lambda: notify_consultation(c, base), maybe_daily])
