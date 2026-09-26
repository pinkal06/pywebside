from django import forms
from django.core.exceptions import ValidationError

from .models import Product


class ProductForm(forms.ModelForm):
    brand = forms.CharField(required=False, max_length=120, widget=forms.TextInput(attrs={"class": "form-control", "data-spec": "brand"}))
    material = forms.CharField(required=False, max_length=120, widget=forms.TextInput(attrs={"class": "form-control", "data-spec": "material"}))
    color = forms.CharField(required=False, max_length=80, widget=forms.TextInput(attrs={"class": "form-control", "data-spec": "color"}))
    size = forms.CharField(required=False, max_length=80, widget=forms.TextInput(attrs={"class": "form-control", "data-spec": "size"}))
    capacity = forms.CharField(required=False, max_length=80, widget=forms.TextInput(attrs={"class": "form-control", "data-spec": "capacity"}))
    author = forms.CharField(required=False, max_length=160, widget=forms.TextInput(attrs={"class": "form-control", "data-spec": "author"}))
    model_name = forms.CharField(required=False, max_length=120, label="Model", widget=forms.TextInput(attrs={"class": "form-control", "data-spec": "model"}))
    class Meta:
        model = Product
        fields = ("title", "category", "description", "price", "discount_percent", "stock_quantity", "condition", "location", "fulfillment_method", "image")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "discount_percent": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "100"}),
            "condition": forms.Select(attrs={"class": "form-select"}),
            "location": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Add pickup city/address or paste a Google Maps link, e.g. Ahmedabad, Navrangpura or https://maps.google.com/...",
            }),
            "image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 5 * 1024 * 1024:
            raise ValidationError("Product image must be 5MB or smaller.")
        return image

    def clean_discount_percent(self):
        discount = self.cleaned_data.get("discount_percent")
        if discount is not None and discount > 100:
            raise ValidationError("Discount cannot exceed 100%.")
        return discount

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        specs = (self.instance.specifications or {}) if self.instance and self.instance.pk else {}
        field_to_spec = {
            "brand": "brand",
            "material": "material",
            "color": "color",
            "size": "size",
            "capacity": "capacity",
            "author": "author",
            "model_name": "model",
        }
        for field_name, spec_name in field_to_spec.items():
            self.fields[field_name].initial = specs.get(spec_name, "")

    def save(self, commit=True):
        product = super().save(commit=False)
        field_to_spec = {
            "brand": "brand",
            "material": "material",
            "color": "color",
            "size": "size",
            "capacity": "capacity",
            "author": "author",
            "model_name": "model",
        }
        product.specifications = {
            spec_name: self.cleaned_data.get(field_name, "").strip()
            for field_name, spec_name in field_to_spec.items()
            if self.cleaned_data.get(field_name, "").strip()
        }
        if commit:
            product.save()
        return product
