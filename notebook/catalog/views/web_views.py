# notebook/catalog/views/web_views.py
import os
from decimal import Decimal, InvalidOperation
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum, F, DecimalField, ExpressionWrapper
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import ListView, CreateView, TemplateView
from django.urls import reverse_lazy
from notebook.core.mixins import AdminRequiredMixin
from notebook.inventory.services import StockService
from notebook.inventory.models import StockBatch
from ..models import Product, Category
from ..forms import ProductForm, CategoryForm


class ProductListView(LoginRequiredMixin, ListView):
    model               = Product
    template_name       = 'inventory.html'
    context_object_name = 'products'
    paginate_by         = 20

    def get_queryset(self):
        qs = Product.objects.select_related('category').order_by('-created_at')
        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(slug__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = ProductForm()
        # Jami sotuv qiymati: price * stock — bitta aggregate query
        result = Product.objects.filter(stock__gt=0).aggregate(
            total_value=Sum(
                ExpressionWrapper(F('price') * F('stock'), output_field=DecimalField())
            )
        )
        ctx['total_inventory_value'] = result['total_value'] or 0

        # Jami tan narxi: StockBatch.remaining_quantity * cost_price
        # Bu FIFO bo'yicha eng to'g'ri hisob — har batch o'z narxida
        batch_result = StockBatch.objects.filter(
            is_active=True, remaining_quantity__gt=0
        ).aggregate(
            total_cost=Sum(
                ExpressionWrapper(
                    F('remaining_quantity') * F('cost_price'),
                    output_field=DecimalField()
                )
            )
        )
        ctx['total_inventory_cost_value'] = batch_result['total_cost'] or 0
        return ctx

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self._ajax_response()
        return super().get(request, *args, **kwargs)

    def _ajax_response(self):
        qs        = self.get_queryset()
        paginator = Paginator(qs, self.paginate_by)
        try:
            page_obj = paginator.page(self.request.GET.get('page', 1))
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.page(1)
        return JsonResponse({
            'products': [{'id': p.id, 'name': p.name, 'price': str(p.price),
                          'stock': p.stock, 'image': p.image.url if p.image else None}
                         for p in page_obj],
            'page': page_obj.number, 'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(), 'has_previous': page_obj.has_previous(),
            'total_count': paginator.count,
        })


class ProductCreateView(LoginRequiredMixin, CreateView):
    model      = Product
    form_class = ProductForm
    success_url = reverse_lazy('catalog:product_list')

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class ProductLauncherCreateView(LoginRequiredMixin, CreateView):
    model      = Product
    form_class = ProductForm

    def form_valid(self, form):
        p = form.save()
        return JsonResponse({'status': 'created', 'id': p.id, 'name': p.name, 'price': float(p.price)})

    def form_invalid(self, form):
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


class ProductUpdateView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            product = get_object_or_404(Product, id=request.POST.get('product_id'))
            product.name = request.POST.get('name', product.name)
            price = request.POST.get('price')
            if price:
                product.price = Decimal(price)
            if 'image' in request.FILES:
                if product.image and os.path.isfile(product.image.path):
                    os.remove(product.image.path)
                product.image = request.FILES['image']
            product.save()
            return JsonResponse({'status': 'updated', 'new_name': product.name,
                                 'new_price': str(product.price),
                                 'new_image_url': product.image.url if product.image else None})
        except (ValueError, InvalidOperation):
            return JsonResponse({'status': 'error', 'message': "Narx noto'g'ri formatda"}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class ProductDeleteView(LoginRequiredMixin, View):
    def post(self, request):
        product = get_object_or_404(Product.all_objects, pk=request.POST.get('product_id'))
        if product.is_active:
            product.is_active = False
            product.save(update_fields=['is_active'])
            return JsonResponse({'status': 'deleted'})
        return JsonResponse({'status': 'error', 'message': "Allaqachon o'chirilgan"}, status=400)


class AddStockView(LoginRequiredMixin, View):
    def post(self, request, product_id):
        try:
            product    = get_object_or_404(Product, id=product_id)
            quantity   = int(request.POST.get('quantity', 0))
            cost_price = Decimal(request.POST.get('cost_price', '0'))
            if quantity <= 0 or cost_price <= 0:
                return JsonResponse({'status': 'error', 'message': "Miqdor va narx musbat bo'lishi kerak!"}, status=400)
            StockService.add_stock(product=product, quantity=quantity, cost_price=cost_price, user=request.user)
            product.refresh_from_db()
            return JsonResponse({'status': 'success', 'new_stock': product.stock, 'product_id': product.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class ProductBatchView(LoginRequiredMixin, TemplateView):
    template_name = 'batch_page.html'

    def get_context_data(self, **kwargs):
        ctx     = super().get_context_data(**kwargs)
        product = get_object_or_404(Product, id=self.kwargs['product_id'])
        ctx.update({'product': product, 'batches': StockBatch.objects.filter(product=product).order_by('-created_at')})
        return ctx


class BatchAdjustmentsView(LoginRequiredMixin, View):
    def get(self, request, batch_id):
        batch       = get_object_or_404(StockBatch, id=batch_id)
        adjustments = batch.adjustments.select_related('user').order_by('-created_at')
        return JsonResponse({'status': 'success', 'adjustments': [
            {'adjustment_type': a.adjustment_type, 'quantity_change': a.quantity_change,
             'new_cost_price': float(a.new_cost_price) if a.new_cost_price else None,
             'reason': a.reason, 'created_at': a.created_at.strftime('%d.%m.%Y %H:%M')}
            for a in adjustments
        ]})


class BatchDeleteView(LoginRequiredMixin, View):
    def post(self, request, batch_id):
        batch = get_object_or_404(StockBatch, id=batch_id)
        try:
            batch.soft_delete()
            return JsonResponse({'status': 'success'})
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class CategorySaveView(LoginRequiredMixin, View):
    def post(self, request):
        category_id = request.POST.get('id')
        instance    = get_object_or_404(Category, pk=category_id) if category_id else None
        form        = CategoryForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save()
            return JsonResponse({'status': 'success', 'id': obj.id, 'name': obj.name})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


class CategoryDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        if category.products.exists():
            return JsonResponse({'status': 'error', 'message': "Bu kategoriya ishlatilgan!"}, status=400)
        category.is_active = False
        category.save(update_fields=['is_active'])
        return JsonResponse({'status': 'success'})