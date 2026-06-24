# notebook/dashboard/views/web_views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from notebook.core.mixins import AdminRequiredMixin
from notebook.business.mixins import BusinessRequiredMixin
from notebook.activity.models import ActivityLog

SALE_ACTION_TYPES  = ['sale','sale_return','payment','payment_refund','client_create','client_update','client_delete',
                      'container_given','container_returned']
STOCK_ACTION_TYPES = ['company_create','company_update','company_delete','branch_create','branch_update',
                      'branch_delete','branch_payment','product_create','product_update','product_delete',
                      'stock_add','stock_adjust','stock_delete','stock_return','container_stock_add']

ACTION_CLASS_MAP = {
    'sale':('badge-sale','fa-shopping-cart'), 'sale_return':('badge-return','fa-undo'),
    'payment':('badge-payment','fa-credit-card'), 'payment_refund':('badge-refund','fa-undo-alt'),
    'client_create':('badge-create','fa-user-plus'), 'client_update':('badge-update','fa-user-edit'),
    'client_delete':('badge-delete','fa-user-times'),
    'company_create':('badge-create','fa-building'), 'company_update':('badge-update','fa-building'),
    'company_delete':('badge-delete','fa-building'), 'branch_create':('badge-create','fa-store'),
    'branch_update':('badge-update','fa-store'), 'branch_delete':('badge-delete','fa-store'),
    'branch_payment':('badge-payment','fa-hand-holding-usd'),
    'product_create':('badge-create','fa-plus'), 'product_update':('badge-update','fa-edit'),
    'product_delete':('badge-delete','fa-trash'), 'stock_add':('badge-stock','fa-boxes'),
    'stock_adjust':('badge-adjust','fa-sliders-h'), 'stock_delete':('badge-delete','fa-trash'),
    'stock_return':('badge-return','fa-undo-alt'),
    'container_given':('badge-payment','fa-box-open'), 'container_returned':('badge-return','fa-box'),
    'container_stock_add':('badge-stock','fa-boxes-stacked'),
}


class LauncherView(LoginRequiredMixin, BusinessRequiredMixin, TemplateView):
    template_name = 'launcher.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from notebook.clients.models import Region
        from notebook.catalog.models import Category
        ctx['regions']    = Region.objects.filter(business=self.request.business)
        ctx['categories'] = Category.objects.filter(business=self.request.business).order_by('name')
        return ctx


class DashboardView(AdminRequiredMixin, LoginRequiredMixin, BusinessRequiredMixin, TemplateView):
    template_name = 'dashboard.html'


class BaseHistoryView(AdminRequiredMixin, LoginRequiredMixin, BusinessRequiredMixin, ListView):
    model               = ActivityLog
    context_object_name = 'logs'
    paginate_by         = 30
    action_type_filter  = []

    def get_queryset(self):
        qs = ActivityLog.objects.select_related('user')\
               .filter(action_type__in=self.action_type_filter, business=self.request.business)\
               .order_by('-created_at')
        search = self.request.GET.get('search', '').strip()
        at     = self.request.GET.get('action_type', '').strip()
        df     = self.request.GET.get('date_from', '').strip()
        dt     = self.request.GET.get('date_to', '').strip()
        if search: qs = qs.filter(Q(description__icontains=search)|Q(user__username__icontains=search))
        if at and at in self.action_type_filter: qs = qs.filter(action_type=at)
        if df: qs = qs.filter(created_at__date__gte=df)
        if dt: qs = qs.filter(created_at__date__lte=dt)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_choices'] = [(k,v) for k,v in ActivityLog.ACTION_CHOICES if k in self.action_type_filter]
        ctx['selected_type']  = self.request.GET.get('action_type', '')
        return ctx

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self._ajax()
        return super().get(request, *args, **kwargs)

    def _ajax(self):
        qs        = self.get_queryset()
        paginator = Paginator(qs, self.paginate_by)
        try:    page_obj = paginator.page(self.request.GET.get('page', 1))
        except: page_obj = paginator.page(1)
        logs = []
        for log in page_obj:
            cls, icon = ACTION_CLASS_MAP.get(log.action_type, ('badge-secondary','fa-circle'))
            logs.append({'id': log.id, 'created_at': log.created_at.strftime('%d.%m.%Y %H:%M'),
                         'user': log.user.username if log.user else 'Tizim',
                         'action_type': log.action_type, 'action_label': log.get_action_type_display(),
                         'action_class': cls, 'action_icon': icon,
                         'description': log.description, 'extra_data': log.extra_data or {}})
        counts = {r['action_type']: r['c'] for r in
                  ActivityLog.objects.filter(action_type__in=self.action_type_filter, business=self.request.business)
                                     .values('action_type').annotate(c=Count('id'))}
        return JsonResponse({'logs': logs, 'page': page_obj.number,
                             'total_pages': paginator.num_pages, 'has_next': page_obj.has_next(),
                             'has_previous': page_obj.has_previous(),
                             'total_count': paginator.count, 'counts': counts})


class SaleHistoryView(BaseHistoryView):
    template_name      = 'history_sale.html'
    action_type_filter = SALE_ACTION_TYPES


class StockHistoryView(BaseHistoryView):
    template_name      = 'history_stock.html'
    action_type_filter = STOCK_ACTION_TYPES