# notebook/sales/services.py
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from django.core.cache import cache
from django.db.transaction import on_commit


class SaleService:

    @staticmethod
    def create_sale_from_cart(client, cart_items: list, user=None):
        from notebook.catalog.models import Product
        from notebook.inventory.services import StockService
        from notebook.activity.models import ActivityLog
        from .models import Sale, SaleItem

        if not client.is_active:
            raise ValueError(f"Mijoz {client.name} faol emas!")

        with transaction.atomic():
            total_amount = Decimal('0')
            sale_items   = []

            products = {
                p.id: p for p in
                Product.objects.select_for_update().filter(
                    id__in=[i['product_id'] for i in cart_items], is_active=True
                )
            }

            for item in cart_items:
                product = products.get(item['product_id'])
                if not product:
                    raise ValueError("Mahsulot topilmadi")
                qty = item['quantity']
                if product.stock < qty:
                    raise ValueError(f"{product.name} omborda yetarli emas!")

                for f in StockService.consume_fifo(product, qty):
                    subtotal = product.price * f['quantity']
                    total_amount += subtotal
                    sale_items.append(SaleItem(
                        product=product,
                        batch=f['batch'],
                        quantity=f['quantity'],
                        price_at_sale=product.price,
                        cost_price_at_sale=f['cost_price'],
                    ))

            sale = Sale.objects.create(client=client, user=user, total_amount=total_amount)
            for si in sale_items:
                si.sale = sale
            SaleItem.objects.bulk_create(sale_items, batch_size=500)

            ActivityLog.objects.create(
                user=user, action_type='sale',
                description=f"{client.name} — {total_amount:,.0f} so'm sotuv",
                extra_data={
                    'sale_id': sale.id, 'client_id': client.id,
                    'client_name': client.name, 'total_amount': str(total_amount),
                    'items': [{'product': si.product.name, 'quantity': si.quantity,
                               'price': str(si.price_at_sale)} for si in sale_items],
                }
            )

            SaleService._add_to_client_debt(client, total_amount)
            cache.delete('dashboard_full_data')
            on_commit(lambda: _refresh_mv())
            return sale

    @staticmethod
    def process_return(sale, return_data: list, user=None, reason=""):
        from notebook.inventory.services import StockService
        from notebook.activity.models import ActivityLog
        from .models import SaleItem, SaleReturn, SaleReturnItem

        with transaction.atomic():
            sale_return     = SaleReturn.objects.create(sale=sale, user=user, reason=reason)
            returned_amount = Decimal('0')
            returned_items_data = []

            # Barcha kerakli sale_item larni BITTA so'rovda olamiz (N+1 emas)
            item_ids = [d['sale_item_id'] for d in return_data]
            # select_for_update() + select_related(nullable FK) PostgreSQL da
            # "FOR UPDATE cannot be applied to the nullable side of an outer join"
            # xatosini beradi. Shuning uchun avval lock, keyin select_related.
            SaleItem.objects.select_for_update().filter(
                id__in=item_ids, sale=sale
            ).values('id')  # faqat lock — SELECT FOR UPDATE, JOIN yo'q
            sale_items_map = {
                si.id: si
                for si in SaleItem.objects.select_related(
                    'product', 'batch'
                ).filter(id__in=item_ids, sale=sale)
            }

            return_item_objs = []
            for item_data in return_data:
                sale_item = sale_items_map.get(item_data['sale_item_id'])
                if not sale_item:
                    raise ValueError("SaleItem topilmadi")
                qty = item_data['quantity']
                if qty <= 0 or qty > sale_item.get_remaining_quantity():
                    raise ValueError("Qaytarish miqdori noto'g'ri")
                if not sale_item.batch:
                    raise ValueError("Batch topilmadi")

                StockService.return_to_batch(batch=sale_item.batch, quantity=qty, user=user, reason=reason)
                sale_item.returned_quantity += qty
                sale_item.save(update_fields=['returned_quantity'])
                returned_amount += sale_item.price_at_sale * qty

                return_item_objs.append(SaleReturnItem(
                    sale_return=sale_return,
                    sale_item=sale_item,
                    returned_quantity=qty,
                    returned_to_batch=sale_item.batch,
                ))
                returned_items_data.append({
                    'product': sale_item.product.name, 'quantity': qty,
                    'price': str(sale_item.price_at_sale),
                })

            # bulk_create — N ta INSERT o'rniga bitta
            SaleReturnItem.objects.bulk_create(return_item_objs)

            ActivityLog.objects.create(
                user=user, action_type='sale_return',
                description=f"{sale.client.name} — {returned_amount:,.0f} so'm qaytarildi",
                extra_data={
                    'return_id': sale_return.id, 'sale_id': sale.id,
                    'client_name': sale.client.name, 'total': str(returned_amount),
                    'reason': reason, 'items': returned_items_data,
                }
            )

            SaleService._reduce_client_debt(sale.client, returned_amount)

            # sale.items.all() bitta query — xotirada tekshiramiz
            all_items = list(sale.items.all())
            if all(i.returned_quantity >= i.quantity for i in all_items):
                sale.cancel(cancelled_by=user)

            cache.delete('dashboard_full_data')
            on_commit(lambda: _refresh_mv())
            return sale_return

    @staticmethod
    def full_cancel_sale(sale, cancelled_by=None, reason=""):
        with transaction.atomic():
            # items bir marta olinadi, process_return ga list sifatida beriladi
            remaining = [
                {'sale_item_id': i.id, 'quantity': i.get_remaining_quantity()}
                for i in sale.items.all() if i.get_remaining_quantity() > 0
            ]
            if remaining:
                SaleService.process_return(sale=sale, return_data=remaining,
                                           user=cancelled_by, reason=reason or "Full Cancel")

    @staticmethod
    def _add_to_client_debt(client, amount: Decimal):
        from notebook.clients.models import Client
        client = Client.objects.select_for_update().get(pk=client.pk)
        if client.advance_balance >= amount:
            client.advance_balance -= amount
        else:
            remaining = amount - client.advance_balance
            client.advance_balance = Decimal('0')
            client.total_debt += remaining
        client.save(update_fields=['total_debt', 'advance_balance'])

    @staticmethod
    def _reduce_client_debt(client, amount: Decimal):
        from notebook.clients.models import Client
        client = Client.objects.select_for_update().get(pk=client.pk)
        if client.total_debt >= amount:
            client.total_debt -= amount
        else:
            remaining = amount - client.total_debt
            client.total_debt = Decimal('0')
            client.advance_balance += remaining
        client.save(update_fields=['total_debt', 'advance_balance'])


def _refresh_mv():
    try:
        from notebook.dashboard.tasks import refresh_materialized_views
        refresh_materialized_views.delay()
    except Exception:
        pass