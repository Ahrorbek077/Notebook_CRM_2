from django.urls import path
from .views.web_views import LauncherView, DashboardView, AnalyticsView, SaleHistoryView, StockHistoryView
from .views.api_views import dashboard_api, analytics_api

app_name = 'dashboard'

urlpatterns = [
    path('',              LauncherView.as_view(),    name='launcher'),
    path('template/',     DashboardView.as_view(),   name='dashboard'),
    path('analytics/',    AnalyticsView.as_view(),   name='analytics'),
    path('history/sales/',SaleHistoryView.as_view(), name='history-sales'),
    path('history/stock/',StockHistoryView.as_view(),name='history-stock'),
    path('api/',          dashboard_api,             name='dashboard_api'),
    path('api/analytics/',analytics_api,             name='analytics_api'),
]
