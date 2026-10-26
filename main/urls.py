from django.urls import path

from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('education/', views.education, name='education'),
    path('gallery/', views.gallery, name='gallery'),
    path('news/', views.news, name='news'),
    path('contact/', views.contact, name='contact'),

    path('join/', views.join, name='join'),
    path('volunteers/', views.volunteers, name='volunteers'),

    path('donation/', views.donation, name='donation'),
    path('donation/create-order/', views.donation_create_order, name='donation_create_order'),
    path('donation/save/', views.donation_save, name='donation_save'),
    path('donation/webhook/', views.donation_webhook, name='donation_webhook'),

    path('cron/fetch-news/', views.cron_fetch_news, name='cron_fetch_news'),
    path('cron/fetch-schemes/', views.cron_fetch_schemes, name='cron_fetch_schemes'),

    path('artisan-support/', views.artisan_support, name='artisan_support'),
]