# notebook/clients/views/web_views.py
# O'zgarishlar:
#   1. ClientUpdateView — latitude/longitude qabul qiladi
#   2. SaleReceiptView  — chek ma'lumotlarini JSON qaytaradi

from notebook.catalog.models import Product, Category
from notebook.company.models import Branch
from notebook.clients.models import Client, Region
from notebook.sales.models import Sale, SaleItem, SaleReturn, SaleReturnItem
from notebook.payments.models import PaymentRefund
from notebook.clients.forms import ClientForm, RegionForm
from django.views.generic import ListView, CreateView, View, DetailView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum, Prefetch, F, ExpressionWrapper, DecimalField, OuterRef, Subquery, IntegerField
from django.contrib.auth.mixins import LoginRequiredMixin
from decimal import Decimal, InvalidOperation
from django.db.models.functions import Coalesce
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from notebook.business.mixins import BusinessRequiredMixin


class ClientListView(LoginRequiredMixin, BusinessRequiredMixin, ListView):
    model = Client
    template_name = "client.html"
    context_object_name = "clients"
    paginate_by = 100

    def get_queryset(self):
        from notebook.containers.models import ClientContainer
        # ── Har mijoz uchun umumiy idish sonini bitta Subquery bilan olamiz ──
        # (N+1 emas — barcha mijoz uchun bitta qo'shimcha SELECT)
        container_total_sq = ClientContainer.objects.filter(
            client=OuterRef('pk')
        ).values('client').annotate(
            total=Sum('quantity')
        ).values('total')

        qs = Client.objects.filter(business=self.request.business).select_related('region').annotate(
            container_total=Coalesce(
                Subquery(container_total_sq, output_field=IntegerField()), 0
            )
        ).order_by("-created_at")
        search    = self.request.GET.get("search", "").strip()
        region_id = self.request.GET.get("region", "").strip()
        balance   = self.request.GET.get("balance", "").strip()  # debt | advance | clear
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(phone__icontains=search))
        if region_id:
            qs = qs.filter(region_id=region_id)
        if balance == "debt":
            qs = qs.filter(total_debt__gt=0)
        elif balance == "advance":
            qs = qs.filter(advance_balance__gt=0)
        elif balance == "clear":
            qs = qs.filter(total_debt=0, advance_balance=0)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ClientForm()
        context['regions'] = Region.objects.filter(is_active=True, business=self.request.business)
        context['selected_region'] = self.request.GET.get("region", "")
        context['selected_balance'] = self.request.GET.get("balance", "")
        context['grand_total_containers'] = self.get_queryset().aggregate(
            total=Coalesce(Sum('container_total'), 0)
        )['total']
        return context

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.get_ajax_response()
        return super().get(request, *args, **kwargs)

    def get_ajax_response(self):
        queryset = self.get_queryset()

        # ── Barcha filterlangan clientlarning UMUMIY summasi — bitta query ──
        # Pagination bo'yicha emas, butun queryset bo'yicha hisoblanadi
        grand_totals = queryset.aggregate(
            grand_debt=Coalesce(Sum('total_debt'), Decimal('0')),
            grand_advance=Coalesce(Sum('advance_balance'), Decimal('0')),
            grand_containers=Coalesce(Sum('container_total'), 0),
        )

        paginator = Paginator(queryset, self.paginate_by)
        page_number = self.request.GET.get('page', 1)
        try:
            page_obj = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.page(1)

        clients_data = [
            {
                "id": c.id,
                "name": c.name,
                "phone": c.phone,
                "address": c.address or "",
                "region_id": c.region_id or "",
                "region_name": c.region.name if c.region else "",
                "total_debt": float(c.total_debt),
                "advance_balance": float(c.advance_balance),
                # ── Map koordinatalari ──────────────────────────────────────
                "latitude":  float(c.latitude)  if c.latitude  else None,
                "longitude": float(c.longitude) if c.longitude else None,
                "has_location": c.has_location,
                "container_total": c.container_total,
            }
            for c in page_obj
        ]
        return JsonResponse({
            "clients": clients_data,
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "total_count": paginator.count,
            # ── Barcha sahifalar bo'yicha UMUMIY yig'indi ──────────────────
            "grand_total_debt": float(grand_totals['grand_debt']),
            "grand_total_advance": float(grand_totals['grand_advance']),
            "grand_total_containers": int(grand_totals['grand_containers']),
            "selected_balance": self.request.GET.get("balance", ""),
        })


