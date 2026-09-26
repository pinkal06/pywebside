from django import forms
from django.utils.text import slugify

from .models import Category


class CategoryForm(forms.ModelForm):
    # Slugs are derived from the category name when one is not supplied.
    slug = forms.SlugField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))

    class Meta:
        model = Category
        fields = ("name", "slug", "description", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_slug(self):
        return slugify(self.cleaned_data.get("slug") or self.cleaned_data.get("name"))
