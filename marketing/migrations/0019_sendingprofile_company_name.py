# Generated by Django 5.2 on 2025-05-19 21:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0018_sendingprofile_emailcontact_last_sender'),
    ]

    operations = [
        migrations.AddField(
            model_name='sendingprofile',
            name='company_name',
            field=models.CharField(default='Mailgun Sandbox', max_length=255),
        ),
    ]
