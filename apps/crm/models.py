"""CRM models for lead tracking and interactions."""
from __future__ import annotations

from django.db import models

from apps.audit.models import AuditEvent
from apps.core.models import ActiveObjectsManager, BaseModel


class PipelineStage(models.Model):
    """Pipeline stages for lead progression."""

    name = models.CharField(max_length=50)
    order = models.IntegerField(default=0)
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.name


class Lead(BaseModel):
    """Prospect/Lead tracking."""

    SOURCE_CHOICES = [
        ("cold_call", "Cold Call"),
        ("referral", "Referral"),
        ("linkedin", "LinkedIn"),
        ("website", "Website"),
        ("other", "Other"),
    ]

    business_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)

    industry = models.CharField(max_length=100, blank=True)
    pain_point = models.TextField(help_text="What problem are they facing?")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="cold_call")

    stage = models.ForeignKey(PipelineStage, on_delete=models.PROTECT)
    value_estimate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Estimated monthly retainer (KES)",
    )

    first_contact_date = models.DateTimeField(auto_now_add=True)
    last_interaction_date = models.DateTimeField(null=True, blank=True)
    next_action = models.CharField(max_length=200, blank=True, help_text="What's the next step?")
    next_action_due = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")

    objects = ActiveObjectsManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.business_name} - {self.stage.name}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        old_stage = None

        if not is_new:
            try:
                old_lead = Lead.all_objects.get(pk=self.pk)
                old_stage = old_lead.stage
            except Lead.DoesNotExist:
                old_stage = None

        super().save(*args, **kwargs)

        if is_new:
            AuditEvent.log(
                event_type="lead.created",
                model_name="Lead",
                object_id=str(self.id),
                action="create",
                after={"business_name": self.business_name, "stage": self.stage.name},
            )
        elif old_stage and old_stage != self.stage:
            AuditEvent.log(
                event_type="lead.stage_changed",
                model_name="Lead",
                object_id=str(self.id),
                action="update",
                before={"stage": old_stage.name},
                after={"stage": self.stage.name},
            )


class Interaction(BaseModel):
    """Log every interaction with a lead."""

    INTERACTION_TYPES = [
        ("call", "Phone Call"),
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("meeting", "Meeting"),
        ("other", "Other"),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="interactions")
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    summary = models.TextField(help_text="What was discussed?")
    outcome = models.CharField(max_length=200, blank=True, help_text="What was agreed?")
    duration_minutes = models.IntegerField(null=True, blank=True)

    objects = ActiveObjectsManager()

    def __str__(self) -> str:
        return f"{self.lead.business_name} - {self.interaction_type} on {self.created_at.date()}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        self.lead.last_interaction_date = self.created_at
        self.lead.save()

        if is_new:
            AuditEvent.log(
                event_type="interaction.logged",
                model_name="Interaction",
                object_id=str(self.id),
                action="create",
                after={
                    "lead": self.lead.business_name,
                    "type": self.interaction_type,
                    "summary": self.summary[:100],
                },
            )
