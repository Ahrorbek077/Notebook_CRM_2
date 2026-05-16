# notebook/core/mixins.py
"""
Barcha app'lar foydalanadigan umumiy Mixin'lar.
"""
from django.core.exceptions import PermissionDenied


class AdminRequiredMixin:
    """Faqat admin va superadmin o'ta oladi."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_admin:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
