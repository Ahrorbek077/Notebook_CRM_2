# notebook/expenses/urls.py
from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('',                     views.expenses_page,  name='page'),
    path('api/list/',            views.expense_list,   name='list'),
    path('api/create/',          views.expense_create, name='create'),
    path('api/delete/<int:pk>/', views.expense_delete, name='delete'),
    path('api/stats/',           views.expense_stats,  name='stats'),
]
