# notebook/containers/views.py
import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from notebook.clients.models import Client
from notebook.company.models import Branch
from notebook.business.mixins import BusinessRequiredMixin
from .models import ContainerType, BranchContainerStock, ClientContainer
from .services import ContainerService


class ContainerTypeListView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Barcha faol idish turlarini qaytaradi — dropdown uchun."""
    def get(self, request):
        types = ContainerType.objects.filter(is_active=True, business=request.business).values('id', 'name')
        return JsonResponse({'status': 'success', 'types': list(types)})


class ClientContainerSummaryView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Mijozdagi barcha idishlarni qaytaradi — Client detail oyna uchun."""
    def get(self, request, client_id):
        client = get_object_or_404(Client, pk=client_id, business=request.business)
        summary = ContainerService.get_client_summary(client)
        total = sum(item['quantity'] for item in summary)
        return JsonResponse({'status': 'success', 'items': summary, 'total': total})


class GiveContainerView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Mijozga idish berish."""
    def post(self, request, client_id):
        try:
            client = get_object_or_404(Client, pk=client_id, business=request.business)
            data = json.loads(request.body)

            branch_id = data.get('branch_id')
            type_id   = data.get('container_type_id')
            quantity  = int(data.get('quantity', 0))
            note      = data.get('note', '').strip()

            if not branch_id or not type_id:
                return JsonResponse({'status': 'error', 'message': "Filial va idish turi tanlanishi shart"}, status=400)

            branch = get_object_or_404(Branch, pk=branch_id, company__business=request.business)
            container_type = get_object_or_404(ContainerType, pk=type_id, business=request.business)

            ContainerService.give(
                client=client, branch=branch, container_type=container_type,
                quantity=quantity, user=request.user, note=note,
            )

            # Yangilangan holatlarni qaytaramiz — frontend DOM yangilash uchun
            client_qty = ClientContainer.objects.filter(
                client=client, container_type=container_type
            ).values_list('quantity', flat=True).first() or 0
            branch_qty = BranchContainerStock.objects.filter(
                branch=branch, container_type=container_type
            ).values_list('quantity', flat=True).first() or 0

            client_total = sum(
                ClientContainer.objects.filter(client=client).values_list('quantity', flat=True)
            )

            return JsonResponse({
                'status': 'success',
                'client_quantity': client_qty,
                'branch_quantity': branch_qty,
                'client_total': client_total,
            })
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class ReturnContainerView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Mijozdan idish qaytarib olish."""
    def post(self, request, client_id):
        try:
            client = get_object_or_404(Client, pk=client_id, business=request.business)
            data = json.loads(request.body)

            branch_id = data.get('branch_id')
            type_id   = data.get('container_type_id')
            quantity  = int(data.get('quantity', 0))
            note      = data.get('note', '').strip()

            if not branch_id or not type_id:
                return JsonResponse({'status': 'error', 'message': "Filial va idish turi tanlanishi shart"}, status=400)

            branch = get_object_or_404(Branch, pk=branch_id, company__business=request.business)
            container_type = get_object_or_404(ContainerType, pk=type_id, business=request.business)

            ContainerService.return_containers(
                client=client, branch=branch, container_type=container_type,
                quantity=quantity, user=request.user, note=note,
            )

            client_qty = ClientContainer.objects.filter(
                client=client, container_type=container_type
            ).values_list('quantity', flat=True).first() or 0
            branch_qty = BranchContainerStock.objects.filter(
                branch=branch, container_type=container_type
            ).values_list('quantity', flat=True).first() or 0

            client_total = sum(
                ClientContainer.objects.filter(client=client).values_list('quantity', flat=True)
            )

            return JsonResponse({
                'status': 'success',
                'client_quantity': client_qty,
                'branch_quantity': branch_qty,
                'client_total': client_total,
            })
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class BranchContainerStockView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Filial idish omborini ko'rish (GET) va to'ldirish (POST)."""
    def get(self, request, branch_id):
        branch = get_object_or_404(Branch, pk=branch_id, company__business=request.business)
        summary = ContainerService.get_branch_summary(branch)
        return JsonResponse({'status': 'success', 'items': summary})

    def post(self, request, branch_id):
        """Omborni to'ldirish — yangi idish keldi (mijoz bilan bog'liq emas)."""
        try:
            branch = get_object_or_404(Branch, pk=branch_id, company__business=request.business)
            data = json.loads(request.body)

            type_id  = data.get('container_type_id')
            quantity = int(data.get('quantity', 0))

            if not type_id:
                return JsonResponse({'status': 'error', 'message': "Idish turi tanlanishi shart"}, status=400)

            container_type = get_object_or_404(ContainerType, pk=type_id, business=request.business)
            stock = ContainerService.add_to_branch_stock(
                branch=branch, container_type=container_type,
                quantity=quantity, user=request.user,
            )
            return JsonResponse({'status': 'success', 'new_quantity': stock.quantity})
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class ContainerTypeCreateView(LoginRequiredMixin, BusinessRequiredMixin, View):
    """Yangi idish turi yaratish (masalan 'Temir karzinka')."""
    def post(self, request):
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            if not name:
                return JsonResponse({'status': 'error', 'message': "Nomi kiritilishi shart"}, status=400)
            obj, created = ContainerType.objects.get_or_create(name=name, business=request.business)
            if not created:
                return JsonResponse({'status': 'error', 'message': "Bu idish turi allaqachon mavjud"}, status=400)
            return JsonResponse({'status': 'success', 'id': obj.id, 'name': obj.name})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)