# notebook/containers/urls.py
from django.urls import path
from . import views

app_name = 'containers'

urlpatterns = [
    path('types/',                          views.ContainerTypeListView.as_view(),     name='type-list'),
    path('types/create/',                   views.ContainerTypeCreateView.as_view(),   name='type-create'),

    path('client/<int:client_id>/summary/',  views.ClientContainerSummaryView.as_view(), name='client-summary'),
    path('client/<int:client_id>/give/',     views.GiveContainerView.as_view(),         name='give'),
    path('client/<int:client_id>/return/',   views.ReturnContainerView.as_view(),       name='return'),

    path('branch/<int:branch_id>/stock/',    views.BranchContainerStockView.as_view(),  name='branch-stock'),
]