# notebook/ocr/views.py
"""
Chek OCR — ikki endpoint:

  1. POST /ocr/api/branch/<pk>/scan/     (multipart, image=<fayl>)
     → OCR + parse + matching → tahrirlanadigan qatorlar JSON

  2. POST /ocr/api/branch/<pk>/confirm/  (JSON, rows=[...])
     → har qator uchun StockService.add_stock (xuddi mavjud xarid kabi),
       filial qarzini CompanyService.record_purchase bilan oshiradi,
       ActivityLog yozadi.

Tasdiqlash mavjud BranchProductPurchaseView mantig'ini aynan takrorlaydi —
FIFO, qarz, karobka tarixi hech narsa buzilmaydi.
"""
import json
import logging
from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from notebook.business.mixins import BusinessRequiredMixin
from notebook.company.models import Branch
from notebook.company.services import CompanyService
from notebook.catalog.models import Product
from notebook.inventory.services import StockService
from notebook.activity.models import ActivityLog

from .engine import image_to_text, OcrError
from .parser import parse_receipt_text, match_products

logger = logging.getLogger(__name__)

MAX_IMAGE_MB = 10
MAX_ROWS     = 60   # bitta chekdan maksimal qator


class ReceiptScanView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Rasm → OCR → parse → matching → JSON."""

    def post(self, request, pk):
        branch = get_object_or_404(
            Branch, pk=pk, is_active=True, company__business=request.business
        )

        img = request.FILES.get('image')
        if not img:
            return JsonResponse({'status': 'error', 'message': "Rasm yuborilmadi."}, status=400)
        if img.size > MAX_IMAGE_MB * 1024 * 1024:
            return JsonResponse({'status': 'error',
                                 'message': f"Rasm {MAX_IMAGE_MB} MB dan katta."}, status=400)

        # ── OCR ──────────────────────────────────────────────────────────────
        try:
            text = image_to_text(img)
        except OcrError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=422)

        # ── Parse + matching ─────────────────────────────────────────────────
        products = Product.objects.filter(
            branch=branch, business=request.business, is_active=True
        ).order_by('name')

        rows = parse_receipt_text(text)[:MAX_ROWS]
        rows = match_products(rows, products)

        # Tan narx taklifi: agar parse narx topmagan bo'lsa, oxirgi batch narxi
        last_costs = {}
        for p in products:
            lb = p.stock_batches.filter(is_active=True).order_by('-created_at').first()
            last_costs[p.id] = str(lb.cost_price) if lb else ''

        return JsonResponse({
            'status': 'ok',
            'rows': rows,
            'raw_text': text,   # debug/ko'rish uchun (UI'da yashirin blokda)
            'products': [{
                'id': p.id, 'name': p.name,
                'unit': p.get_unit_type_display() if hasattr(p, 'get_unit_type_display') else 'dona',
                'box_enabled': bool(getattr(p, 'is_box_enabled', False) and getattr(p, 'units_per_box', None)),
                'units_per_box': str(p.units_per_box) if getattr(p, 'units_per_box', None) else '',
                'last_cost': last_costs.get(p.id, ''),
            } for p in products],
        })


class ReceiptConfirmView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Tasdiqlangan qatorlar → kirim (StockBatch) + filial qarzi + ActivityLog."""

    def post(self, request, pk):
        branch = get_object_or_404(
            Branch, pk=pk, is_active=True, company__business=request.business
        )

        try:
            data = json.loads(request.body or '{}')
            rows = data.get('rows', [])
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': "Noto'g'ri JSON."}, status=400)

        if not rows or not isinstance(rows, list):
            return JsonResponse({'status': 'error', 'message': "Qatorlar bo'sh."}, status=400)
        if len(rows) > MAX_ROWS:
            return JsonResponse({'status': 'error', 'message': "Qatorlar juda ko'p."}, status=400)

        created, errors = [], []
        grand_total = Decimal('0')

        for i, row in enumerate(rows, start=1):
            try:
                product = Product.objects.get(
                    pk=int(row.get('product_id') or 0),
                    branch=branch, business=request.business, is_active=True,
                )
            except (Product.DoesNotExist, ValueError, TypeError):
                errors.append(f"{i}-qator: mahsulot tanlanmagan.")
                continue

            mode = row.get('mode', 'unit')   # 'unit' | 'box'
            try:
                cost_price = Decimal(str(row.get('cost_price', 0)))
            except (InvalidOperation, ValueError, TypeError):
                errors.append(f"{i}-qator ({product.name}): narx noto'g'ri.")
                continue

            box_quantity, units_per_box = None, None
            if mode == 'box':
                if not getattr(product, 'is_box_enabled', False) or not getattr(product, 'units_per_box', None):
                    errors.append(f"{i}-qator ({product.name}): karobka sozlanmagan.")
                    continue
                try:
                    box_quantity = int(Decimal(str(row.get('quantity', 0))))
                except (InvalidOperation, ValueError, TypeError):
                    errors.append(f"{i}-qator ({product.name}): karobka soni noto'g'ri.")
                    continue
                if box_quantity <= 0:
                    errors.append(f"{i}-qator ({product.name}): karobka soni 0 dan katta emas.")
                    continue
                units_per_box = product.units_per_box
                quantity = Decimal(box_quantity) * units_per_box
            else:
                try:
                    quantity = Decimal(str(row.get('quantity', 0)))
                except (InvalidOperation, ValueError, TypeError):
                    errors.append(f"{i}-qator ({product.name}): miqdor noto'g'ri.")
                    continue

            if quantity <= 0 or cost_price <= 0:
                errors.append(f"{i}-qator ({product.name}): miqdor/narx musbat bo'lsin.")
                continue

            try:
                batch = StockService.add_stock(
                    product=product, quantity=quantity, cost_price=cost_price,
                    branch=branch, user=request.user,
                    box_quantity=box_quantity, units_per_box=units_per_box,
                )
            except ValueError as e:
                errors.append(f"{i}-qator ({product.name}): {e}")
                continue

            line_total   = quantity * cost_price
            grand_total += line_total
            created.append({
                'product': product.name, 'batch_id': batch.id,
                'quantity': str(quantity), 'total': str(line_total),
            })

        # ── Filial qarzi — bitta umumiy summa (mavjud oqim bilan bir xil) ────
        if grand_total > 0:
            CompanyService.record_purchase(branch=branch, amount=grand_total, user=request.user)
            branch.refresh_from_db()

        if created:
            ActivityLog.objects.create(
                user=request.user, business=request.business, action_type='stock_add',
                description=(f"Chekdan xarid (OCR): {branch} — {len(created)} qator, "
                             f"jami {grand_total:,.0f} so'm"),
                extra_data={
                    'branch_id': branch.id, 'source': 'receipt_ocr',
                    'rows': created, 'grand_total': str(grand_total),
                },
            )

        if not created:
            return JsonResponse({'status': 'error',
                                 'message': "Hech narsa kiritilmadi. " + " ".join(errors)}, status=400)

        return JsonResponse({
            'status': 'ok',
            'created_count': len(created),
            'grand_total': str(grand_total),
            'new_debt': str(branch.total_debt),
            'errors': errors,   # qisman xatolar (bo'lsa) — UI ko'rsatadi
        })
