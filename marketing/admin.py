from .models import EmailContact, EmailEvent, EmailObject, Campaign, MailingList, Schedule
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import CSVUploadForm
import csv

# admin.site.register(EmailContact)
admin.site.register(EmailEvent)
admin.site.register(EmailObject)
admin.site.register(Campaign)
# admin.site.register(MailingList)

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'day_of_week', 'time')
    list_filter = ('day_of_week',)
    list_filter = ('campaign',)

@admin.register(MailingList)
class MailingListAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    filter_horizontal = ('contacts',)

@admin.register(EmailContact)
class EmailContactAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'ab_variant', 'subscribed')

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
                for row in reader:
                    first_name, last_name, title, company, email, corporate_phone, industry, mailing_list = row
                    if email:
                        if not email == 'Email':  # Skip the header row
                            EmailContact.objects.create(
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
                                mailing_list_obj.contacts.add(email)
                messages.success(request, "Emails added successfully from CSV.")
                return redirect("..")
        else:
            form = CSVUploadForm()

        context = {
            'form': form,
            'title': "Upload CSV File",
        }
        return render(request, 'admin/upload_csv.html', context)