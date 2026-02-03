from datetime import timedelta

from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.automations.models import AutomationRun
from apps.core.models import AppSetting
from apps.crm.models import Lead
from apps.dashboard.services import get_consistency_metrics


@login_required

def home(request):
    now = timezone.now()
    today = timezone.localdate()
    stale_days = AppSetting.get_int("stale_days", 7)
    stale_cutoff = now - timedelta(days=stale_days)

    user = request.user
    groups = set(user.groups.values_list("name", flat=True)) if user.is_authenticated else set()
    is_owner = user.is_superuser or "Owner" in groups
    is_sales = "Sales" in groups
    is_ops = "Ops" in groups

    can_view_leads = is_owner or is_sales
    can_view_health = is_owner or is_ops
    can_view_financials = is_owner

    overdue_leads = Lead.objects.filter(
        next_action_due__lt=now, next_action_due__isnull=False
    ).select_related("stage")
    due_today_leads = Lead.objects.filter(
        next_action_due__date=today
    ).select_related("stage")
    stale_leads = Lead.objects.filter(
        Q(last_interaction_date__lte=stale_cutoff)
        | Q(last_interaction_date__isnull=True, first_contact_date__lte=stale_cutoff)
    ).select_related("stage")

    priorities = (
        Lead.objects.select_related("stage")
        .annotate(
            priority_rank=Case(
                When(next_action_due__lt=now, then=Value(1)),
                When(next_action_due__date=today, then=Value(2)),
                When(
                    Q(last_interaction_date__lte=stale_cutoff)
                    | Q(last_interaction_date__isnull=True, first_contact_date__lte=stale_cutoff),
                    then=Value(3),
                ),
                default=Value(4),
                output_field=IntegerField(),
            )
        )
        .order_by("priority_rank", "-value_estimate")
    )

    pipeline_counts = (
        Lead.objects.values("stage__name", "stage__order")
        .annotate(total=Count("id"))
        .order_by("stage__order")
    )

    next_actions = (
        Lead.objects.exclude(next_action="")
        .filter(next_action_due__isnull=False)
        .order_by("next_action_due")
        .select_related("stage")
    )

    consistency_metrics = get_consistency_metrics(now=now)

    last_daily_summary = (
        AutomationRun.objects.filter(event_type="daily.summary", success=True)
        .order_by("-created_at")
        .first()
    )
    automation_failures_24h = AutomationRun.objects.filter(
        created_at__gte=now - timedelta(hours=24), success=False
    ).count()
    automation_runs = AutomationRun.objects.order_by("-created_at")[:5]

    context = {
        "overdue_leads": overdue_leads,
        "due_today_leads": due_today_leads,
        "stale_leads": stale_leads,
        "stale_days": stale_days,
        "priorities": priorities[:10],
        "pipeline_counts": pipeline_counts,
        "next_actions": next_actions[:10],
        "consistency_metrics": consistency_metrics,
        "last_daily_summary": last_daily_summary,
        "automation_failures_24h": automation_failures_24h,
        "automation_runs": automation_runs,
        "can_view_leads": can_view_leads,
        "can_view_health": can_view_health,
        "can_view_financials": can_view_financials,
    }
    return render(request, "dashboard/home.html", context)
