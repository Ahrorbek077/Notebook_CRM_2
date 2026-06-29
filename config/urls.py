# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import set_language
from django.shortcuts import redirect


def root_redirect(request):
    return redirect('dashboard:launcher' if request.user.is_authenticated else 'accounts:login')


urlpatterns = [
    path('',           root_redirect),
    path('admin/',     admin.site.urls),
    path('i18n/set/',  set_language, name='set_language'),   # til o'zgartirish
    path('accounts/',  include('notebook.accounts.urls')),
    path('business/',  include('notebook.business.urls', namespace='business')),
    path('clients/',   include('notebook.clients.urls')),
    path('products/',  include('notebook.catalog.urls')),
    path('company/',   include('notebook.company.urls', namespace='company')),
    path('dashboard/', include('notebook.dashboard.urls')),
    path('expenses/', include('notebook.expenses.urls', namespace='expenses')),
    path('containers/', include('notebook.containers.urls', namespace='containers')),
    path('sms/', include('notebook.sms.urls', namespace='sms')),
    path('inbox/', include('notebook.inbox.urls', namespace='inbox')),
]

handler403 = 'notebook.accounts.views.error_403'
handler404 = 'notebook.accounts.views.error_404'
handler413 = 'notebook.accounts.views.error_413'
handler500 = 'notebook.accounts.views.error_500'

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)