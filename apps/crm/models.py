"""CRM models for lead tracking and interactions."""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.core.models import ActiveObjectsManager, BaseModel


class PipelineStage(models.Model):
    """
    WHAT: Defines the steps a lead goes through.
    WHY: Track progress, measure conversion rates, identify bottlenecks.
    EXAMPLES: Cold, Warm, Meeting Booked, Proposal Sent, Won, Lost.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Stage name (e.g., 'Meeting Booked')",
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order (0=first stage, 1=second, etc.)",
    )
    is_won = models.BooleanField(
        default=False,
        help_text="True if this stage means 'we got the client'",
    )
    is_lost = models.BooleanField(
        default=False,
        help_text="True if this stage means 'we lost the lead'",
    )

    class Meta:
        ordering = ["order"]
        verbose_name = "Pipeline Stage"
        verbose_name_plural = "Pipeline Stages"

    def __str__(self) -> str:
        return self.name

    @property
    def is_terminal(self):
        """
        Returns True if this is an end state (won or lost).
        Use to stop automation sequences when a lead is terminal.
        """
        return self.is_won or self.is_lost


class Lead(BaseModel):
    """
    WHAT: A potential client (prospect).
    WHY: Track everyone you talk to, what they need, where they are in pipeline.
    LIFECYCLE: Create -> Move through stages -> Convert to Client or mark Lost.
    """

    SOURCE_CHOICES = [
        ("cold_call", "Cold Call"),
        ("cold_email", "Cold Email"),
        ("referral", "Referral"),
        ("linkedin", "LinkedIn"),
        ("website", "Website Form"),
        ("networking", "Networking Event"),
        ("other", "Other"),
    ]

    business_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)

    industry = models.CharField(max_length=100, blank=True)
    pain_point = models.TextField(
        help_text="CRITICAL: What problem are they facing? Be specific. Example: "
        "'Manually enters 50 orders daily into Excel, takes 2 hours, frequent errors'",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="cold_call",
        help_text="How did you find this lead?",
    )

    stage = models.ForeignKey(
        PipelineStage,
        on_delete=models.PROTECT,
        help_text="Current stage in pipeline",
    )
    value_estimate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Estimated monthly retainer (KES). Used to prioritize high-value leads",
    )

    first_contact_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When you first reached out (auto-set on creation)",
    )
    last_interaction_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time you called/emailed/met (auto-updated when logging interaction)",
    )
    next_action = models.CharField(
        max_length=200,
        blank=True,
        help_text="What's the next step? (e.g., 'Send proposal', 'Follow-up call')",
    )
    next_action_due = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When should next_action happen? (used for reminders)",
    )

    notes = models.TextField(
        blank=True,
        help_text="Internal notes, conversation summaries, anything useful",
    )
    tags = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated tags (e.g., 'urgent, high-value, decision-maker')",
    )

    objects = ActiveObjectsManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lead"
        verbose_name_plural = "Leads"

    def __str__(self) -> str:
        return f"{self.business_name} - {self.stage.name}"

    @property
    def is_overdue(self):
        if not self.next_action_due:
            return False
        return timezone.now() > self.next_action_due

    @property
    def days_in_pipeline(self):
        delta = timezone.now() - self.first_contact_date
        return delta.days

    @property
    def days_since_last_interaction(self):
        if not self.last_interaction_date:
            return self.days_in_pipeline
        delta = timezone.now() - self.last_interaction_date
        return delta.days

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_stage = None

        if not is_new:
            try:
                old_lead = Lead.objects.get(pk=self.pk)
                old_stage = old_lead.stage
            except Lead.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if is_new:
            AuditEvent.log(
                event_type="lead.created",
                model_name="Lead",
                object_id=str(self.id),
                action="create",
                after={
                    "business_name": self.business_name,
                    "stage": self.stage.name,
                    "source": self.source,
                    "value_estimate": float(self.value_estimate),
                },
            )
        elif old_stage and old_stage != self.stage:
            AuditEvent.log(
                event_type="lead.stage_changed",
                model_name="Lead",
                object_id=str(self.id),
                action="update",
                before={"stage": old_stage.name},
                after={"stage": self.stage.name},
                metadata={"days_to_move": (timezone.now() - self.first_contact_date).days},
            )


class Interaction(BaseModel):
    """
    WHAT: Log of every contact with a lead (calls, emails, meetings).
    WHY: Track what was discussed, maintain context, measure response time.
    BEST PRACTICE: Log interaction immediately after it happens.
    """

    INTERACTION_TYPES = [
        ("call", "Phone Call"),
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("meeting", "In-Person Meeting"),
        ("video_call", "Video Call (Zoom/Meet)"),
        ("other", "Other"),
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="interactions",
        help_text="Which lead is this interaction with?",
    )
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPES,
        help_text="How did you communicate?",
    )
    summary = models.TextField(
        help_text="REQUIRED: What was discussed? What did they say? Be specific.",
    )
    outcome = models.CharField(
        max_length=200,
        blank=True,
        help_text="What was agreed/decided? (e.g., 'Meeting booked for Friday', 'Not interested')",
    )
    duration_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="How long did this interaction take? (helps track time spent per lead)",
    )

    objects = ActiveObjectsManager()

    def __str__(self) -> str:
        return f"{self.lead.business_name} - {self.interaction_type} on {self.created_at.date()}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        Lead.objects.filter(pk=self.lead.pk).update(
            last_interaction_date=self.created_at,
        )

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
                    "duration": self.duration_minutes,
                },
            )
