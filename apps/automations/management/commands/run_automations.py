from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.automations.models import AutomationRun
from apps.automations.services import send_daily_summary_webhook, send_lead_overdue_webhook
from apps.crm.models import Lead


class Command(BaseCommand):
    help = "Runs automation hooks (overdue and daily summary)."

    def add_arguments(self, parser):
        parser.add_argument("--overdue", action="store_true", help="Send overdue lead notifications")
        parser.add_argument("--daily-summary", action="store_true", help="Send daily summary")

    def handle(self, *args, **options):
        if not settings.GDC_AUTOMATIONS_ENABLED:
            self.stdout.write("Automations disabled.")
            return

        run_overdue = options["overdue"]
        run_daily = options["daily_summary"]
        if not run_overdue and not run_daily:
            run_overdue = True
            run_daily = True

        now = timezone.now()
        today = timezone.localdate(now)

        if run_overdue:
            overdue_qs = Lead.objects.filter(next_action_due__lt=now, next_action_due__isnull=False)
            sent = 0
            for lead in overdue_qs:
                already_sent = AutomationRun.objects.filter(
                    event_type="lead.overdue",
                    lead_id=lead.id,
                    created_at__date=today,
                    success=True,
                ).exists()
                if already_sent:
                    continue
                send_lead_overdue_webhook(lead)
                sent += 1
            self.stdout.write(f"Overdue notifications sent: {sent}")

        if run_daily:
            already_sent = AutomationRun.objects.filter(
                event_type="daily.summary",
                created_at__date=today,
                success=True,
            ).exists()
            if already_sent:
                self.stdout.write("Daily summary already sent today.")
            else:
                send_daily_summary_webhook(now=now)
                self.stdout.write("Daily summary sent.")
