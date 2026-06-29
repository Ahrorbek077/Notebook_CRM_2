# notebook/inbox/urls.py
from django.urls import path
from .views import (
    BankWebhookView, IncomingTransactionListView,
    MatchTransactionView, IgnoreTransactionView, RegenerateWebhookTokenView,
)

app_name = 'inbox'

urlpatterns = [
    path('webhook/<str:token>/', BankWebhookView.as_view(),            name='webhook'),
    path('',                     IncomingTransactionListView.as_view(), name='list'),
    path('<int:pk>/match/',      MatchTransactionView.as_view(),        name='match'),
    path('<int:pk>/ignore/',     IgnoreTransactionView.as_view(),       name='ignore'),
    path('regenerate-token/',    RegenerateWebhookTokenView.as_view(),  name='regenerate_token'),
]
