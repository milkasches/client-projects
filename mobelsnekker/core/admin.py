from django.contrib import admin, messages
from django.utils.html import format_html, format_html_join

from .emails import notify_consultation, notify_order
from .maintenance import maybe_daily
from .models import Attachment, ConsultationRequest, Order


class EmailStatusFilter(admin.SimpleListFilter):
    title = "owner email"
    parameter_name = "email"

    def lookups(self, request, model_admin):
        return [("failed", "Not delivered"), ("ok", "Sent")]

    def queryset(self, request, qs):
        if self.value() == "failed":
            return qs.filter(notified_at__isnull=True)
        if self.value() == "ok":
            return qs.filter(notified_at__isnull=False)
        return qs


class NotifyMixin:
    notify_fn = None

    @admin.display(description="Email", ordering="notified_at")
    def email_status(self, obj):
        if obj.notified_at:
            return format_html('<span title="{}" style="color:#2f9e44">✔</span>', obj.notified_at.strftime("%d.%m %H:%M"))
        return format_html('<span title="{}" style="color:#d14b2f">✖ {}</span>', obj.notify_error or "pending", obj.notify_attempts)

    @admin.action(description="Resend email notification to the owner")
    def resend(self, request, queryset):
        fn = type(self).notify_fn
        ok = sum(1 for o in queryset if fn(o, request.build_absolute_uri("/"), with_client=False))
        level = messages.SUCCESS if ok == queryset.count() else messages.WARNING
        self.message_user(request, f"Sent {ok} of {queryset.count()}.", level)

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        # daily backup / retry runs after the page is delivered
        response._resource_closers.append(maybe_daily)
        return response


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ("preview", "original_name", "size")
    fields = ("preview", "original_name", "size", "file")

    @admin.display(description="Preview")
    def preview(self, obj):
        if obj.file and obj.original_name.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="height:80px;border-radius:6px"></a>', obj.file.url)
        return format_html('<a href="{}" target="_blank">open</a>', obj.file.url) if obj.file else "-"


@admin.register(Order)
class OrderAdmin(NotifyMixin, admin.ModelAdmin):
    notify_fn = staticmethod(notify_order)
    actions = ["resend"]
    list_display = ("id", "created_at", "name", "phone", "email", "source", "price_range", "email_status", "status")
    list_filter = ("status", "source", EmailStatusFilter, "delivery", "created_at")
    list_editable = ("status",)
    search_fields = ("name", "email", "phone", "description", "address")
    readonly_fields = ("created_at", "ip", "estimate_table", "notified_at", "notify_attempts", "notify_error")
    inlines = [AttachmentInline]
    fieldsets = (
        (None, {"fields": ("status", "created_at", "source")}),
        ("Client", {"fields": ("name", "email", "phone", "preferred_time")}),
        ("Project", {"fields": ("description", "delivery", "address")}),
        ("Calculator estimate", {"fields": ("estimate_low", "estimate_high", "estimate_table")}),
        ("Internal", {"fields": ("internal_notes", "ip", "notified_at", "notify_attempts", "notify_error")}),
    )

    @admin.display(description="Estimate")
    def price_range(self, obj):
        if obj.estimate_low:
            return f"{obj.estimate_low:,} – {obj.estimate_high:,} kr".replace(",", " ")
        return "—"

    @admin.display(description="Breakdown")
    def estimate_table(self, obj):
        if not obj.estimate:
            return "—"
        rows = format_html_join("", "<tr><td>{}</td><td style='text-align:right'>{} kr</td></tr>",
                                ((l["label"], l["amount"]) for l in obj.estimate.get("lines", [])))
        return format_html("<table>{}<tr><td><b>Total incl. VAT</b></td><td style='text-align:right'><b>{} kr</b></td></tr></table>",
                           rows, obj.estimate.get("total"))


@admin.register(ConsultationRequest)
class ConsultationAdmin(NotifyMixin, admin.ModelAdmin):
    notify_fn = staticmethod(notify_consultation)
    actions = ["resend"]
    list_display = ("id", "created_at", "name", "phone", "contact_method", "preferred_date", "preferred_slot", "topic", "email_status", "status")
    list_filter = ("status", EmailStatusFilter, "contact_method", "topic")
    list_editable = ("status",)
    search_fields = ("name", "email", "phone", "message")
    readonly_fields = ("created_at", "ip", "notified_at", "notify_attempts", "notify_error")
