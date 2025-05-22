"""
URL configuration for marketing project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from marketing.marketing.views import mailgun_webhook, unsubscribe_view, view_email_template, index, analytics_view, analytics_demo

app_name = 'marketing'  # Namespace for the app


urlpatterns = [
    # path('', index, name='index'), # Remove when added to the main app
    # path('admin/', admin.site.urls),
    path('mailgun/webhook/', mailgun_webhook, name='mailgun_webhook'),
    path('unsubscribe/<str:email>/', unsubscribe_view, name='unsubscribe'),
    path('email_template/<int:id>/', view_email_template, name='view_email_template'),  # Remove when live
    path('analytics/', analytics_view, name='analytics'),
    path('analytics_demo/', analytics_demo, name='analytics_demo'),  # Remove when live
    # path('send_email/', send_mail_view, name='send_email'),  # This should be a POST request in production
    # path('email_template_a/', view_email_template_a, name='email_template_a'), # Remove when live
    # path('email_template_b/', view_email_template_b, name='email_template_b'),
]
