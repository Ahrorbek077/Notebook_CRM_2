# notebook/accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator

from .models import User
from .forms import RegisterForm, UserEditForm, ProfileForm, PasswordChangeForm, LoginForm
from .decorators import superadmin_required


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:launcher')
    form  = LoginForm(request.POST or None)
    error = None
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user:
            if not user.is_active:
                error = "Sizning hisobingiz bloklangan!"
            else:
                login(request, user)
                return redirect('dashboard:launcher')
        else:
            error = "Login yoki parol noto'g'ri!"
    return render(request, 'accounts/login.html', {'form': form, 'error': error})


@login_required
def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@method_decorator(superadmin_required, name='dispatch')
class StaffListView(View):
    def get(self, request):
        users  = User.objects.exclude(role='superadmin').filter(
            business=request.business
        ).select_related('fired_by').order_by('is_active', '-created_at')
        return render(request, 'accounts/staff.html', {
            'active_users': users.filter(is_active=True),
            'fired_users':  users.filter(is_active=False),
        })


@method_decorator(superadmin_required, name='dispatch')
class StaffCreateView(View):
    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.business = request.business
            user.save()
            return JsonResponse({'status': 'created', 'id': user.id, 'username': user.username,
                                 'role': user.get_role_display(), 'phone': user.phone})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


@method_decorator(superadmin_required, name='dispatch')
class StaffEditView(View):
    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id, business=request.business)
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'updated', 'username': user.username,
                                 'role': user.get_role_display(), 'phone': user.phone})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


@method_decorator(superadmin_required, name='dispatch')
class StaffFireView(View):
    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id, business=request.business)
        if user.is_superadmin:
            return JsonResponse({'status': 'error', 'message': "Super adminni ishdan bo'yb bo'lmaydi!"}, status=403)
        action = request.POST.get('action', 'fire')
        if action == 'fire':
            user.fire(fired_by=request.user)
            msg = f"{user.username} ishdan haydaldi"
        else:
            user.is_active = True
            user.fired_at  = None
            user.fired_by  = None
            user.save(update_fields=['is_active', 'fired_at', 'fired_by'])
            msg = f"{user.username} qayta yollandi"
        return JsonResponse({'status': 'success', 'message': msg})


@method_decorator(login_required, name='dispatch')
class SettingsView(View):
    def get(self, request):
        return render(request, 'accounts/settings.html', {
            'profile_form':  ProfileForm(instance=request.user),
            'password_form': PasswordChangeForm(user=request.user),
        })

    def post(self, request):
        action = request.POST.get('action')
        if action == 'profile':
            form = ProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                return JsonResponse({'status': 'success', 'message': 'Profil yangilandi!',
                                     'username': request.user.username})
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        elif action == 'password':
            form = PasswordChangeForm(user=request.user, data=request.POST)
            if form.is_valid():
                request.user.set_password(form.cleaned_data['new_password'])
                request.user.save()
                update_session_auth_hash(request, request.user)
                return JsonResponse({'status': 'success', 'message': "Parol o'zgartirildi!"})
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return JsonResponse({'status': 'error', 'message': "Noto'g'ri so'rov"}, status=400)


class DirectoryView(View):
    def get(self, request):
        from notebook.catalog.models import Category
        from notebook.clients.models import Region
        return render(request, 'accounts/directory.html', {
            'categories': Category.all_objects.filter(business=request.business),
            'regions':    Region.objects.filter(business=request.business),
        })


# Error handlers
def error_403(request, exception=None):
    return render(request, 'errors/403.html', status=403)

def error_404(request, exception=None):
    return render(request, 'errors/404.html', status=404)

def error_413(request, exception=None):
    return render(request, 'errors/413.html', status=413)

def error_500(request):
    return render(request, 'errors/500.html', status=500)
