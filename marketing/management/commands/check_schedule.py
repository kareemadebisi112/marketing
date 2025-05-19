from django.core.management.base import BaseCommand
from django.utils.timezone import now, localtime
from marketing.marketing.models import Schedule, EmailObject, EmailContact, CampaignEmailTemplate
from marketing.marketing.utils import send_email
import random
import time

class Command(BaseCommand):
    help = "Check and send scheduled emails."

    def batch_send_email(self, contacts, campaign, template):
        for contact in contacts:
            if not (contact.subscribed and template):
                self.stdout.write(self.style.WARNING(f"Contact {contact.email} is unsubscribed."))
                continue

            time.sleep(random.randint(10, 30))

            result = send_email(contact, campaign, template)
            
            if result is None:
                self.stdout.write(self.style.ERROR(f"No active sending profile found."))
                continue

            status_code, response_text, subject, html = result

            if status_code == 200:
                EmailObject.objects.create(
                    subject=subject,
                    body=html,
                    contact=contact,
                    sent_at=localtime(now()),
                    status='sent',
                    campaign=campaign,
                )
                self.stdout.write(self.style.SUCCESS(f"Email sent to {contact.email} with subject: {subject}."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Failed to send email to {contact.email}: {response_text}."))

    def handle(self, *args, **kwargs):
        # Convert current time to local timezone
        now = localtime(now())
        current_datetime = now
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
            schedule.last_run = now
            schedule.save()

            campaign = schedule.campaign
            if campaign.status != 'active':
                continue

            campaign_email_template = CampaignEmailTemplate.objects.filter(
                campaign=campaign,
                order=campaign.current_step + 1
                ).first()
            
            if not campaign_email_template:
                self.stdout.write(self.style.ERROR(f"No email template found for campaign {campaign.name} at step {campaign.current_step + 1}."))
                continue
            
            contacts = EmailContact.objects.filter(
                id__in=campaign.mailing_lists.values_list('contacts', flat=True)
                )
            # contacts = list(contacts)
            # random.shuffle(contacts)  # Shuffle contacts for random sending order
            self.stdout.write(self.style.SUCCESS(f"Sending emails to {len(contacts)} contacts for campaign {campaign.name}."))
            self.batch_send_email(contacts, campaign, campaign_email_template.template)

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
        
        # Proof of life
        self.stdout.write(self.style.SUCCESS(f"Checked schedule at {formatted_time}."))