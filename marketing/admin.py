from .models import EmailContact, EmailEvent, EmailObject, Campaign, MailingList, Schedule, CampaignEmailTemplate, EmailTemplate
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import CSVUploadForm
import csv

# admin.site.register(EmailContact)
DAYS_OF_WEEK = [
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
]
@admin.register(EmailObject)
class EmailObjectAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sent_at', 'status', 'contact', 'opened')
    list_filter = ('status', 'sent_at', 'opened')
    search_fields = ('subject', 'contact__email')
@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'start_date', 'end_date', 'next_schedule_run', 'total_steps')
    # def get_queryset(self, request):
    #     queryset = super().get_queryset(request)
    #     return queryset.filter(status='active')
    list_editable = ('status',)
    ordering = ('start_date',)
    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('mailing_lists',)

    class CampaignEmailTemplateInline(admin.TabularInline):
        model = CampaignEmailTemplate
        extra = 1

    class ScheduleInline(admin.TabularInline):
        model = Schedule
        extra = 1

    inlines = [CampaignEmailTemplateInline, ScheduleInline]

    def next_schedule_run(self, obj):
        next_schedule = obj.schedules.filter(active=True).order_by('next_run').first()
        return next_schedule.next_run if next_schedule else "No active schedule"
    next_schedule_run.admin_order_field = 'schedules__next_run'
    next_schedule_run.short_description = 'Next Schedule Run'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.order_by('name')
@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('subject_a', 'subject_b')
    search_fields = ('subject_a', 'subject_b')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'day_of_week_display', 'time', 'campaign', 'active', 'last_run', 'next_run')
    list_filter = ('day_of_week', 'campaign', 'active')
    search_fields = ('name', 'campaign__name')
    # list_editable = ('active', 'time')
    ordering = ('next_run',)


    def day_of_week_display(self, obj):
        return dict(DAYS_OF_WEEK).get(obj.day_of_week, 'Unknown')
    day_of_week_display.short_description = 'Day of Week'

@admin.register(MailingList)
class MailingListAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'total_emails')
    filter_horizontal = ('contacts',)

    def total_emails(self, obj):
        return obj.contacts.count()
    total_emails.short_description = 'Total Emails'

@admin.register(EmailContact)
class EmailContactAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'company', 'industry', 'ab_variant', 'subscribed', 'engaged')
    list_filter = ('ab_variant', 'subscribed', 'engaged', 'industry', 'mailing_lists')
    list_editable = ('engaged',)
    search_fields = ('email', 'first_name', 'last_name', 'company', 'industry')


    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.admin_site.admin_view(self.upload_csv), name='upload_csv'),
        ]
        return custom_urls + urls

    def upload_csv(self, request):
        if request.method == "POST":
            form = CSVUploadForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES['csv_file']
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.reader(decoded_file)
                for i, row in enumerate(reader):
                    if i == 0:  # Skip the header row
                        continue
                    try:
                        first_name, last_name, title, company, email, corporate_phone, industry, mailing_list = row
                    except ValueError:
                        messages.error(request, f"Row {i + 1} has an incorrect number of columns. Skipping.")
                        continue
                    if email:
                        if EmailContact.objects.filter(email=email).exists():
                            messages.warning(request, f"Email {email} already exists. Skipping.")
                            continue
                        contact = EmailContact.objects.create(
                            first_name=first_name,
                            last_name=last_name,
                            title=title,
                            company=company,
                            email=email,
                            phone=corporate_phone,
                            industry=industry,
                        )
                        # Add to mailing list if specified
                        if mailing_list:
                            mailing_list_obj, created = MailingList.objects.get_or_create(name=mailing_list)
                            mailing_list_obj.contacts.add(contact)
            messages.success(request, "Emails added successfully from CSV.")
            return redirect("..")
        else:
            form = CSVUploadForm()

        context = {
            'form': form,
            'title': "Upload CSV File",
        }
        return render(request, 'admin/upload_csv.html', context)
    
@admin.register(EmailEvent)
class EmailEventAdmin(admin.ModelAdmin):
    list_display = ('event_type','email', 'timestamp')
    list_filter = ('event_type', 'timestamp', 'email')
    search_fields = ('email_object__subject', 'contact__email')
