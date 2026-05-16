# notebook/clients/forms.py
from django import forms
from .models import Client, Region


class ClientForm(forms.ModelForm):
    # Xaritadan keladigan koordinatalar (ixtiyoriy)
    latitude  = forms.DecimalField(
        max_digits=9, decimal_places=6,
        required=False, widget=forms.HiddenInput()
    )
    longitude = forms.DecimalField(
        max_digits=9, decimal_places=6,
        required=False, widget=forms.HiddenInput()
    )

    class Meta:
        model  = Client
        fields = ['name', 'phone', 'address', 'region', 'latitude', 'longitude']
        widgets = {
            'name':    forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Mijoz ismi (har qanday alifboda)"
            }),
            'phone':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998901234567'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'region':  forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Ism kiritilishi shart")
        if len(name) < 2:
            raise forms.ValidationError("Ism kamida 2 ta harf bo'lishi kerak")
        return name

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise forms.ValidationError("Telefon kiritilishi shart")
        return phone


class RegionForm(forms.ModelForm):
    class Meta:
        model  = Region
        fields = ['name', 'order']

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Viloyat nomi kiritilishi shart")
        return name