"""
Company views — Kompaniya, Filial va Filial mahsulotlari boshqaruvi.
"""
import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, OuterRef, Subquery, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from django.db.models import Sum, Q as dQ
from .models import Company, Branch, BranchPayment
from .services import CompanyService
from notebook.catalog.models import Product, Category
from notebook.catalog.forms import ProductForm
from notebook.inventory.models import StockBatch
from notebook.inventory.services import StockService
from notebook.activity.models import ActivityLog
from notebook.business.mixins import BusinessRequiredMixin


# ─── Web sahifalar ────────────────────────────────────────────────────────────

class CompanyListView(LoginRequiredMixin, BusinessRequiredMixin, View):
    def get(self, request):
        companies = Company.objects.filter(business=request.business).prefetch_related('branches').order_by('name')
        return render(request, 'company/company_list.html', {'companies': companies})


class BranchDetailView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Filial sahifasi — filial mahsulotlari, sotib olish, CRUD."""
    def get(self, request, pk):
        branch   = get_object_or_404(Branch, pk=pk, is_active=True, company__business=request.business)
        search   = request.GET.get('search', '').strip()
        page_num = request.GET.get('page', 1)

        # ── latest_cost_price N+1 ni Subquery bilan hal qilamiz ──────────
        # Har product uchun alohida query o'rniga bitta LEFT JOIN
        from notebook.inventory.models import StockBatch
        latest_batch_cost = StockBatch.objects.filter(
            product=OuterRef('pk'), is_active=True
        ).order_by('-created_at').values('cost_price')[:1]

        qs = Product.objects.filter(
            branch=branch, is_active=True, business=request.business
        ).select_related('category').annotate(
            annotated_cost_price=Coalesce(
                Subquery(latest_batch_cost, output_field=DecimalField()),
                'default_cost_price',
                output_field=DecimalField()
            )
        ).order_by('-created_at')

        if search:
            qs = qs.filter(Q(name__icontains=search))

        paginator = Paginator(qs, 20)
        try:
            page_obj = paginator.page(page_num)
        except (EmptyPage, PageNotAnInteger):
            page_obj = paginator.page(1)

        categories = Category.objects.filter(is_active=True, business=request.business)

        # To'lovlar statistikasi — bitta aggregate query
        pay_agg = BranchPayment.objects.filter(branch=branch).aggregate(
            total_cash=Sum('amount', filter=dQ(payment_type='cash')),
            total_transfer=Sum('amount', filter=dQ(payment_type='transfer')),
            total_discount=Sum('amount', filter=dQ(payment_type='discount')),
        )
        # So'nggi 10 ta to'lov tarixi (AJAX load more bilan davom etadi)
        recent_payments = BranchPayment.objects.filter(branch=branch).select_related('user').order_by('-created_at')[:10]

        return render(request, 'company/branch_detail.html', {
            'branch':          branch,
            'company':         branch.company,
            'page_obj':        page_obj,
            'products':        page_obj.object_list,
            'categories':      categories,
            'search':          search,
            'pay_cash':        pay_agg['total_cash']     or 0,
            'pay_transfer':    pay_agg['total_transfer'] or 0,
            'pay_discount':    pay_agg['total_discount'] or 0,
            'recent_payments': recent_payments,
        })


# ─── Company AJAX ─────────────────────────────────────────────────────────────

class CompanyCreateView(LoginRequiredMixin, BusinessRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            if not name:
                return JsonResponse({'status': 'error', 'message': 'Nomi kiritilmagan'}, status=400)
            company = CompanyService.create_company(
                name=name, business=request.business, phone=data.get('phone', ''),
                address=data.get('address', ''), note=data.get('note', ''),
                user=request.user,
            )
            return JsonResponse({'status': 'success', 'company': {'id': company.id, 'name': company.name}})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class CompanyEditView(LoginRequiredMixin, BusinessRequiredMixin, View):
    def post(self, request, pk):
        try:
            company = get_object_or_404(Company, pk=pk, is_active=True, business=request.business)
            data    = json.loads(request.body)
            fields  = {k: v for k, v in data.items() if k in ('name', 'phone', 'address', 'note')}
            CompanyService.update_company(company, fields, user=request.user)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class CompanyDeleteView(LoginRequiredMixin, BusinessRequiredMixin, View):
    def post(self, request, pk):
        try:
            company = get_object_or_404(Company, pk=pk, is_active=True, business=request.business)
            CompanyService.delete_company(company, user=request.user)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ─── Branch AJAX ──────────────────────────────────────────────────────────────

class BranchCreateView(LoginRequiredMixin, BusinessRequiredMixin, View):
    def post(self, request):
        try:
            data       = json.loads(request.body)
            company_id = data.get('company_id')
            name       = data.get('name', '').strip()
            if not company_id or not name:
                return JsonResponse({'status': 'error', 'message': "company_id va name kerak"}, status=400)
            company = get_object_or_404(Company, pk=company_id, is_active=True, business=request.business)
            branch  = CompanyService.create_branch(
                company=company, name=name,
                phone=data.get('phone', ''), address=data.get('address', ''),
                note=data.get('note', ''), user=request.user,
            )
            return JsonResponse({'status': 'success', 'branch': {
                'id': branch.id, 'name': branch.name,
                'company_id': company.id, 'company_name': company.name,
                'url': f'/company/branch/{branch.id}/',
            }})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class BranchEditView(LoginRequiredMixin, BusinessRequiredMixin, View):
    def post(self, request, pk):
        try:
            branch = get_object_or_404(Branch, pk=pk, is_active=True, company__business=request.business)
            data   = json.loads(request.body)
            fields = {k: v for k, v in data.items() if k in ('name', 'phone', 'address', 'note')}
            CompanyService.update_branch(branch, fields, user=request.user)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class BranchDeleteView(LoginRequiredMixin, BusinessRequiredMixin, View):
    def post(self, request, pk):
        try:
            branch = get_object_or_404(Branch, pk=pk, is_active=True, company__business=request.business)
            CompanyService.delete_branch(branch, user=request.user)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class BranchPayView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Biz filialga to'laymiz."""
    def post(self, request, pk):
        try:
            branch = get_object_or_404(Branch, pk=pk, is_active=True, company__business=request.business)
            data   = json.loads(request.body)
            amount = Decimal(str(data.get('amount', 0)))
            bp = CompanyService.pay_to_branch(
                branch=branch, amount=amount,
                payment_type=data.get('payment_type', 'cash'),
                discount_percent=Decimal(str(data.get('discount_percent', 0))),
                due_date=data.get('due_date') or None,
                note=data.get('note', ''), user=request.user,
            )
            # pay_to_branch() ichida branch.save() bo'ldi —
            # ortiqcha Branch.objects.get() o'rniga branchni refresh qilamiz
            branch.refresh_from_db(fields=['total_debt', 'advance_balance'])
            return JsonResponse({
                'status':      'success',
                'new_debt':    str(branch.total_debt),
                'new_advance': str(branch.advance_balance),
            })
        except (InvalidOperation, ValueError) as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ─── Branch Product CRUD ──────────────────────────────────────────────────────

