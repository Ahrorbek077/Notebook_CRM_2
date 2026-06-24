# notebook/business/forms.py
from django import forms
from .models import Business


class BusinessForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ['name', 'phone', 'note']
        widgets = {
            'name':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Biznes nomi (masalan: Aka — asosiy biznes)"}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998901234567'}),
            'note':  forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Biznes nomi kiritilishi shart")
        return name
