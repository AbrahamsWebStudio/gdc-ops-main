from django.core.management.base import BaseCommand

from apps.crm.models import PipelineStage


class Command(BaseCommand):
    help = "Create default pipeline stages"

    def handle(self, *args, **kwargs):
        stages = [
            ("Cold", 0, False, False),
            ("Warm", 1, False, False),
            ("Meeting Booked", 2, False, False),
            ("Audit Done", 3, False, False),
            ("Proposal Sent", 4, False, False),
            ("Won - Client", 5, True, False),
            ("Lost", 6, False, True),
        ]

        for name, order, is_won, is_lost in stages:
            PipelineStage.objects.get_or_create(
                name=name,
                defaults={"order": order, "is_won": is_won, "is_lost": is_lost},
            )
            self.stdout.write(f"Created stage: {name}")

        self.stdout.write(self.style.SUCCESS("Pipeline stages seeded!"))
