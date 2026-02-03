from django.contrib import admin
from django.utils.html import format_html
from .models import Interaction, Lead, PipelineStage


@admin.register(PipelineStage)
class PipelineStageAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "is_won", "is_lost"]
    list_editable = ["order"]
    ordering = ["order"]


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    def overdue_indicator(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red;">{}</span>',
                               "🔴 OVERDUE")
        if obj.next_action_due:
            return format_html('<span style="color: green;">{}</span>',
                               "✅ Scheduled")
        return "-"

    overdue_indicator.short_description = "Status"

    def days_since_contact(self, obj):
        days = obj.days_since_last_interaction
        if days > 7:
            return format_html(
                '<span style="color: orange;">{} days</span>', days)
        return f"{days} days"

    days_since_contact.short_description = "Last Contact"

    list_display = [
        "business_name",
        "contact_person",
        "stage",
        "value_estimate",
        "overdue_indicator",
        "days_since_contact",
        "next_action_due",
    ]
    list_filter = ["stage", "source", "industry", "created_at"]
    search_fields = [
        "business_name",
        "contact_person",
        "phone",
        "email",
        "pain_point"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "first_contact_date",
        "last_interaction_date",
    ]

    fieldsets = (
        (
            "Basic Info",
            {"fields": ("business_name", "contact_person", "phone", "email")},
        ),
        (
            "Context",
            {"fields": ("industry", "pain_point", "source", "tags")},
        ),
        (
            "Pipeline",
            {
                "fields": (
                    "stage",
                    "value_estimate",
                    "next_action",
                    "next_action_due",
                )
            },
        ),
        ("Notes", {"fields": ("notes",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                    "first_contact_date",
                    "last_interaction_date",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    class InteractionInline(admin.TabularInline):
        model = Interaction
        extra = 1
        fields = ["interaction_type",
                  "summary", "outcome",
                  "duration_minutes",
                  "created_at"]
        readonly_fields = ["created_at"]

    inlines = [InteractionInline]


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ["lead", "interaction_type", "created_at",
                    "duration_minutes", "outcome"]
    list_filter = ["interaction_type", "created_at"]
    search_fields = ["lead__business_name", "summary", "outcome"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {"fields": ("lead", "interaction_type",
                        "summary", "outcome", "duration_minutes")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
