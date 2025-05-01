from django.core.management.base import BaseCommand
from django.utils.timezone import now
from marketing.marketing.models import Schedule, EmailObject
from marketing.marketing.utils import send_ab_email

class Command(BaseCommand):
    help = "Check and send scheduled emails."

    def handle(self, *args, **kwargs):
        current_day = now().weekday() # 0 = Monday, 6 = Sunday
        current_hour = now().time().hour
        current_time = f"{current_hour:02d}:00:00"

        # Find active schedules for current day and time
        schedules = Schedule.objects.filter(
            day_of_week=current_day,
            time__lte=current_time,
            active=True
        )

        for schedule in schedules:
            campaign = schedule.campaign
            if campaign.status == 'active':
                # Get all contacts in the campaign's mailing lists
                contacts = campaign.mailing_lists.values_list('contacts', flat=True)
                for contact in contacts:
                    status_code, response_text, subject, html = send_ab_email(contact, campaign)
                    if status_code == 200:
                        # Save the email record
                        EmailObject.objects.create(
                            subject=subject,
                            body=html,
                            contact=contact,
                            sent_at=now(),
                            status='sent'
                        )
                        self.stdout.write(self.style.SUCCESS(f"Email sent to {contact.email} with subject: {subject}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"Failed to send email to {contact.email}: {response_text}"))

                campaign.current_step += 1
                if campaign.current_step >= campaign.total_steps:
                    campaign.status = 'completed'
                    campaign.save()
                else:
                    campaign.save()
                    self.stdout.write(self.style.SUCCESS(f"Campaign {campaign.name} step updated to {campaign.current_step}."))
        
        # Proof of life
        self.stdout.write(self.style.SUCCESS(f"Checked schedule at {current_time}."))