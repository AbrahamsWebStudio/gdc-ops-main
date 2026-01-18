from django.contrib import admin

from .models import Interaction, Lead, PipelineStage


@admin.register(PipelineStage)
class PipelineStageAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "is_won", "is_lost"]
    list_editable = ["order"]


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = [
        "business_name",
        "contact_person",
        "stage",
        "value_estimate",
        "next_action_due",
        "created_at",
    ]
    list_filter = ["stage", "source", "industry"]
    search_fields = ["business_name", "contact_person", "phone", "email"]
    readonly_fields = ["created_at", "updated_at", "first_contact_date"]

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
        ("Notes", {"fields": ("notes",)}),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "first_contact_date",
                    "last_interaction_date",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ["lead", "interaction_type", "created_at", "duration_minutes"]
    list_filter = ["interaction_type", "created_at"]
    search_fields = ["lead__business_name", "summary"]
    readonly_fields = ["created_at"]
