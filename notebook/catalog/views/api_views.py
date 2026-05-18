# notebook/catalog/views/api_views.py
import json
import logging
from decimal import Decimal
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from notebook.catalog.models import Product
from notebook.clients.models import Client
from notebook.sales.models import Sale
from notebook.inventory.models import StockBatch
from notebook.inventory.services import StockService
from notebook.sales.services import SaleService
from notebook.payments.services import PaymentService

logger = logging.getLogger(__name__)


class ProductModalListView(View):
    def get(self, request):
        products = Product.objects.filter(stock__gt=0, is_active=True).order_by('name')
        return JsonResponse({'products': list(products.values('id', 'name', 'price', 'stock'))})


class FilteredProductsView(View):
    def get(self, request):
        qs = Product.objects.filter(stock__gt=0).select_related('category').order_by('name')
        query       = request.GET.get('search', '').strip()
        category_id = request.GET.get('category')
        if query:       qs = qs.filter(name__icontains=query)
        if category_id: qs = qs.filter(category_id=category_id)
        paginator = Paginator(qs, 10)
        page_obj  = paginator.get_page(request.GET.get('page', 1))
        return JsonResponse({
            'products': [{'id': p.id, 'name': p.name, 'price': str(p.price), 'stock': p.stock}
                         for p in page_obj],
            'has_next': page_obj.has_next(), 'has_previous': page_obj.has_previous(),
            'current_page': page_obj.number, 'total_pages': paginator.num_pages,
            'total_count': paginator.count,
        })


