from django.contrib import admin

from .models import AutomationRun


@admin.register(AutomationRun)
class AutomationRunAdmin(admin.ModelAdmin):
    list_display = ("created_at",
                    "event_type",
                    "lead_id",
                    "success",
                    "status_code",
                    "attempts")
    list_filter = ("event_type", "success")
    search_fields = ("lead_id", "correlation_id", "webhook_url")
    readonly_fields = (
        "created_at",
        "updated_at",
        "correlation_id",
        "event_type",
        "lead_id",
        "webhook_url",
        "payload_hash",
        "status_code",
        "success",
        "error_message",
        "attempts",
        "request_headers",
        "response_body_snippet",
        "duration_ms",
        "last_attempt_at",
        "payload_preview",
    )
