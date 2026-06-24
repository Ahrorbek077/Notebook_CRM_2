# notebook/business/middleware.py
"""
CurrentBusinessMiddleware — har bir so'rovga `request.business` ni qo'shadi.

Qoidalar:
  - Superadmin (aka): session['active_business_id'] orqali TANLAGAN biznesni
    ko'radi. Hali tanlamagan bo'lsa — o'zining biznesi (request.user.business)
    ko'rsatiladi. Shu orqali "switch" funksiyasi ishlaydi.
  - Admin/Staff: HAR DOIM faqat o'zining request.user.business'i.
    Session orqali boshqasini ko'ra olmaydi — bu ularning ma'lumotlari
    boshqalarga aralashib ketmasligini kafolatlaydi.
  - Anonim foydalanuvchi: request.business = None.
"""
from .models import Business


class CurrentBusinessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.business = None

        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            if getattr(user, 'is_superadmin', False):
                biz_id = request.session.get('active_business_id')
                business = None
                if biz_id:
                    business = Business.objects.filter(id=biz_id, is_active=True).first()
                if business is None:
                    business = user.business
                    if business:
                        request.session['active_business_id'] = business.id
                request.business = business
            else:
                request.business = user.business

        return self.get_response(request)
