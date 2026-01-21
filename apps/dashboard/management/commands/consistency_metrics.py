import json

from django.core.management.base import BaseCommand

from apps.dashboard.services import get_consistency_metrics


class Command(BaseCommand):
    help = "Prints the consistency metrics payload used by the dashboard."

    def handle(self, *args, **options):
        metrics = get_consistency_metrics()
        self.stdout.write(json.dumps(metrics, indent=2))
