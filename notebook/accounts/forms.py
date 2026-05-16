# apps/accounts/forms.py
from django import forms
from django.contrib.auth import password_validation
from .models import User

class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Parol"
    )

    class Meta:
        model  = User
        fields = ["username", "phone", "role", "password"]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'phone':    forms.TextInput(attrs={'class': 'form-control'}),
            'role':     forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Superadmin faqat admin yoki staff qo'sha oladi
        self.fields['role'].choices = [
            ('admin', 'Admin'),
            ('staff', 'Xodim'),
        ]


class UserEditForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ["username", "phone", "role"]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'phone':    forms.TextInput(attrs={'class': 'form-control'}),
            'role':     forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [
            ('admin', 'Admin'),
            ('staff', 'Xodim'),
        ]


class ProfileForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['username', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'phone':    forms.TextInput(attrs={'class': 'form-control'}),
        }


class PasswordChangeForm(forms.Form):
    old_password  = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Joriy parol"
    )
    new_password  = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Yangi parol",
        min_length=6
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Yangi parolni tasdiqlang"
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old = self.cleaned_data.get('old_password')
        if not self.user.check_password(old):
            raise forms.ValidationError("Joriy parol noto'g'ri!")
        return old

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Yangi parollar mos emas!")
        return cleaned