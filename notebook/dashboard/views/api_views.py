# notebook/dashboard/views/api_views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from notebook.dashboard.services import DashboardService


@login_required
def dashboard_api(request):
    try:
        return JsonResponse(DashboardService.get_dashboard_data())
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)