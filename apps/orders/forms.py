from django import forms

from .models import Order, PickupSchedule, SellerAvailability


class OrderForm(forms.ModelForm):
    shipping_address = forms.CharField(
        label="Shipping address", widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"})
    )

    class Meta:
        model = Order
        fields = ("quantity", "shipping_address")
        widgets = {"quantity": forms.NumberInput(attrs={"min": 1, "value": 1})}


class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(
        label="Shipping address", max_length=500,
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
    )


class SellerAvailabilityForm(forms.ModelForm):
    class Meta:
        model = SellerAvailability
        fields = ("weekday", "start_time", "end_time", "pickup_location", "is_active")
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "pickup_location": forms.TextInput(attrs={"maxlength": 255, "placeholder": "e.g. Maninagar, Ahmedabad"}),
        }


class PickupScheduleForm(forms.ModelForm):
    class Meta:
        model = PickupSchedule
        fields = ("pickup_date", "pickup_time", "buyer_message")
        widgets = {
            "pickup_date": forms.DateInput(attrs={"type": "date"}),
            "pickup_time": forms.TimeInput(attrs={"type": "time"}),
            "buyer_message": forms.Textarea(attrs={"rows": 3, "maxlength": 1000, "placeholder": "I would like to collect this product."}),
        }
