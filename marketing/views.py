# views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from .models import EmailContact, EmailEvent, EmailObject, EmailTemplate, Campaign, Schedule, MailingList, SendingProfile
from .utils import send_email, verify_mailgun_signature
import datetime
from django.shortcuts import render
import json
from django.template import Template, Context
from django.db.models import Count, Q
import requests
from django.conf import settings
from django.shortcuts import get_object_or_404

        
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
    sender = SendingProfile.objects.filter(active=True).first()    
    contact = EmailContact.objects.filter(ab_variant='A').first()
    if contact:
        context = {
            'contact': contact,
            'variant': contact.ab_variant,
            'sender': sender,
        }

    template = EmailTemplate.objects.get(id=id)
    template_content = template.template
    subject = template.subject_a if contact.ab_variant == 'A' else template.subject_b
    subject = subject.replace("{{ contact.company }}", contact.company or "Your Company")
    rendered_template = f"<h1>{subject}</h1>" + Template(template_content).render(Context(context))

    return HttpResponse(rendered_template)


def analytics_demo(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized access'}, status=403)
    
    return render(request, 'analytics_demo.html')


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

def analytics_view(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

    # Calculate general analytics
    total_contacts = EmailContact.objects.count()
    total_campaigns = Campaign.objects.count()
    total_emails_sent = EmailObject.objects.filter(status='sent').count()
    total_emails_opened = EmailObject.objects.filter(opened=True).count()
    total_emails_failed = EmailObject.objects.filter(status='failed').count()
    total_unsubscribed = EmailContact.objects.filter(subscribed=False).count()
    total_emails_clicked = EmailEvent.objects.filter(event_type='clicked').count()
    engaged_contacts = EmailContact.objects.filter(engaged=True).count()

    # Calculate rates
    open_rate = (total_emails_opened / total_emails_sent * 100) if total_emails_sent > 0 else 0
    bounce_rate = (total_emails_failed / total_emails_sent * 100) if total_emails_sent > 0 else 0
    unsubscribe_rate = (total_unsubscribed / total_contacts * 100) if total_contacts > 0 else 0
    click_rate = (total_emails_clicked / total_emails_sent * 100) if total_emails_sent > 0 else 0

    campaign_analytics = Campaign.objects.annotate(
        emails_sent=Count('emails', filter=Q(emails__status='sent')),
        emails_opened=Count('emails', filter=Q(emails__opened=True)),
        emails_failed=Count('emails', filter=Q(emails__status='failed')),
        open_rate=Count('emails', filter=Q(emails__opened=True)) * 100.0 / Count('emails', filter=Q(emails__status='sent')),
        emails_replied=Count('emails', filter=Q(emails__replied=True)),
        reply_rate=Count('emails', filter=Q(emails__replied=True)) * 100.0 / Count('emails', filter=Q(emails__status='sent'))
    ).values('name', 'emails_sent', 'emails_opened', 'emails_failed', 'open_rate', 'emails_replied', 'reply_rate').order_by('-emails_sent')

    active_campigns = campaign_analytics.filter(status='active')
    completed_campaigns = campaign_analytics.filter(status='completed')

    # Fetch recent email events
    recent_events = EmailEvent.objects.order_by('-timestamp')[:10].values(
        'email', 'event_type', 'timestamp', 'metadata'
    )

    # Fetch the next-up schedule and its campaign
    next_schedule = Schedule.objects.filter(active=True, next_run__gte=datetime.datetime.now()).order_by('next_run').first()
    next_schedule_data = None
    if next_schedule:
        next_schedule_data = {
            # 'name': next_schedule.name,
            'day_of_week': next_schedule.get_day_of_week_display(),
            'time': next_schedule.time,
            'campaign': next_schedule.campaign.name,
            'next_run': next_schedule.next_run,
        }
    
    # Pass analytics data to the template
    context = {
        'total_contacts': total_contacts,
        'total_campaigns': total_campaigns,
        'total_emails_sent': total_emails_sent,
        'total_emails_opened': total_emails_opened,
        'total_emails_failed': total_emails_failed,
        'total_unsubscribed': total_unsubscribed,
        'total_emails_clicked': total_emails_clicked,
        'engaged_contacts': engaged_contacts,
        'open_rate': f"{open_rate:.2f}%",
        'bounce_rate': f"{bounce_rate:.2f}%",
        'unsubscribe_rate': f"{unsubscribe_rate:.2f}%",
        'click_rate': f"{click_rate:.2f}%",
        'active_campigns': active_campigns,
        'completed_campaigns': completed_campaigns,
        'recent_events': recent_events,
        'next_schedule': next_schedule_data,
    }
    return render(request, 'analytics.html', context)

@csrf_exempt
def eventbrite_webhook(request):
    if request.method == "POST":
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
        
        api_url = payload.get('api_url')
        config = payload.get('config', {})
        action = config.get('action')
        user_id = config.get('user_id')
        webhook_id = config.get('webhook_id')
        api_key = settings.EVENTBRITE_API_KEY

        if action == 'test':
            return JsonResponse({'status': 'success', 'message': 'Test successful'}, status=200)

        if action == 'order.placed':
            response = requests.get(api_url, headers={'Authorization': f'Bearer {api_key}'})
            if response.status_code != 200:
                return JsonResponse({'error': 'Failed to fetch order details'}, status=400)
            order = response.json()
            first_name = order.get('first_name')
            last_name = order.get('last_name')
            email = order.get('email')
            event_id = order.get('event_id')

            contact = EmailContact.objects.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                subscribed=True,  # Assuming they are subscribed by default
            )

            mailing_list = get_object_or_404(MailingList, event_id=event_id)
            if mailing_list:
                mailing_list.contacts.add(contact)
                mailing_list.save()
            else:
                mailing_list = MailingList.objects.create(
                    name=f"Event {event_id} Mailing List",
                    event_id=event_id,
                    contacts=[contact],
                )
                
            EmailEvent.objects.create(
                email=email,
                event_type='order.placed',
                timestamp=datetime.datetime.now(),
                metadata={
                    'first_name': first_name,
                    'last_name': last_name,
                    'event_id': event_id,
                    'webhook_id': webhook_id,
                }
            )

            # You can now use these variables as needed, e.g. save to DB or log
            print(f"Contact Saved: {first_name} {last_name}, Email: {email}, Mailing List: {mailing_list.name}")
        return JsonResponse({'status': 'success',}, status=200)
    return JsonResponse({'status': 'invalid method'}, status=405)