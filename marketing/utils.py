# utils.py
import requests
from django.conf import settings
from django.template.loader import render_to_string
import json
import csv
import hmac
import hashlib
# from .models import EmailObject

MAILGUN_API_URL = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
MAILGUN_API_KEY = settings.MAILGUN_API_KEY

EMAIL_VARIATIONS = {
    "A": {
        0: {"subject": "Unlock Hours with Simple Automation", "template": "emails/day_1.html"},
        1: {"subject": "Quick Follow-Up: Ready to Chat About Automation?", "template": "emails/day_2.html"},
        2: {"subject": "Should I Circle Back Another Time?", "template": "emails/day_3.html"},
    },
    "B": {
        0: {"subject": "Let's Automate the Boring Stuff in Your Workflow", "template": "emails/day_1.html"},
        1: {"subject": "Still curious about automation?", "template": "emails/day_2.html"},
        2: {"subject": "Let’s Cut the Manual Work", "template": "emails/day_3.html"},
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


def verify_mailgun_signature(request):
        try:
            payload = json.loads(request.body.decode('utf-8'))
            signature_data = payload.get('signature', {})
            timestamp = signature_data.get('timestamp')
            token = signature_data.get('token')
            signature = signature_data.get('signature')
        except json.JSONDecodeError:
            return False, ("Invalid JSON")
        except KeyError:
            return False, ("Missing required fields")
        
        if not timestamp or not token or not signature:
            return False, ("Missing required fields")
        
        # Create the signature string
        signature_string = f"{timestamp}{token}"
        # Decode the API key
        api_key = settings.MAILGUN_API_KEY.encode('utf-8')
        # Create the HMAC signature
        hmac_signature = hmac.new(api_key, signature_string.encode('utf-8'), hashlib.sha256).hexdigest()
        # Compare the HMAC signature with the provided signature
        if hmac.compare_digest(hmac_signature, signature):
            return True, ("Signature is valid")
        else:
            return False, ("Signature is invalid")
        
        