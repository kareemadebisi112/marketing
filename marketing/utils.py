# utils.py
import requests
from django.conf import settings
from django.template import Template, Context
import json
import hmac
import hashlib

MAILGUN_API_URL = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
MAILGUN_API_KEY = settings.MAILGUN_API_KEY

def send_email(contact, campaign, email_template):
    if not (contact.subscribed and email_template):
        return None  # Skip if unsubscribed or no template provided

    current_step = campaign.current_step
    if current_step >= campaign.total_steps or campaign.status == 'completed':
        return None  # No more steps to send emails for

    subject = (email_template.subject_a if contact.ab_variant == 'A' 
               else email_template.subject_b).replace(
                   "{{ contact.company }}", contact.company or "Your Company")

    context = {"contact": contact, "current_step": current_step, "total_steps": campaign.total_steps}
    template = Template(email_template.template)
    html = template.render(Context(context))

    data = {
        "from": f"{settings.EMAIL_NAME} @ {settings.EMAIL_COMPANY} <{settings.EMAIL_NAME.lower()}@{settings.MAILGUN_DOMAIN}>",
        "to": contact.email,
        "subject": subject,
        "html": html,
        "o:tracking": "yes",
        "o:tag": [campaign.slug, f"variant_{contact.ab_variant}"],
        "h:X-Mailgun-Variables": json.dumps({"user_id": contact.id}),
        "o:tracking-clicks": "yes",
        "o:tracking-opens": "yes",
    }

    response = requests.post(MAILGUN_API_URL, auth=("api", MAILGUN_API_KEY), data=data)
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
        
        