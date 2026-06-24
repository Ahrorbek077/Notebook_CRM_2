# notebook/business/views.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.decorators import method_decorator
from django.views import View

from notebook.accounts.decorators import superadmin_required
from .models import Business
from .forms import BusinessForm


@method_decorator(superadmin_required, name='dispatch')
class BusinessListView(View):
    """Superadmin uchun — barcha bizneslar ro'yxati (aka/ukalar)."""
    def get(self, request):
        businesses = Business.objects.filter(is_active=True).order_by('name')
        return render(request, 'business/business_list.html', {
            'businesses': businesses,
            'form': BusinessForm(),
        })


@method_decorator(superadmin_required, name='dispatch')
class BusinessCreateView(View):
    def post(self, request):
        form = BusinessForm(request.POST)
        if form.is_valid():
            biz = form.save(commit=False)
            biz.owner = request.user if not request.POST.get('owner_id') else None
            biz.save()
            return JsonResponse({'status': 'created', 'id': biz.id, 'name': biz.name})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


@method_decorator(superadmin_required, name='dispatch')
class BusinessDeleteView(View):
    def post(self, request, pk):
        biz = get_object_or_404(Business, pk=pk)
        biz.is_active = False
        biz.save(update_fields=['is_active'])
        return JsonResponse({'status': 'deleted'})


@method_decorator(superadmin_required, name='dispatch')
class BusinessSwitchView(View):
    """Superadmin joriy ko'rib turgan biznesni almashtiradi (session orqali).

    Admin/staff uchun bu endpoint ishlamaydi — ular doim o'z biznesida qoladi
    (superadmin_required shartining o'zi buni ta'minlaydi).
    """
    def post(self, request):
        biz_id = request.POST.get('business_id')
        business = get_object_or_404(Business, pk=biz_id, is_active=True)
        request.session['active_business_id'] = business.id
        return JsonResponse({'status': 'switched', 'business_id': business.id, 'name': business.name})
