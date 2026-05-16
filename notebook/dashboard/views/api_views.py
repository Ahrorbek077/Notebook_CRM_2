# notebook/dashboard/views/api_views.py
from django.http import JsonResponse
from notebook.dashboard.services import DashboardService


def dashboard_api(request):
    try:
        return JsonResponse(DashboardService.get_dashboard_data())
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