class AddToCartView(View):
    def post(self, request, client_id):
        try:
            data       = json.loads(request.body or '{}')
            product_id = data.get('product_id')
            quantity   = int(data.get('quantity', 1))
            if not product_id or quantity <= 0:
                return JsonResponse({'status': 'error', 'message': "product_id va miqdor kerak"}, status=400)
            product  = get_object_or_404(Product, id=product_id, is_active=True)
            cart_key = f'cart_client_{client_id}'
            cart     = request.session.get(cart_key, [])
            cart_dict = {item['product_id']: item for item in cart}
            if product_id in cart_dict:
                new_qty = cart_dict[product_id]['quantity'] + quantity
                if product.stock < new_qty:
                    return JsonResponse({'status': 'error', 'message': 'Yetarli stock mavjud emas'}, status=400)
                cart_dict[product_id]['quantity'] = new_qty
            else:
                if product.stock < quantity:
                    return JsonResponse({'status': 'error', 'message': 'Yetarli stock mavjud emas'}, status=400)
                cart_dict[product_id] = {'product_id': product.id, 'name': product.name,
                                         'price': str(product.price), 'quantity': quantity}
            request.session[cart_key] = list(cart_dict.values())
            request.session.modified  = True
            return JsonResponse({'status': 'success',
                                 'cart_count': sum(i['quantity'] for i in cart_dict.values())})
        except Exception as e:
            logger.error(f"AddToCart error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Server xatoligi'}, status=500)


class GetCartView(View):
    def get(self, request, client_id):
        cart  = request.session.get(f'cart_client_{client_id}', [])
        total = sum(Decimal(i['price']) * i['quantity'] for i in cart)
        return JsonResponse({'status': 'success', 'cart': cart, 'total': float(total),
                             'item_count': sum(i['quantity'] for i in cart)})


class ClearCartView(View):
    def post(self, request, client_id):
        request.session[f'cart_client_{client_id}'] = []
        request.session.modified = True
        return JsonResponse({'status': 'success'})


class CreateSaleView(View):
    def post(self, request, client_id):
        try:
            client   = get_object_or_404(Client, id=client_id)
            cart_key = f'cart_client_{client_id}'
            cart     = request.session.get(cart_key, [])
            if not cart:
                return JsonResponse({'status': 'error', 'message': "Savatcha bo'sh"}, status=400)
            sale = SaleService.create_sale_from_cart(
                client=client,
                cart_items=[{'product_id': i['product_id'], 'quantity': i['quantity']} for i in cart],
                user=request.user,
            )
            request.session[cart_key] = []
            request.session.modified  = True
            return JsonResponse({'status': 'success', 'sale_id': sale.id,
                                 'total_amount': float(sale.total_amount)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class CreatePaymentView(View):
    def post(self, request, client_id):
        try:
            client = get_object_or_404(Client, id=client_id)
            data   = json.loads(request.body)
            PaymentService.create_payment(
                client=client, amount=Decimal(data.get('amount', '0')),
                user=request.user, note=data.get('note', '')
            )
            client.refresh_from_db()
            return JsonResponse({'status': 'success',
                                 'total_debt': float(client.total_debt),
                                 'advance_balance': float(client.advance_balance)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class PaymentRefundView(LoginRequiredMixin, View):
    def post(self, request, payment_id):
        try:
            from notebook.payments.models import Payment
            payment = get_object_or_404(Payment.objects.select_related('client'), id=payment_id)
            if payment.is_cancelled:
                return JsonResponse({'status': 'error', 'message': "Bekor qilingan to'lovni qaytarib bo'lmaydi"}, status=400)
            if payment.get_remaining_amount() <= 0:
                return JsonResponse({'status': 'error', 'message': "Allaqachon to'liq qaytarilgan"}, status=400)
            data = json.loads(request.body)
            PaymentService.refund_payment(
                payment=payment, amount=Decimal(str(data.get('amount', 0))),
                user=request.user, reason=data.get('reason', '')
            )
            return JsonResponse({'status': 'success', 'remaining': float(payment.get_remaining_amount())})
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class StockAdjustmentView(View):
    def post(self, request, batch_id):
        try:
            batch = get_object_or_404(StockBatch, id=batch_id)
            if batch.remaining_quantity != batch.quantity_received:
                return JsonResponse({'status': 'error', 'message': "Sarflangan batchni o'zgartirib bo'lmaydi"}, status=400)
            quantity_change = int(request.POST.get('quantity_change', 0))
            new_cost_price  = request.POST.get('new_cost_price', '').strip()
            reason          = request.POST.get('reason', '').strip()
            if not reason:
                return JsonResponse({'status': 'error', 'message': 'Sabab kiritish majburiy'}, status=400)
            new_cost_price = Decimal(new_cost_price) if new_cost_price else None
            adj = StockService.adjust_stock(batch=batch, quantity_change=quantity_change,
                                            new_cost_price=new_cost_price, user=request.user, reason=reason)
            batch.refresh_from_db(); batch.product.refresh_from_db()
            return JsonResponse({'status': 'success', 'adjustment_id': adj.id,
                                 'new_remaining': batch.remaining_quantity, 'new_stock': batch.product.stock})
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class SaleReturnView(View):
    def post(self, request, sale_id):
        try:
            sale = get_object_or_404(
                Sale.objects.select_related('client').prefetch_related('items'),
                id=sale_id
            )
            if sale.status == Sale.STATUS_CANCELLED:
                return JsonResponse({'status': 'error', 'message': "Bekor qilingan sotuvni qaytarib bo'lmaydi"}, status=400)
            data = json.loads(request.body)
            if data.get('full_return'):
                # items prefetch_related orqali allaqachon yuklangan — DB ga qayta bormaymiz
                return_data = [
                    {'sale_item_id': i.id, 'quantity': i.get_remaining_quantity()}
                    for i in sale.items.all() if i.get_remaining_quantity() > 0
                ]
            else:
                return_data = data.get('items', [])
            sale_return = SaleService.process_return(sale=sale, return_data=return_data,
                                                     user=request.user, reason=data.get('reason', ''))
            return JsonResponse({'status': 'success', 'return_id': sale_return.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class SaleCancelView(View):
    def post(self, request, sale_id):
        try:
            sale = get_object_or_404(
                Sale.objects.select_related('client').prefetch_related('items'),
                id=sale_id
            )
            if sale.status == Sale.STATUS_CANCELLED:
                return JsonResponse({'status': 'error', 'message': "Allaqachon bekor qilingan"}, status=400)
            sale.full_cancel(cancelled_by=request.user)
            return JsonResponse({'status': 'success', 'sale_id': sale.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)