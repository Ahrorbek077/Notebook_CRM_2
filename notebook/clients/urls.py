# notebook/clients/urls.py
from django.urls import path
from .views.web_views import (
    ClientListView, ClientCreateView, ClientUpdateView,
    ClientDeleteView, ClientDetailView,
    RegionSaveView, RegionDeleteView,
    SaleReceiptView,
    SaleReceiptPdfView,
    SaleReceiptPngView,
    SaleReceiptEscposView,
)

app_name = 'clients'

urlpatterns = [
    path('list/',                   ClientListView.as_view(),    name='client_list'),
    path('create/',                 ClientCreateView.as_view(),  name='client_create'),
    path('update/',                 ClientUpdateView.as_view(),  name='client_update'),
    path('delete/',                 ClientDeleteView.as_view(),  name='client_delete'),
    path('client/<int:pk>/',        ClientDetailView.as_view(),  name='client_detail'),
    path('region/save/',            RegionSaveView.as_view(),    name='region-save'),
    path('region/delete/<int:pk>/', RegionDeleteView.as_view(),  name='region-delete'),

    # ── Chek ────────────────────────────────────────────────────────────────
    path('receipt/<int:sale_id>/',  SaleReceiptView.as_view(),   name='sale_receipt'),
    path('receipt/<int:sale_id>/pdf/',  SaleReceiptPdfView.as_view(),   name='sale_receipt_pdf'),
    path('receipt/<int:sale_id>/png/',  SaleReceiptPngView.as_view(),   name='sale_receipt_png'),
    path('receipt/<int:sale_id>/escpos/',  SaleReceiptEscposView.as_view(),   name='sale_receipt_escpos'),
]
