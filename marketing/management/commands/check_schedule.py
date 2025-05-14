from django.core.management.base import BaseCommand
from django.utils.timezone import now, localtime
from marketing.marketing.models import Schedule, EmailObject, EmailContact, CampaignEmailTemplate
from marketing.marketing.utils import send_email

class Command(BaseCommand):
    help = "Check and send scheduled emails."

    def handle(self, *args, **kwargs):
        # Convert current time to local timezone
        current_datetime = localtime(now())
        current_day = current_datetime.weekday() # 0 = Monday, 6 = Sunday
        current_hour = current_datetime.time().hour
        formatted_time = f"{current_hour:02d}:00:00"

        # Find active schedules for current day and time
        schedules = Schedule.objects.filter(
            day_of_week=current_day,
            time=formatted_time,
            active=True
        )

        batch_size = 10  # Number of emails to send in one batch
        delay = 2  # Delay in seconds between batches

        for schedule in schedules:
            campaign = schedule.campaign
            if campaign.status != 'active':
                continue

            campaign_email_template = CampaignEmailTemplate.objects.filter(
                campaign=campaign,
                order=campaign.current_step + 1
                ).first()
            contacts = EmailContact.objects.filter(
                id__in=campaign.mailing_lists.values_list('contacts', flat=True)
                )

            for contact in contacts:
                status_code, response_text, subject, html = send_email(contact, campaign, campaign_email_template.template)
                if not status_code:
                    self.stdout.write(self.style.WARNING(f"Contact {contact.email} is unsubscribed."))
                    continue
                if status_code == 200:
                    EmailObject.objects.create(
                        subject=subject,
                        body=html,
                        contact=contact,
                        sent_at=localtime(now()),
                        status='sent'
                        )
                    self.stdout.write(self.style.SUCCESS(f"Email sent to {contact.email} with subject: {subject} on Schedule {schedule.name}."))
                elif status_code:
                    self.stdout.write(self.style.ERROR(f"Failed to send email to {contact.email}: {response_text}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"Email not sent to unsubscribed {contact.email}."))

            campaign.current_step += 1
            campaign.status = 'completed' if campaign.current_step >= campaign.total_steps else campaign.status
            campaign.save()
            self.stdout.write(self.style.SUCCESS(f"Campaign {campaign.name} step updated to {campaign.current_step}."))

            if campaign.status == 'completed':
                related_schedules = Schedule.objects.filter(campaign=campaign)
                for related_schedule in related_schedules:
                    related_schedule.active = False
                    related_schedule.save()
                schedule.active = False

            schedule.last_run = localtime(now())
            schedule.save()

        
        # Proof of life
        self.stdout.write(self.style.SUCCESS(f"Checked schedule at {formatted_time}."))