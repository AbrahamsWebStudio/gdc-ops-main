from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.crm.models import Interaction, Lead, PipelineStage
from apps.dashboard.services import (
    follow_up_completion_rate,
    speed_to_lead_minutes,
    stage_movement_count,
)


def aware_dt(year, month, day, hour=0, minute=0):
    tz = timezone.get_current_timezone()
    return timezone.make_aware(datetime(year, month, day, hour, minute), tz)


class MetricsServiceTests(TestCase):
    def setUp(self):
        self.stage = PipelineStage.objects.create(name="Warm", order=1)

    def _make_lead(self, created_at, **kwargs):
        lead = Lead.objects.create(
            business_name="Acme Ltd",
            contact_person="Jane Doe",
            phone="0700000000",
            email="jane@example.com",
            pain_point="Needs a better process",
            stage=self.stage,
            **kwargs,
        )
        Lead.objects.filter(pk=lead.pk).update(created_at=created_at)
        return Lead.objects.get(pk=lead.pk)

    def _make_interaction(self, lead, created_at):
        interaction = Interaction.objects.create(
            lead=lead,
            interaction_type="call",
            summary="Initial call",
        )
        Interaction.objects.filter(pk=interaction.pk).update(created_at=created_at)
        return Interaction.objects.get(pk=interaction.pk)

    def _make_audit(self, event_type, timestamp, object_id):
        event = AuditEvent.objects.create(
            user=None,
            user_email="system",
            event_type=event_type,
            model_name="Lead",
            object_id=str(object_id),
            action="update",
            before_data=None,
            after_data=None,
            metadata={},
        )
        AuditEvent.objects.filter(pk=event.pk).update(timestamp=timestamp)
        return AuditEvent.objects.get(pk=event.pk)

    def test_speed_to_lead_minutes_average_and_empty_window(self):
        start = aware_dt(2026, 1, 5)
        end = start + timedelta(days=7)

        lead1 = self._make_lead(start + timedelta(hours=1))
        self._make_interaction(lead1, start + timedelta(hours=2))

        self._make_lead(start + timedelta(hours=3))

        old_lead = self._make_lead(start - timedelta(days=2))
        self._make_interaction(old_lead, start + timedelta(hours=1))

        result = speed_to_lead_minutes(start, end)
        self.assertEqual(result, 60.0)

        empty_start = start + timedelta(days=10)
        empty_end = empty_start + timedelta(days=7)
        self._make_lead(empty_start + timedelta(hours=1))
        empty_result = speed_to_lead_minutes(empty_start, empty_end)
        self.assertIsNone(empty_result)

    def test_follow_up_completion_rate_counts_once_and_no_due(self):
        start = aware_dt(2026, 1, 5)
        end = start + timedelta(days=7)

        lead_due = self._make_lead(
            start + timedelta(hours=1),
            next_action_due=start + timedelta(days=1),
        )
        self._make_interaction(lead_due, start + timedelta(days=1, hours=1))
        self._make_interaction(lead_due, start + timedelta(days=2))

        lead_not_completed = self._make_lead(
            start + timedelta(hours=2),
            next_action_due=start + timedelta(days=2),
        )
        self._make_interaction(lead_not_completed, start + timedelta(days=1))

        result = follow_up_completion_rate(start, end)
        self.assertEqual(result["due"], 2)
        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["rate"], 50.0)

        empty_start = start + timedelta(days=10)
        empty_end = empty_start + timedelta(days=7)
        empty_result = follow_up_completion_rate(empty_start, empty_end)
        self.assertIsNone(empty_result["rate"])
        self.assertEqual(empty_result["due"], 0)
        self.assertEqual(empty_result["completed"], 0)

    def test_stage_movement_count_and_no_events(self):
        start = aware_dt(2026, 1, 5)
        end = start + timedelta(days=7)

        self._make_audit("lead.stage_changed", start + timedelta(days=1), object_id=1)
        self._make_audit("lead.stage_changed", start + timedelta(days=2), object_id=2)
        self._make_audit("lead.created", start + timedelta(days=1), object_id=3)

        result = stage_movement_count(start, end)
        self.assertEqual(result, 2)

        empty_start = start + timedelta(days=10)
        empty_end = empty_start + timedelta(days=7)
        empty_result = stage_movement_count(empty_start, empty_end)
        self.assertEqual(empty_result, 0)
