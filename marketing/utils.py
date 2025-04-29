# utils.py
import requests
from django.conf import settings
from django.template.loader import render_to_string
import json
import csv
# from .models import Email

MAILGUN_API_URL = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
MAILGUN_API_KEY = settings.MAILGUN_API_KEY

EMAIL_VARIATIONS = {
    "A": {
        0: {"subject": "Unlock Hours with Simple Automation", "template": "emails/day_1.html"},
        1: {"subject": "“This saved us 15 hours a week” – Real Results from Automation", "template": "emails/day_2.html"},
        2: {"subject": "Closing Soon: Free Consult & Discount for New Clients", "template": "emails/day_3.html"},
    },
    "B": {
        0: {"subject": "Let's Automate the Boring Stuff in Your Workflow", "template": "emails/day_1.html"},
        1: {"subject": "Still curious about automation?", "template": "emails/day_2.html"},
        2: {"subject": "One Last Nudge — Let’s Cut the Manual Work", "template": "emails/day_3.html"},
    },
}

def send_ab_email(contact, campaign):
    if not contact.subscribed:
        return
    
    if contact.ab_variant == 'A':
        email_variation = EMAIL_VARIATIONS["A"]
    else:
        email_variation = EMAIL_VARIATIONS["B"]

    # Determine the email variation based on the current step in the campaign
    current_step = campaign.current_step
    total_steps = campaign.total_steps
    if current_step >= total_steps:
        return  # No more steps to send emails for
    
    email_info = email_variation.get(current_step)
    if not email_info:
        return  # No email info for the current step
    
    context = {
        "contact": contact,
        "current_step": current_step,
        "total_steps": total_steps,
    }
    subject = email_info["subject"]
    template = email_info["template"]
    html = render_to_string(template, context)
    lower_name = settings.EMAIL_NAME.lower()


    data = {
        "from": f"{settings.EMAIL_NAME} @ {settings.EMAIL_COMPANY} <{lower_name}@{settings.MAILGUN_DOMAIN}>",
        "to": contact.email,
        "subject": subject,
        "html": html,
        "o:tracking": "yes",
        "o:tag": [f"{campaign.slug}", f"variant_{contact.ab_variant}"],
        "h:X-Mailgun-Variables": json.dumps({"user_id": contact.id}),
        "o:tracking-clicks": "yes",
        "o:tracking-opens": "yes",
    }

    response = requests.post(
        MAILGUN_API_URL,
        auth=("api", MAILGUN_API_KEY),
        data=data,
    )

    return response.status_code, response.text, subject, html