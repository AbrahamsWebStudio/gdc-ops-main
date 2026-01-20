from django.core.management.base import BaseCommand

from apps.crm.models import PipelineStage


class Command(BaseCommand):
    """
    WHAT: Creates default pipeline stages
    WHY: Can't add leads without stages
    USAGE: python manage.py seed_pipeline
    """

    help = "Create default CRM pipeline stages"

    def handle(self, *args, **kwargs):
        """
        STAGES EXPLANATION:
        - Cold: First contact, no response yet
        - Warm: Responded positively, exploring
        - Meeting Booked: Agreed to audit/demo
        - Audit Done: Completed free process audit
        - Proposal Sent: Sent pricing & scope
        - Won - Client: Signed, paying client
        - Lost: Rejected or went silent
        """
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
            stage, created = PipelineStage.objects.get_or_create(
                name=name,
                defaults={"order": order, "is_won": is_won, "is_lost": is_lost},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Created stage: {name}"))
            else:
                self.stdout.write(f"ℹ️  Stage already exists: {name}")

        self.stdout.write(self.style.SUCCESS("\n🎉 Pipeline stages ready!"))
