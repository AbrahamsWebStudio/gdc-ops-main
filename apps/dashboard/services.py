from datetime import timedelta

from django.db.models import Avg, DurationField, ExpressionWrapper, F, Min
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.crm.models import Lead


def _calendar_week_window(now):
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=7)
    return week_start, week_end


def _rolling_window(now, days=7):
    return now - timedelta(days=days), now


def speed_to_lead_minutes(start, end):
    leads = (
        Lead.objects.filter(created_at__gte=start, created_at__lt=end)
        .annotate(first_interaction=Min("interactions__created_at"))
        .exclude(first_interaction__isnull=True)
    )
    duration = ExpressionWrapper(
        F("first_interaction") - F("created_at"), output_field=DurationField()
    )
    avg = leads.annotate(response_time=duration).aggregate(
        avg=Avg("response_time"))["avg"]
    if not avg:
        return None
    return round(avg.total_seconds() / 60, 2)


def follow_up_completion_rate(start, end):
    due_qs = Lead.objects.filter(next_action_due__gte=start,
                                 next_action_due__lt=end)
    due_count = due_qs.count()
    if not due_count:
        return {"rate": None, "due": 0, "completed": 0}

    completed_count = (
        due_qs.filter(interactions__created_at__gte=F("next_action_due"))
        .filter(interactions__created_at__gte=start,
                interactions__created_at__lt=end)
        .distinct()
        .count()
    )
    rate = round((completed_count / due_count) * 100, 2)
    return {"rate": rate, "due": due_count, "completed": completed_count}


def stage_movement_count(start, end):
    return AuditEvent.objects.filter(
        event_type="lead.stage_changed",
        timestamp__gte=start,
        timestamp__lt=end,
    ).count()


def get_consistency_metrics(now=None):
    now = now or timezone.now()
    week_start, week_end = _calendar_week_window(now)
    rolling_start, rolling_end = _rolling_window(now, days=7)

    return {
        "speed_to_lead": {
            "week": speed_to_lead_minutes(week_start, week_end),
            "rolling": speed_to_lead_minutes(rolling_start, rolling_end),
        },
        "follow_up_completion_rate": {
            "week": follow_up_completion_rate(week_start, week_end),
            "rolling": follow_up_completion_rate(rolling_start, rolling_end),
        },
        "stage_movements": {
            "week": stage_movement_count(week_start, week_end),
            "rolling": stage_movement_count(rolling_start, rolling_end),
        },
    }
