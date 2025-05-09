# views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from .models import EmailContact, EmailEvent, EmailObject, EmailTemplate
from .utils import send_email, verify_mailgun_signature
import datetime
from django.shortcuts import render
import json
from django.template import Template, Context

        
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

def view_email_template(request, id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized access'}, status=403)
    
    contact = EmailContact.objects.filter(ab_variant='A').first()
    if contact:
        context = {
            'contact': contact,
            'variant': contact.ab_variant,
        }
    
    template = EmailTemplate.objects.get(id=id)
    template_content = template.template
    subject = template.subject_a if contact.ab_variant == 'A' else template.subject_b
    subject = subject.replace("{{ contact.company }}", contact.company or "Your Company")
    rendered_template = f"<h1>{subject}</h1>" + Template(template_content).render(Context(context))

    return HttpResponse(rendered_template)




@csrf_exempt
def mailgun_webhook(request):
    if request.method == "POST":
        # Verify the Mailgun signature
        # is_valid, message = verify_mailgun_signature(request)
        # if not is_valid:
        #     return JsonResponse({'error': message}, status=400)
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

        event_data = payload.get('event-data', {})
        event = event_data.get('event')
        email = event_data.get('recipient')
        timestamp = datetime.datetime.fromtimestamp(event_data.get('timestamp', 0))

        if email not in EmailContact.objects.values_list('email', flat=True):
            return JsonResponse({'status': 'success', 'event': event, 'email': email, 'timestamp': timestamp, 'type': 'test'}, status=200)

        EmailEvent.objects.create(
            email=email,
            event_type=event,
            timestamp=timestamp,
            metadata=event_data
        )

        if event == 'unsubscribed':
            EmailContact.objects.filter(email=email).update(subscribed=False)

        if event == 'failed':
            email_contact = EmailContact.objects.filter(email=email).first()
            if email_contact:
                # Remove email from mailing list
                email_contact.subscribed = False
                email_contact.save()
                
                email_obj = EmailObject.objects.filter(contact=email_contact, opened=False).first()
                if email_obj:
                    email_obj.status = 'failed'
                    email_obj.save()

        if event == 'opened':
            email_contact = EmailContact.objects.filter(email=email).first()
            if email_contact:
                email_obj = EmailObject.objects.filter(contact=email_contact, opened=False).first()
                if email_obj:
                    email_obj.opened = True
                    email_obj.save()
        
        if event == 'clicked':
            email_contact = EmailContact.objects.filter(email=email).first()
            if email_contact:
                email_obj = EmailObject.objects.filter(contact=email_contact, opened=False).first()
                if email_obj:
                    email_obj.opened = True
                    email_obj.save()

        return JsonResponse({'status': 'success', 'event': event, 'email': email, 'timestamp': timestamp}, status=200)
    elif request.method == "GET":
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'invalid method'}, status=405)

def unsubscribe_view(request, email):
    EmailContact.objects.filter(email=email).update(subscribed=False)
    return HttpResponse("You've been unsubscribed.")


def send_mail_view(request):
    for contact in EmailContact.objects.all():
        print(contact.email, contact.ab_variant)
        status_code, response_text,subject, html = send_email(contact)
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
