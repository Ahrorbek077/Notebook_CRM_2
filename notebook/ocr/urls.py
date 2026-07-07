# notebook/ocr/urls.py
from django.urls import path
from .views import ReceiptScanView, ReceiptConfirmView

app_name = 'ocr'

urlpatterns = [
    path('api/branch/<int:pk>/scan/',    ReceiptScanView.as_view(),    name='scan'),
    path('api/branch/<int:pk>/confirm/', ReceiptConfirmView.as_view(), name='confirm'),
]
