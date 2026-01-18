"""Shared base models and managers."""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """Base model for all GDC entities."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class ActiveObjectsManager(models.Manager):
    """Manager that excludes soft-deleted records by default."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
