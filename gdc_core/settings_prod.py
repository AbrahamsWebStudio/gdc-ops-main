"""Production settings stub (unused for now)."""
from .settings import *  # noqa: F403
import os

DEBUG = False
ALLOWED_HOSTS = [host.strip() for host in os.getenv(
    "DJANGO_ALLOWED_HOSTS",
    ""
    ).split(",") if host.strip()]


GDC_AUTOMATIONS_ENABLED = os.getenv(
    "GDC_AUTOMATIONS_ENABLED", "true").lower() == "true"
GDC_WEBHOOK_BASE_URL = os.getenv("GDC_WEBHOOK_BASE_URL", "")
GDC_WEBHOOK_TIMEOUT = int(os.getenv("GDC_WEBHOOK_TIMEOUT", "5"))
GDC_AUTOMATIONS_RETRY_MAX = int(os.getenv("GDC_AUTOMATIONS_RETRY_MAX", "3"))
