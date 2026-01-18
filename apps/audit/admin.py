from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "event_type", "user_email", "action", "model_name"]
    list_filter = ["event_type", "action", "model_name", "timestamp"]
    search_fields = ["user_email", "object_id", "event_type"]
    readonly_fields = [field.name for field in AuditEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
