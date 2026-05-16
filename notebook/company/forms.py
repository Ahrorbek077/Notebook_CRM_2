# notebook/company/forms.py
from django import forms
from .models import Company, Branch


class CompanyForm(forms.ModelForm):
    class Meta:
        model  = Company
        fields = ['name', 'phone', 'address', 'note']
        widgets = {
            'name':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Kompaniya nomi"}),
            'phone':   forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'note':    forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Kompaniya nomi kiritilishi shart")
        return name


class BranchForm(forms.ModelForm):
    class Meta:
        model  = Branch
        fields = ['name', 'phone', 'address', 'note']
        widgets = {
            'name':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Filial nomi"}),
            'phone':   forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'note':    forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Filial nomi kiritilishi shart")
        return name
