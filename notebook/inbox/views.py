# notebook/inbox/views.py
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from decimal import Decimal, InvalidOperation

from notebook.core.mixins import AdminRequiredMixin
from notebook.business.mixins import BusinessRequiredMixin
from notebook.business.models import Business
from notebook.clients.models import Client
from .models import IncomingTransaction
from .services import IncomingTransactionService


@method_decorator(csrf_exempt, name='dispatch')
class BankWebhookView(View):
    """Telefon (MacroDroid) shu manzilga POST yuboradi.

    URL: /inbox/webhook/<token>/
    Body (form-encoded yoki JSON): {"text": "<SMS matni>", "source": "sms"}

    Autentifikatsiya yo'q (telefon login qila olmaydi) — o'rniga URL'dagi
    maxfiy `token` himoya qiladi. Token "Bizneslar" sahifasida ko'rinadi
    va xohlasa qayta generatsiya qilish mumkin.
    """
    def post(self, request, token):
        business = get_object_or_404(Business, webhook_token=token, is_active=True)

        text = request.POST.get('text', '')
        if not text and request.body:
            try:
                data = json.loads(request.body)
                text = data.get('text', '')
            except (json.JSONDecodeError, UnicodeDecodeError):
                text = ''

        if not text.strip():
            return JsonResponse({'status': 'error', 'message': "'text' maydoni bo'sh"}, status=400)

        source = request.POST.get('source') or 'sms'
        if source not in dict(IncomingTransaction.SOURCE_CHOICES):
            source = IncomingTransaction.SOURCE_SMS

        txn = IncomingTransactionService.create_from_webhook(business, text, source=source)
        return JsonResponse({'status': 'ok', 'id': txn.id, 'parsed_amount': str(txn.parsed_amount or '')})

    def get(self, request, token):
        # Ba'zi avtomatizatsiya vositalari (MacroDroid) GET so'rovi bilan ham
        # tekshirish qilishi mumkin — token to'g'riligini tasdiqlaymiz, xolos.
        get_object_or_404(Business, webhook_token=token, is_active=True)
        return JsonResponse({'status': 'ok', 'message': 'Webhook faol. SMS yuborish uchun POST ishlatilsin.'})


class IncomingTransactionListView(AdminRequiredMixin, LoginRequiredMixin, BusinessRequiredMixin, View):
    def get(self, request):
        unmatched = IncomingTransaction.objects.filter(
            business=request.business, status=IncomingTransaction.STATUS_UNMATCHED
        ).order_by('-created_at')
        recent = IncomingTransaction.objects.filter(
            business=request.business
        ).exclude(status=IncomingTransaction.STATUS_UNMATCHED).order_by('-created_at')[:20]

        clients = Client.objects.filter(business=request.business).order_by('name').only('id', 'name', 'phone', 'total_debt')

        return render(request, 'inbox/transaction_list.html', {
            'unmatched': unmatched,
            'recent': recent,
            'clients': clients,
            'webhook_url': request.build_absolute_uri(f'/inbox/webhook/{request.business.webhook_token}/'),
        })


class MatchTransactionView(AdminRequiredMixin, LoginRequiredMixin, BusinessRequiredMixin, View):
    def post(self, request, pk):
        txn = get_object_or_404(IncomingTransaction, pk=pk, business=request.business)
        client_id = request.POST.get('client_id')
        amount_raw = request.POST.get('amount')

        client = get_object_or_404(Client, pk=client_id, business=request.business)
        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError):
            return JsonResponse({'status': 'error', 'message': "Summa noto'g'ri"}, status=400)

        try:
            IncomingTransactionService.match_to_client(txn, client, amount, user=request.user)
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

        return JsonResponse({'status': 'success'})


class IgnoreTransactionView(AdminRequiredMixin, LoginRequiredMixin, BusinessRequiredMixin, View):
    def post(self, request, pk):
        txn = get_object_or_404(IncomingTransaction, pk=pk, business=request.business)
        txn.status = IncomingTransaction.STATUS_IGNORED
        txn.save(update_fields=['status'])
        return JsonResponse({'status': 'success'})


class RegenerateWebhookTokenView(AdminRequiredMixin, LoginRequiredMixin, BusinessRequiredMixin, View):
    """Token kimgadir bilinib qolsa — superadmin shu yerdan yangilab qo'yadi."""
    def post(self, request):
        import secrets
        business = request.business
        business.webhook_token = secrets.token_urlsafe(24)
        business.save(update_fields=['webhook_token'])
        return JsonResponse({
            'status': 'success',
            'webhook_url': request.build_absolute_uri(f'/inbox/webhook/{business.webhook_token}/'),
        })
