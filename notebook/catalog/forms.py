# notebook/catalog/forms.py
from django import forms
from .models import Product, Category


class ProductForm(forms.ModelForm):
    class Meta:
        model  = Product
        fields = ['name', 'category', 'price', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rasm majburiy emas — bo'sh yuborilsa xato chiqmaydi
        self.fields['image'].required = False
        widgets = {
            'name':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mahsulot nomi'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price':    forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Sotuv narxi'}),
            'image':    forms.FileInput(attrs={'class': 'form-control'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model  = Category
        fields = ['name']

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if Category.all_objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Bunday kategoriya allaqachon mavjud!")
        return name
