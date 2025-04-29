# marketing
 Simple email marketing plugin for Django


## Settings Variables
```
MAILGUN_DOMAIN
EMAIL_NAME
EMAIL_COMPANY
MAILGUN_API_KEY
```

## Installed Apps
```
INSTALLED_APPS = [

	...
	'marketing',
	'django_crontab',
]
```
## Add an Hourly Cronjob
```
CRONJOBS = [
    ('0 * * * *', 'marketing.management.commands.check_schedules'),  # Run every hour
]
```

## Register Cronjob
```
python manage.py crontab add
```

## Verify Cronjobs
```
python manage.py crontab show
```