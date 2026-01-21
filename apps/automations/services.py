from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
import uuid
from datetime import timedelta

from django.conf import settings
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.crm.models import Lead
from .models import AutomationRun

WEBHOOK_PATHS = {
    "lead.created": "gdc-lead-created",
    "lead.overdue": "gdc-lead-overdue",
    "daily.summary": "gdc-daily-summary",
}


def _unix_ts(dt):
    return int(dt.timestamp())


def _lead_summary(lead):
    return {
        "lead_id": str(lead.id),
        "business_name": lead.business_name,
        "stage": lead.stage.name,
        "phone": lead.phone,
        "next_action": lead.next_action,
        "next_action_due": _unix_ts(lead.next_action_due) if lead.next_action_due else None,
    }


def _build_payload(event_type, correlation_id, lead=None, summary=None):
    payload = {
        "event_type": event_type,
        "timestamp": _unix_ts(timezone.now()),
        "correlation_id": str(correlation_id),
    }
    if lead is not None:
        payload["lead"] = _lead_summary(lead)
        payload["lead_id"] = str(lead.id)
    if summary is not None:
        payload["summary"] = summary
    return payload


def _sign_payload(payload_bytes, secret):
    signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def _send_webhook(event_type, payload, lead_id=None):
    if event_type not in WEBHOOK_PATHS:
        raise ValueError(f"Unknown event_type: {event_type}")

    base_url = settings.GDC_WEBHOOK_BASE_URL.rstrip("/") + "/"
    webhook_url = base_url + WEBHOOK_PATHS[event_type]
    secret = settings.GDC_WEBHOOK_SECRET
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()

    run = AutomationRun.objects.create(
        correlation_id=uuid.UUID(payload["correlation_id"]),
        event_type=event_type,
        lead_id=lead_id,
        webhook_url=webhook_url,
        payload_hash=payload_hash,
        payload_preview=payload,
    )

    max_retries = settings.GDC_AUTOMATIONS_RETRY_MAX
    for attempt in range(1, max_retries + 1):
        start = time.monotonic()
        run.attempts = attempt
        run.last_attempt_at = timezone.now()

        headers = {
            "Content-Type": "application/json",
            "X-GDC-Event": event_type,
            "X-GDC-Timestamp": str(payload["timestamp"]),
        }

        if not secret:
            run.success = False
            run.error_message = "Missing GDC_WEBHOOK_SECRET"
            run.duration_ms = int((time.monotonic() - start) * 1000)
            run.request_headers = headers
            run.save(update_fields=["attempts", "last_attempt_at", "success", "error_message", "duration_ms", "request_headers"])
            break

        headers["X-GDC-Signature"] = _sign_payload(payload_bytes, secret)

        try:
            req = urllib.request.Request(webhook_url, data=payload_bytes, method="POST")
            for key, value in headers.items():
                req.add_header(key, value)
            with urllib.request.urlopen(req, timeout=settings.GDC_WEBHOOK_TIMEOUT) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                run.status_code = resp.getcode()
                run.response_body_snippet = body[:1000]
                run.success = 200 <= resp.getcode() < 300
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            run.status_code = exc.code
            run.response_body_snippet = body[:1000]
            run.error_message = f"HTTPError: {exc}"
            run.success = False
        except Exception as exc:  # noqa: BLE001
            run.error_message = str(exc)
            run.success = False
        finally:
            run.duration_ms = int((time.monotonic() - start) * 1000)
            run.request_headers = headers
            run.save(
                update_fields=[
                    "attempts",
                    "last_attempt_at",
                    "status_code",
                    "success",
                    "error_message",
                    "response_body_snippet",
                    "duration_ms",
                    "request_headers",
                ]
            )

        if run.success:
            break

    AuditEvent.log(
        event_type="automation.run",
        model_name="AutomationRun",
        object_id=str(run.id),
        action="create",
        metadata={
            "correlation_id": str(run.correlation_id),
            "event_type": event_type,
            "lead_id": str(lead_id) if lead_id else None,
            "success": run.success,
            "attempts": run.attempts,
        },
    )
    return run


def send_lead_created_webhook(lead):
    correlation_id = uuid.uuid4()
    payload = _build_payload("lead.created", correlation_id, lead=lead)
    return _send_webhook("lead.created", payload, lead_id=lead.id)


def send_lead_overdue_webhook(lead):
    correlation_id = uuid.uuid4()
    payload = _build_payload("lead.overdue", correlation_id, lead=lead)
    return _send_webhook("lead.overdue", payload, lead_id=lead.id)


def _priority_leads(now, limit=5):
    today = timezone.localdate(now)
    stale_cutoff = now - timedelta(days=7)
    qs = (
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
        .order_by("priority_rank", "-value_estimate")[:limit]
    )
    return [
        {
            "lead_id": str(lead.id),
            "business_name": lead.business_name,
            "stage": lead.stage.name,
            "next_action_due": _unix_ts(lead.next_action_due) if lead.next_action_due else None,
        }
        for lead in qs
    ]


def send_daily_summary_webhook(now=None):
    now = now or timezone.now()
    today = timezone.localdate(now)
    stale_cutoff = now - timedelta(days=7)

    summary = {
        "counts": {
            "new_leads": Lead.objects.filter(created_at__date=today).count(),
            "overdue": Lead.objects.filter(next_action_due__lt=now, next_action_due__isnull=False).count(),
            "due_today": Lead.objects.filter(next_action_due__date=today).count(),
            "stale": Lead.objects.filter(
                Q(last_interaction_date__lte=stale_cutoff)
                | Q(last_interaction_date__isnull=True, first_contact_date__lte=stale_cutoff)
            ).count(),
        },
        "top_priorities": _priority_leads(now, limit=5),
    }

    correlation_id = uuid.uuid4()
    payload = _build_payload("daily.summary", correlation_id, summary=summary)
    return _send_webhook("daily.summary", payload)
