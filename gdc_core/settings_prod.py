"""Production settings stub (unused for now)."""
from .settings import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if host.strip()]
