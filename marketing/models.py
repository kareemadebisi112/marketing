# models.py
from django.db import models
import random
from django.utils.text import slugify
from django.urls import reverse
from django.utils.timezone import now, localtime
from django.utils import timezone


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class EmailContact(BaseModel):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    ab_variant = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B')], blank=True, null=True)
    subscribed = models.BooleanField(default=True)
    engaged = models.BooleanField(default=False)  # Indicates if the user has engaged with the email (opened/clicked)

    def __str__(self):
        return self.email

    # overwrite the save method to handle A/B testing logic
    def save(self, *args, **kwargs):
        if not self.ab_variant:
            # Assign A or B randomly
            self.ab_variant = 'A' if random.choice([True, False]) else 'B'
        if self.engaged:
            self.subscribed = False  # Self determined based on engagement
        super().save(*args, **kwargs)


class EmailEvent(BaseModel):
    email = models.EmailField()
    event_type = models.CharField(max_length=50)  # e.g., opened, clicked, unsubscribed
    timestamp = models.DateTimeField()
    metadata = models.JSONField()

class EmailTemplate(BaseModel):
    # name = models.CharField(max_length=255)
    subject_a = models.CharField(max_length=255)
    subject_b = models.CharField(max_length=255)
    template = models.TextField()

    def __str__(self):
        return f"Email Template - {self.subject_a} / {self.subject_b}"
    
    def get_absolute_url(self):
        return reverse('marketing:view_email_template', args=[self.id])

class EmailObject(BaseModel):
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=[('sent', 'Sent'), ('failed', 'Failed')], default='sent')
    contact = models.ForeignKey(EmailContact, on_delete=models.CASCADE, related_name='emails')
    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE, related_name='emails', blank=True, null=True)
    opened = models.BooleanField(default=False)
    replied = models.BooleanField(default=False)

    def __str__(self):
        return f"Email to {self.contact.email} - {self.subject}"
    
class MailingList(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    contacts = models.ManyToManyField(EmailContact, related_name='mailing_lists')

    def __str__(self):
        return self.name
    
class Campaign(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=50,
        choices=[('draft', 'Draft'), ('active', 'Active'), ('completed', 'Completed')],
        default='draft'
    )
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    mailing_lists = models.ManyToManyField(MailingList, related_name='campaigns', blank=True)
    templates = models.ManyToManyField(
        EmailTemplate,
        related_name='campaigns',
        through='CampaignEmailTemplate',
        blank=True
    )
    current_step = models.IntegerField(default=0)  # Step in the campaign process
    total_steps = models.IntegerField(default=0)  # Total steps in the campaign process
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.pk:  # Check if the campaign already exists
            if self.templates.exists():
                self.total_steps = self.templates.count()
        super().save(*args, **kwargs)

class CampaignEmailTemplate(BaseModel):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='email_templates')
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, related_name='campaign_email_templates')
    order = models.IntegerField()  # Step in the campaign process

    class Meta:
        unique_together = ('campaign', 'template')

    def __str__(self):
        return f"{self.campaign.name} - {self.template.subject_a} / {self.template.subject_b}"
    
class Schedule(BaseModel):
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    time = models.TimeField()
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='schedules')
    active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        day = dict(self.DAYS_OF_WEEK).get(self.day_of_week, 'Unknown')
        return f"{day} at {self.time}"
    
    def save(self, *args, **kwargs):
        if self.active:
            today = localtime(now())
            if self.last_run:
                self.next_run = self.last_run + timezone.timedelta(days=7)
            else:
                next_run_date = today + timezone.timedelta(days=(self.day_of_week - today.weekday()) % 7)
                self.next_run = timezone.datetime.combine(next_run_date, self.time, tzinfo=timezone.get_current_timezone())
        if not self.active:
            self.next_run = None
        super().save(*args, **kwargs)