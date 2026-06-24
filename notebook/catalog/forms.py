# notebook/catalog/forms.py
from django import forms
from .models import Product, Category


class ProductForm(forms.ModelForm):
    class Meta:
        model  = Product
        fields = ['name', 'category', 'price', 'unit_type', 'is_box_enabled', 'units_per_box', 'image']

    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs)
        if business is not None:
            self.fields['category'].queryset = Category.objects.filter(business=business)
        # Rasm va karobka maydonlari majburiy emas
        self.fields['image'].required = False
        self.fields['is_box_enabled'].required = False
        self.fields['units_per_box'].required = False
        widgets = {
            'name':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mahsulot nomi'}),
            'category':  forms.Select(attrs={'class': 'form-control'}),
            'price':     forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Sotuv narxi'}),
            'unit_type': forms.Select(attrs={'class': 'form-control'}),
            'image':     forms.FileInput(attrs={'class': 'form-control'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model  = Category
        fields = ['name']

    def __init__(self, *args, business=None, **kwargs):
        self.business = business
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        business = self.business or getattr(self.instance, 'business', None)
        qs = Category.all_objects.filter(name__iexact=name, business=business).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Bunday kategoriya allaqachon mavjud!")
        return name