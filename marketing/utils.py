# utils.py
import requests
from django.conf import settings
from django.template.loader import render_to_string
import json
import csv
# from .models import Email

MAILGUN_API_URL = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
MAILGUN_API_KEY = settings.MAILGUN_API_KEY

def send_ab_email(contact):
    pass
    if not contact.subscribed:
        return

    variant = contact.ab_variant or 'A'
    subject = "Save More Today!" if variant == 'A' else "Unlock Your Exclusive Deal"
    html = render_to_string(f"emails/variant_{variant}.html")
    lower_name = settings.EMAIL_NAME.lower()

    data = {
        "from": f"{settings.EMAIL_NAME} @ {settings.EMAIL_COMPANY} <{lower_name}@{settings.MAILGUN_DOMAIN}>",
        "to": contact.email,
        "subject": subject,
        "html": html,
        "o:tracking": "yes",
        "o:tag": [f"test_campaign_2025", f"variant_{variant}"],
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