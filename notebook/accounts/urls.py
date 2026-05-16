from django.urls import path
from notebook.accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('staff/', views.StaffListView.as_view(), name='staff-list'),
    path('staff/create/', views.StaffCreateView.as_view(),name='staff-create'),
    path('staff/<int:user_id>/edit/', views.StaffEditView.as_view(), name='staff-edit'),
    path('staff/<int:user_id>/fire/', views.StaffFireView.as_view(), name='staff-fire'),
    path('settings/', views.SettingsView.as_view(),  name='settings'),
    path('directory/', views.DirectoryView.as_view(), name='directory'),
]
