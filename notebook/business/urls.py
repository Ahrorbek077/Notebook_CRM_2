# notebook/business/urls.py
from django.urls import path
from .views import BusinessListView, BusinessCreateView, BusinessDeleteView, BusinessSwitchView

app_name = 'business'

urlpatterns = [
    path('list/',   BusinessListView.as_view(),   name='business_list'),
    path('create/', BusinessCreateView.as_view(), name='business_create'),
    path('delete/<int:pk>/', BusinessDeleteView.as_view(), name='business_delete'),
    path('switch/', BusinessSwitchView.as_view(), name='business_switch'),
]
