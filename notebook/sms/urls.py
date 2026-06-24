# notebook/sms/urls.py
from django.urls import path
from .views import SendBalanceSmsView

app_name = 'sms'

urlpatterns = [
    path('send/<int:client_id>/', SendBalanceSmsView.as_view(), name='send-balance-sms'),
]
