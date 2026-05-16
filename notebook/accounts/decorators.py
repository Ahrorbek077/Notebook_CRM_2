# apps/accounts/decorators.py
from functools import wraps
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def superadmin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superadmin:
            return render(request, 'errors/403.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapper