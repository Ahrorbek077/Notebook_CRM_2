# notebook/business/mixins.py
"""
Boshqa app'lar view'larida ishlatiladigan umumiy yordamchilar.

Misol (CBV):
    class ClientListView(BusinessRequiredMixin, ListView):
        model = Client

        def get_queryset(self):
            qs = super().get_queryset()           # ── biror filterdan keyin
            return self.scope(qs)                  # ── joriy biznes bilan cheklaydi

Misol (function-based / oddiy View):
    from notebook.business.mixins import scope_qs
    qs = scope_qs(Client.objects.all(), request)
"""
from django.core.exceptions import PermissionDenied


def scope_qs(queryset, request, field='business'):
    """Berilgan queryset'ni request.business bilan cheklaydi.

    Superadmin biznes tanlamagan (juda kam holat, masalan business hali
    yo'q) bo'lsa — bo'sh queryset qaytaradi (xavfsizlik uchun: noaniqlik
    bo'lganda HECH NARSA ko'rsatmaslik, hamma narsani ko'rsatishdan yaxshi).
    """
    business = getattr(request, 'business', None)
    if business is None:
        return queryset.none()
    return queryset.filter(**{field: business})


class BusinessRequiredMixin:
    """Foydalanuvchi tizimga kirgan va joriy biznesi aniqlangan bo'lishi shart.

    AdminRequiredMixin/LoginRequiredMixin bilan birga ishlatiladi.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.business is None:
            raise PermissionDenied("Sizga hali biznes biriktirilmagan. Administratorga murojaat qiling.")
        return super().dispatch(request, *args, **kwargs)

    def scope(self, queryset, field='business'):
        return scope_qs(queryset, self.request, field=field)
