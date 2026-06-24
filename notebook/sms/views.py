# notebook/sms/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from notebook.business.mixins import BusinessRequiredMixin
from notebook.clients.models import Client
from .services import SmsService, EskizAPIError, SmsRateLimitError


class SendBalanceSmsView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """POST /sms/send/<client_id>/ — mijozga qarz/avans haqida avtomatik SMS yuboradi."""

    def post(self, request, client_id):
        client = get_object_or_404(Client, id=client_id, business=request.business)
        try:
            log = SmsService.send_balance_sms(client, user=request.user)
        except SmsRateLimitError as e:
            # 429 — "juda ko'p so'rov", frontend buni alohida (kutish) ko'rsatishi mumkin
            return JsonResponse({'status': 'error', 'message': str(e)}, status=429)
        except EskizAPIError as e:
            return JsonResponse({'status': 'error', 'message': f"SMS yuborilmadi: {e}"}, status=502)
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Kutilmagan xatolik: {e}"}, status=500)

        return JsonResponse({
            'status': 'success',
            'message': f"SMS {client.phone} raqamiga yuborildi",
            'sms_log_id': log.id,
        })