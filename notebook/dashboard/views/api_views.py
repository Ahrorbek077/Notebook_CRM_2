# notebook/dashboard/views/api_views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from notebook.dashboard.services import DashboardService, AnalyticsService


@login_required
def dashboard_api(request):
    if request.business is None:
        return JsonResponse({'error': "Sizga hali biznes biriktirilmagan"}, status=403)
    try:
        return JsonResponse(DashboardService.get_dashboard_data(request.business.id))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def analytics_api(request):
    if request.business is None:
        return JsonResponse({'error': "Sizga hali biznes biriktirilmagan"}, status=403)
    try:
        return JsonResponse(AnalyticsService.get_overview(request.business.id))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)