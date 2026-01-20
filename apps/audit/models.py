"""Audit logging models."""
from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class AuditEvent(models.Model):
    """Append-only audit log."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                             blank=True)
    user_email = models.EmailField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    event_type = models.CharField(max_length=100, db_index=True)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    action = models.CharField(max_length=50)
    before_data = models.JSONField(null=True, blank=True)
    after_data = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    correlation_id = models.UUIDField(default=uuid.uuid4, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp", "event_type"]),
            models.Index(fields=["model_name", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M')} - {self.event_type} by {self.user_email}"

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValueError("AuditEvent records are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditEvent records are append-only.")

    @classmethod
    def log(
        cls,
        event_type: str,
        model_name: str,
        object_id: str,
        action: str,
        user=None,
        before=None,
        after=None,
        metadata=None,
        request=None,
    ):
        ip = None
        user_agent = ""
        if request:
            forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
            if forwarded_for:
                ip = forwarded_for.split(",")[0].strip()
            else:
                ip = request.META.get("REMOTE_ADDR")
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

        return cls.objects.create(
            user=user,
            user_email=getattr(user, "email", "") or "system",
            ip_address=ip,
            user_agent=user_agent,
            event_type=event_type,
            model_name=model_name,
            object_id=str(object_id),
            action=action,
            before_data=before,
            after_data=after,
            metadata=metadata or {},
        )
