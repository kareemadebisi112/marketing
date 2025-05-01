# views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.utils.dateparse import parse_datetime
from .models import EmailContact, EmailEvent, EmailObject
from .utils import send_ab_email
import datetime
from django.shortcuts import render
import os
import json

        
def index(request):
    contacts = []
    for contact in EmailContact.objects.all().order_by('ab_variant'):
        contacts.append({
            'email': contact.email,
            'first_name': contact.first_name,
            'ab_variant': contact.ab_variant,
        })    
    context = {
        'contacts': contacts,
    }
    if not contacts:
        return JsonResponse({'emails': []})
    return render(request, 'index.html', context)

def view_email_template_a(request):
    contact = EmailContact.objects.filter(ab_variant='A').first()
    if contact:
        context = {
            'contact': contact,
            'variant': contact.ab_variant,
        }
        return render(request, 'emails/day_3.html', context)
    return render(request, 'emails/variant_A.html')

def view_email_template_b(request):
    contact = EmailContact.objects.filter(ab_variant='B').first()
    if contact:
        context = {
            'contact': contact,
            'variant': contact.ab_variant,
        }
        return render(request, 'emails/variant_B.html', context)
    return render(request, 'emails/variant_B.html')

@csrf_exempt
def mailgun_webhook(request):
    if request.method == "POST":
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

        event_data = payload.get('event-data', {})
        # event = event_data.get('event')
        # email = event_data.get('recipient')
        # timestamp = datetime.datetime.fromtimestamp(event_data.get('timestamp', 0))

        # EmailEvent.objects.create(
        #     email=email,
        #     event_type=event,
        #     timestamp=timestamp,
        #     metadata=event_data
        # )

        # if event == 'unsubscribed':
        #     EmailContact.objects.filter(email=email).update(subscribed=False)

        # if event == 'opened':
        #     email_contact = EmailContact.objects.filter(email=email).first()
        #     if email_contact:
        #     email_obj = EmailObject.objects.filter(contact=email_contact, opened=False).first()
        #     if email_obj:
        #         email_obj.opened = True
        #         email_obj.save()

        return JsonResponse({'status': 'success', 'payload': event_data}, status=200)
        # event = payload.get('event')
        # email = payload.get('recipient')
        # timestamp = parse_datetime(payload.get('timestamp'))
        
        # EmailEvent.objects.create(
        #     email=email,
        #     event_type=event,
        #     timestamp=timestamp,
        #     metadata=payload
        # )

        # if event == 'unsubscribed':
        #     EmailContact.objects.filter(email=email).update(subscribed=False)

        # if event == 'opened':
        #     email_contact = EmailContact.objects.filter(email=email).first()
        #     if email_contact:
        #         email = EmailObject.objects.filter(contact=email_contact, opened=False).first()
        #         if email:
        #             email.opened = True
        #             email.save()
        # return JsonResponse(payload)
    elif request.method == "GET":
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'invalid method'}, status=405)

def unsubscribe_view(request, email):
    EmailContact.objects.filter(email=email).update(subscribed=False)
    return HttpResponse("You've been unsubscribed.")


def send_mail_view(request):
    for contact in EmailContact.objects.all():
        print(contact.email, contact.ab_variant)
        status_code, response_text,subject, html = send_ab_email(contact)
        if status_code != 200:
            return JsonResponse({'status': 'failed to send email', 'response': response_text}, status=status_code)
        else:
            email = EmailObject(
                subject=subject,
                body=html,
                contact=contact,
                status="sent",
                sent_at=datetime.datetime.now(),
            )
            email.save()
    return JsonResponse({'status': 'emails sent successfully'})