class BranchProductCreateView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Filialga yangi mahsulot qo'shish.
    
    Faqat mahsulot katalogga qo'shiladi — stock 0 qoladi.
    Stock keyinchalik 'Sotib olish' tugmasi orqali to'ldiriladi.
    Tan narxi esa 'Sotib olish' modal da kiritiladi (default_cost_price sifatida saqlanadi).
    """
    def post(self, request, branch_pk):
        try:
            branch = get_object_or_404(Branch, pk=branch_pk, is_active=True, company__business=request.business)
            form   = ProductForm(request.POST, request.FILES, business=request.business)
            if form.is_valid():
                # ── Tan narxini validatsiya (stock uchun default) ──────────
                cost_price_str = request.POST.get('cost_price', '').strip()
                try:
                    cost_price = Decimal(cost_price_str)
                    if cost_price <= 0:
                        raise ValueError
                except (InvalidOperation, ValueError):
                    return JsonResponse({'status': 'error', 'message': "Tan narxi to'g'ri kiritilmagan"}, status=400)

                # ── Karobka validatsiyasi ──────────────────────────────────
                is_box_enabled = request.POST.get('is_box_enabled') == 'true'
                if is_box_enabled:
                    try:
                        units_per_box = Decimal(request.POST.get('units_per_box', '0'))
                        if units_per_box <= 0:
                            raise ValueError
                    except (InvalidOperation, ValueError):
                        return JsonResponse({'status': 'error', 'message': "Karobka yoqilgan bo'lsa, 1 karobkadagi miqdorni to'g'ri kiriting"}, status=400)
                else:
                    units_per_box = None

                product = form.save(commit=False)
                product.branch           = branch
                product.business         = request.business
                product.created_by       = request.user
                product.default_cost_price = cost_price   # yangi maydon
                product.is_box_enabled   = is_box_enabled
                product.units_per_box    = units_per_box
                product.save()
                # ── Stock qo'shilmaydi — faqat katalogga qo'shildi ────────

                ActivityLog.objects.create(
                    user=request.user, business=request.business, action_type='product_create',
                    description=f"Mahsulot katalogga qo'shildi: {product.name} ({product.get_unit_type_display()}), tan narxi: {cost_price:,.0f} so'm (filial: {branch.name})",
                    extra_data={'product_id': product.id, 'name': product.name, 'branch_id': branch.id,
                                'cost_price': str(cost_price), 'unit_type': product.unit_type,
                                'unit_label': product.get_unit_type_display()}
                )
                return JsonResponse({
                    'status': 'success',
                    'product': {
                        'id': product.id, 'name': product.name,
                        'price': str(product.price), 'stock': str(product.stock),
                        'cost_price': str(cost_price),
                        'unit_type': product.unit_type,
                        'unit_label': product.get_unit_type_display(),
                        'is_box_enabled': product.is_box_enabled,
                        'units_per_box': str(product.units_per_box) if product.units_per_box else None,
                        'category': product.category.name,
                        'image': product.image.url if product.image else None,
                    }
                })
            errors = {k: v[0] for k, v in form.errors.items()}
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class BranchProductUpdateView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Filial mahsulotini yangilash."""
    def post(self, request, pk):
        import os
        from decimal import InvalidOperation as DIE
        try:
            product = get_object_or_404(Product, pk=pk, is_active=True, business=request.business)
            name       = request.POST.get('name', '').strip()
            price      = request.POST.get('price', '')
            cat        = request.POST.get('category', '')
            cost_price = request.POST.get('cost_price', '').strip()

            if name:  product.name = name
            if price:
                product.price = Decimal(price)
            if cat:
                product.category_id = int(cat)
            if 'image' in request.FILES:
                if product.image and os.path.isfile(product.image.path):
                    os.remove(product.image.path)
                product.image = request.FILES['image']
            product.save()

            # ── Tan narxini yangilash ──────────────────────────────────────
            # MUHIM: Faqat default_cost_price o'zgaradi — keyingi xarid uchun.
            # Mavjud batchlar o'ZGARMAYDI — ular tarixiy sotib olish narxi.
            new_cost = None
            if cost_price:
                try:
                    new_cost = Decimal(cost_price)
                    if new_cost > 0:
                        product.default_cost_price = new_cost
                        product.save(update_fields=['default_cost_price'])
                except InvalidOperation:
                    pass

            ActivityLog.objects.create(
                user=request.user, business=request.business, action_type='product_update',
                description=f"Mahsulot yangilandi: {product.name}" + (f", tan narxi: {new_cost:,.0f} so'm" if new_cost else ""),
                extra_data={'product_id': product.id, 'name': product.name,
                            'new_cost_price': str(new_cost) if new_cost else None}
            )
            return JsonResponse({
                'status': 'success',
                'product': {
                    'id': product.id, 'name': product.name,
                    'price': str(product.price),
                    'cost_price': str(new_cost) if new_cost else str(product.latest_cost_price),
                    'category': product.category.name,
                    'image': product.image.url if product.image else None,
                }
            })
        except (DIE, ValueError) as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class BranchProductDeleteView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Mahsulotni soft-delete qilish."""
    def post(self, request, pk):
        try:
            product = get_object_or_404(Product, pk=pk, is_active=True, business=request.business)
            product.is_active = False
            product.save(update_fields=['is_active'])
            ActivityLog.objects.create(
                user=request.user, business=request.business, action_type='product_delete',
                description=f"Mahsulot o'chirildi: {product.name}",
                extra_data={'product_id': product.id, 'name': product.name}
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ─── Batch Return (xarid qaytarish) ──────────────────────────────────────────

class BatchReturnView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """
    Xarid qaytarish — batch ichidagi qolgan mahsulotni kompaniyaga qaytarish.
      - stock kamayadi
      - qarz kamayadi (avvalo qarzdan, ortiqcha avansga)
    """
    def post(self, request, batch_id):
        try:
            batch    = get_object_or_404(StockBatch, pk=batch_id, is_active=True, business=request.business)
            data     = json.loads(request.body)
            try:
                quantity = Decimal(str(data.get('quantity', 0)))
            except (InvalidOperation, ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': "Miqdor noto'g'ri"}, status=400)
            reason   = data.get('reason', '').strip()

            if quantity <= 0:
                return JsonResponse({'status': 'error',
                                     'message': "Miqdor 0 dan katta bo'lishi kerak"}, status=400)

            returned_amount = StockService.return_purchase(
                batch=batch, quantity=quantity, user=request.user, reason=reason
            )

            new_debt    = None
            new_advance = None
            branch = batch.branch
            if branch:
                CompanyService.record_return(
                    branch=branch, amount=returned_amount, user=request.user,
                )
                branch.refresh_from_db()
                new_debt    = str(branch.total_debt)
                new_advance = str(branch.advance_balance)

            batch.refresh_from_db()
            batch.product.refresh_from_db()

            return JsonResponse({
                'status':          'success',
                'returned_amount': str(returned_amount),
                'new_remaining':   str(batch.remaining_quantity),
                'new_received':    str(batch.quantity_received),
                'new_stock':       str(batch.product.stock),
                'new_debt':        new_debt,
                'new_advance':     new_advance,
            })

        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class BranchProductPurchaseView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Mahsulotni sotib olish — ikki rejim:

      1) Dona/kg rejimi (oldingi kabi):
         { "mode": "unit", "quantity": 10, "cost_price": 700 }
         → 10 dona, 1 donasi 700 so'm

      2) Karobka rejimi (yangi):
         { "mode": "box", "box_quantity": 2, "cost_price": 700 }
         → units_per_box MAHSULOTDAN avtomatik olinadi (Product.units_per_box)
         → 2 karobka × (masalan 15) dona = 30 dona, 1 donasi 700 so'm
         (cost_price har doim ENG KICHIK birlik narxi, karobka narxi emas!)

      Ikkalasida ham StockBatch.quantity_received har doim eng kichik
      birlikda (dona/kg) saqlanadi — FIFO, dashboard, return o'zgarishsiz.
    """
    def post(self, request, pk):
        try:
            product = get_object_or_404(Product, pk=pk, is_active=True, business=request.business)
            data    = json.loads(request.body)
            mode    = data.get('mode', 'unit')   # 'unit' | 'box'

            box_quantity  = None
            units_per_box = None

            if mode == 'box':
                # ── Karobka rejimi: units_per_box MAHSULOTDAN olinadi ──────
                if not product.is_box_enabled or not product.units_per_box:
                    return JsonResponse({'status': 'error', 'message': "Bu mahsulot uchun karobka sozlanmagan. Mahsulotni Edit qiling"}, status=400)

                try:
                    box_quantity = int(data.get('box_quantity', 0))
                except (ValueError, TypeError):
                    return JsonResponse({'status': 'error', 'message': "Karobka soni noto'g'ri"}, status=400)

                if box_quantity <= 0:
                    return JsonResponse({'status': 'error', 'message': "Karobka soni 0 dan katta bo'lishi kerak"}, status=400)

                units_per_box = product.units_per_box   # ← Product dan, operator kiritmaydi

                quantity = Decimal(box_quantity) * units_per_box
            else:
                # ── Dona/kg rejimi (oldingi kabi) ────────────────────────────
                try:
                    quantity = Decimal(str(data.get('quantity', 0)))
                except (InvalidOperation, ValueError, TypeError):
                    return JsonResponse({'status': 'error', 'message': "Miqdor noto'g'ri"}, status=400)

            # Tan narxini: 1) JSON dan (edit holat), 2) oxirgi batch dan olamiz
            cost_price_raw = data.get('cost_price')
            if cost_price_raw:
                cost_price = Decimal(str(cost_price_raw))
            else:
                last_batch = product.stock_batches.filter(is_active=True).order_by('-created_at').first()
                if not last_batch:
                    return JsonResponse({'status': 'error', 'message': "Mahsulot uchun tan narxi belgilanmagan. Avval mahsulotni Edit qiling"}, status=400)
                cost_price = last_batch.cost_price

            if quantity <= 0:
                return JsonResponse({'status': 'error', 'message': "Miqdor 0 dan katta bo'lishi kerak"}, status=400)
            if cost_price <= 0:
                return JsonResponse({'status': 'error', 'message': "Tan narxi 0 dan katta bo'lishi kerak"}, status=400)

            total_cost = quantity * cost_price

            batch = StockService.add_stock(
                product=product,
                quantity=quantity,
                cost_price=cost_price,
                branch=product.branch,
                user=request.user,
                box_quantity=box_quantity,
                units_per_box=units_per_box,
            )
            product.refresh_from_db()

            # ← Qarzni oshiramiz: biz filialga shu summani qarzdormiz
            if product.branch:
                CompanyService.record_purchase(
                    branch=product.branch,
                    amount=total_cost,
                    user=request.user,
                )
                product.branch.refresh_from_db()
                new_debt    = str(product.branch.total_debt)
                new_advance = str(product.branch.advance_balance)
            else:
                new_debt    = '0'
                new_advance = '0'

            unit_label = product.get_unit_type_display()
            if mode == 'box':
                desc = (f"Sotib olindi: {product.name} — {box_quantity} karobka × "
                        f"{units_per_box} {unit_label} = {quantity} {unit_label}, "
                        f"1 {unit_label} tan narxi: {cost_price:,.0f} so'm")
            else:
                desc = f"Sotib olindi: {product.name} × {quantity} {unit_label}, tan narx: {cost_price:,.0f} so'm"

            ActivityLog.objects.create(
                user=request.user, business=request.business, action_type='stock_add',
                description=desc,
                extra_data={
                    'product_id': product.id, 'name': product.name, 'batch_id': batch.id,
                    'quantity': str(quantity), 'unit_label': unit_label, 'cost_price': str(cost_price),
                    'total_cost': str(total_cost),
                    'branch_id': product.branch_id,
                    'mode': mode,
                    'box_quantity': box_quantity, 'units_per_box': str(units_per_box) if units_per_box else None,
                }
            )

            return JsonResponse({
                'status':     'success',
                'new_stock':  str(product.stock),
                'batch_id':   batch.id,
                'new_debt':   new_debt,
                'new_advance':new_advance,
                'total_cost': str(total_cost),
                'quantity':   str(quantity),
            })
        except (InvalidOperation, ValueError) as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class BranchPaymentsApiView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """
    AJAX: branch to'lovlari tarixi — offset asosida load more.
    GET /company/api/branch/<pk>/payments/?offset=10&limit=10
    """
    PAGE_SIZE = 10

    def get(self, request, pk):
        branch = get_object_or_404(Branch, pk=pk, is_active=True, company__business=request.business)
        try:
            offset = max(int(request.GET.get('offset', 0)), 0)
        except ValueError:
            offset = 0

        qs    = BranchPayment.objects.filter(branch=branch).order_by('-created_at')
        total = qs.count()
        items = qs.select_related('user')[offset: offset + self.PAGE_SIZE]

        TYPE_LABELS = {'cash': 'Naqd', 'transfer': "O'tkazma", 'discount': 'Chegirma'}

        return JsonResponse({
            'items': [
                {
                    'amount':       str(p.amount),
                    'payment_type': p.payment_type,
                    'type_label':   TYPE_LABELS.get(p.payment_type, p.payment_type),
                    'note':         p.note,
                    'date':         p.created_at.strftime('%d.%m.%y'),
                    'time':         p.created_at.strftime('%H:%M'),
                }
                for p in items
            ],
            'has_more': (offset + self.PAGE_SIZE) < total,
            'next_offset': offset + self.PAGE_SIZE,
            'total': total,
        })