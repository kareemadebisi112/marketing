# Generated by Django 5.2 on 2025-04-29 18:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0007_schedule'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='current_step',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='campaign',
            name='total_steps',
            field=models.IntegerField(default=1),
        ),
    ]
