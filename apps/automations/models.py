from __future__ import annotations

import uuid

from django.db import models

from apps.core.models import BaseModel


class AutomationRun(BaseModel):
    correlation_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    lead_id = models.UUIDField(null=True, blank=True, db_index=True)
    webhook_url = models.URLField()
    payload_hash = models.CharField(max_length=64)
    status_code = models.IntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    attempts = models.IntegerField(default=0)
    request_headers = models.JSONField(null=True, blank=True)
    response_body_snippet = models.TextField(blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    payload_preview = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["lead_id", "event_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} {self.created_at:%Y-%m-%d %H:%M:%S}"