# ====================== CREATE ======================
class ClientCreateView(LoginRequiredMixin, BusinessRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm

    def form_valid(self, form):
        form.instance.business = self.request.business
        form.save()
        return JsonResponse({"status": "created"})

    def form_invalid(self, form):
        return JsonResponse({
            "status": "error",
            "message": "Formada xatolik bor",
            "errors": form.errors
        }, status=400)


# ====================== UPDATE ======================
class ClientUpdateView(LoginRequiredMixin, BusinessRequiredMixin, View):
    def post(self, request):
        client_id = request.POST.get("client_id")
        try:
            client = Client.all_objects.get(id=client_id, business=request.business)
        except Client.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Client topilmadi"}, status=404)

        client.name    = request.POST.get("name", client.name).strip()
        client.phone   = request.POST.get("phone", client.phone).strip()
        client.address = request.POST.get("address", client.address).strip()

        region_id = request.POST.get("region_id")
        if region_id:
            client.region_id = int(region_id)
        elif region_id == "":
            client.region = None

        # ── Koordinatalarni saqlash ─────────────────────────────────────────
        lat_str = request.POST.get("latitude", "").strip()
        lng_str = request.POST.get("longitude", "").strip()

        if lat_str and lng_str:
            try:
                client.latitude  = Decimal(lat_str)
                client.longitude = Decimal(lng_str)
            except InvalidOperation:
                return JsonResponse({"status": "error", "message": "Koordinata noto'g'ri"}, status=400)
        elif lat_str == "" and lng_str == "":
            # Ikkala maydon bo'sh — o'chirish
            client.latitude  = None
            client.longitude = None

        client.save()
        return JsonResponse({
            "status": "updated",
            "region_name": client.region.name if client.region else "",
            "has_location": client.has_location,
            "latitude":  float(client.latitude)  if client.latitude  else None,
            "longitude": float(client.longitude) if client.longitude else None,
        })


# ====================== DELETE ======================
class ClientDeleteView(LoginRequiredMixin, BusinessRequiredMixin, View):
    def post(self, request):
        client_id = request.POST.get("client_id")
        client = get_object_or_404(Client.all_objects, pk=client_id, business=request.business)
        if client.is_active:
            client.is_active = False
            client.save(update_fields=['is_active'])
            return JsonResponse({"status": "deleted", "message": "Mijoz soft delete qilindi"})
        else:
            return JsonResponse({"status": "error", "message": "Mijoz allaqachon o'chirilgan"}, status=400)


# ====================== DETAIL ======================
class ClientDetailView(LoginRequiredMixin, BusinessRequiredMixin, DetailView):
    model = Client
    template_name = "client_detail.html"
    context_object_name = "client"

    def get_queryset(self):
        return Client.objects.filter(business=self.request.business).select_related('region')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.object

        sales = client.sales.filter(
            status=Sale.STATUS_ACTIVE
        ).prefetch_related(
            Prefetch('items', queryset=SaleItem.objects.select_related('product'))
        ).order_by('-created_at')[:30]

        sale_returns = SaleReturn.objects.filter(
            sale__client=client
        ).prefetch_related(
            Prefetch('items', queryset=SaleReturnItem.objects.select_related('sale_item__product'))
        ).select_related('sale').order_by('-created_at')[:30]

        payments_qs = client.payments.filter(is_cancelled=False)
        payments = list(payments_qs.order_by('-created_at')[:30])

        payment_refunds = PaymentRefund.objects.filter(
            payment__client=client
        ).select_related('payment').order_by('-created_at')[:30]

        total_sold = SaleItem.objects.filter(
            sale__client=client, sale__status=Sale.STATUS_ACTIVE
        ).aggregate(
            total=Coalesce(
                Sum(ExpressionWrapper(
                    (F('quantity') - F('returned_quantity')) * F('price_at_sale'),
                    output_field=DecimalField()
                )),
                Decimal('0')
            )
        )['total']

        total_paid = payments_qs.aggregate(
            total=Coalesce(
                Sum(F('amount') - F('refunded_amount'), output_field=DecimalField()),
                Decimal('0')
            )
        )['total']

        history = []

        for sale in sales:
            items_list = sale.items.all()
            serialized_items = []
            for item in items_list:
                serialized_items.append({
                    'id': item.id,
                    'product': {'name': item.product.name},
                    'quantity': str(item.quantity),
                    'unit_label': item.product.get_unit_type_display(),
                    'returned_quantity': str(item.returned_quantity),
                    'remaining': str(item.get_remaining_quantity()),
                    'price_at_sale': float(item.price_at_sale),
                    'subtotal': float(item.price_at_sale * item.quantity),
                    'returned_subtotal': float(item.price_at_sale * item.returned_quantity),
                })
            # Dona va kg ni qo'shib bo'lmaydi — mahsulot TURLARI sonini ko'rsatamiz
            product_types_count = len(serialized_items)
            history.append({
                'date': sale.created_at,
                'type': 'sale',
                'display_type': 'Sotuv',
                'badge': 'Qarz',
                'badge_color': 'bg-danger',
                'amount': float(sale.total_amount),
                'is_positive': False,
                'details': f"{product_types_count} xil mahsulot",
                'items': serialized_items,
                'serialized_items': serialized_items,
                'sale_id': sale.id,
            })

        for sale_return in sale_returns:
            returned_items = sale_return.items.all()
            total_returned = 0
            serialized_return_items = []
            for i in returned_items:
                subtotal = i.returned_quantity * i.sale_item.price_at_sale
                total_returned += subtotal
                serialized_return_items.append({
                    'product_name': i.sale_item.product.name,
                    'quantity': i.returned_quantity,
                    'price': float(i.sale_item.price_at_sale),
                    'subtotal': float(subtotal),
                })
            history.append({
                'date': sale_return.created_at,
                'type': 'sale_return',
                'display_type': 'Qaytarish',
                'badge': 'Qaytarildi',
                'badge_color': 'bg-warning text-dark',
                'amount': float(total_returned),
                'is_positive': True,
                'details': sale_return.reason or f"Sotuv #{sale_return.sale.id} dan",
                'items': serialized_return_items,
                'return_id': sale_return.id,
                'sale_id': sale_return.sale.id,
            })

        for payment in payments:
            history.append({
                'date': payment.created_at,
                'type': 'payment',
                'display_type': "To'lov",
                'badge': "To'langan",
                'badge_color': 'bg-success',
                'amount': float(payment.amount),
                'is_positive': True,
                'details': payment.note or 'Izohsiz',
                'payment_id': payment.id,
                'note': payment.note or '',
                'refunded_amount': float(payment.refunded_amount),
                'remaining_amount': float(payment.get_remaining_amount()),
                'is_fully_refunded': payment.is_fully_refunded(),
            })

        for refund in payment_refunds:
            history.append({
                'date': refund.created_at,
                'type': 'payment_refund',
                'display_type': "To'lov qaytarildi",
                'badge': 'Refund',
                'badge_color': 'bg-warning text-dark',
                'amount': float(refund.amount),
                'is_positive': False,
                'details': refund.reason or f"To'lov #{refund.payment.id} dan",
                'refund_id': refund.id,
                'payment_id': refund.payment.id,
                'reason': refund.reason or '',
            })

        history.sort(key=lambda x: x['date'], reverse=True)

        paginator = Paginator(history, 15)
        page_number = self.request.GET.get('history_page', 1)
        page_obj = paginator.get_page(page_number)

        context.update({
            'history': page_obj.object_list,
            'history_page_obj': page_obj,
            'sales': sales,
            'payments': payments,
            'total_sold': total_sold,
            'total_paid': total_paid,
            'calculated_debt': client.total_debt,
            'products': Product.objects.filter(stock__gt=0, business=self.request.business).only('id', 'name', 'stock').order_by('name'),
            'categories': Category.objects.filter(is_active=True, business=self.request.business).only('id', 'name').order_by('name'),
            'branches': Branch.objects.filter(is_active=True, company__business=self.request.business).only('id', 'name').order_by('name'),
            # ── Map ─────────────────────────────────────────────────────────
            'google_maps_api_key': '',   # settings.GOOGLE_MAPS_API_KEY
        })
        return context


# ====================== RECEIPT VIEW ======================
# Sotuv chekini JSON formatda qaytaradi.
# Frontend (receipt.js) bu ma'lumotni oladi:
#   — Browser print (CSS @media print) uchun HTML modal
#   — Web Bluetooth API + ESC/POS uchun raw bytes
@method_decorator(login_required, name='dispatch')
class SaleReceiptView(BusinessRequiredMixin, View):
    def get(self, request, sale_id):
        sale = get_object_or_404(
            Sale.objects.select_related('client', 'user')
                        .prefetch_related('items__product'),
            id=sale_id, business=request.business
        )

        items = []
        for item in sale.items.all():
            items.append({
                'name':       item.product.name,
                'qty':        str(item.quantity),
                'unit_label': item.product.get_unit_type_display(),
                'price':      float(item.price_at_sale),
                'subtotal':   float(item.price_at_sale * item.quantity),
            })

        receipt_data = {
            'sale_id':     sale.id,
            'client_name': sale.client.name,
            'client_phone': sale.client.phone,
            'cashier':     sale.user.get_full_name() if sale.user else '—',
            'date':        sale.created_at.strftime('%d.%m.%Y %H:%M'),
            'items':       items,
            'total':       float(sale.total_amount),
            'debt':        float(sale.client.total_debt),
            'advance':     float(sale.client.advance_balance),
        }
        return JsonResponse({'status': 'success', 'receipt': receipt_data})


# ====================== REGION ======================
class RegionSaveView(LoginRequiredMixin, BusinessRequiredMixin, View):
    def post(self, request):
        region_id = request.POST.get("id")
        region = get_object_or_404(Region, pk=region_id, business=request.business) if region_id else None
        form = RegionForm(request.POST, instance=region)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.business = request.business
            obj.save()
            return JsonResponse({"status": "success", "id": obj.id, "name": obj.name, "order": obj.order})
        return JsonResponse({"status": "error", "errors": form.errors}, status=400)


class RegionDeleteView(LoginRequiredMixin, BusinessRequiredMixin, View):
    def post(self, request, pk):
        region = get_object_or_404(Region, pk=pk, business=request.business)
        if region.clients.exists():
            return JsonResponse({"status": "error", "message": "Bu region ishlatilgan!"}, status=400)
        region.is_active = False
        region.save(update_fields=["is_active"])
        return JsonResponse({"status": "success"})