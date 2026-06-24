# notebook/business/context_processors.py
from .models import Business


def business_context(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}

    ctx = {'current_business': getattr(request, 'business', None)}

    if getattr(user, 'is_superadmin', False):
        ctx['switchable_businesses'] = Business.objects.filter(is_active=True).order_by('name')

    return ctx
