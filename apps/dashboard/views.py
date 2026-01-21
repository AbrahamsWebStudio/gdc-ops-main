from datetime import timedelta

from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.shortcuts import render
from django.utils import timezone

from apps.crm.models import Lead
from apps.dashboard.services import get_consistency_metrics


def home(request):
    now = timezone.now()
    today = timezone.localdate()
    stale_cutoff = now - timedelta(days=7)

    overdue_leads = Lead.objects.filter(
        next_action_due__lt=now).select_related("stage")
    stale_leads = Lead.objects.filter(
        Q(last_interaction_date__lte=stale_cutoff)
        | Q(last_interaction_date__isnull=True,
            first_contact_date__lte=stale_cutoff)
    ).select_related("stage")

    priorities = (
        Lead.objects.select_related("stage")
        .annotate(
            priority_rank=Case(
                When(next_action_due__lt=now, then=Value(1)),
                When(next_action_due__date=today, then=Value(2)),
                When(
                    Q(last_interaction_date__lte=stale_cutoff)
                    | Q(last_interaction_date__isnull=True,
                        first_contact_date__lte=stale_cutoff),
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

    context = {
        "overdue_leads": overdue_leads,
        "stale_leads": stale_leads,
        "priorities": priorities[:10],
        "pipeline_counts": pipeline_counts,
        "next_actions": next_actions[:10],
        "consistency_metrics": consistency_metrics,
    }
    return render(request, "dashboard/home.html", context)
