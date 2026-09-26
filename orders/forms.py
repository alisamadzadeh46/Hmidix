from django import forms

from accounts.models import phone_validator

from .models import Order


class CheckoutForm(forms.ModelForm):
    phone = forms.CharField(label='شماره تماس', validators=[phone_validator])

    class Meta:
        model = Order
        fields = ['full_name', 'phone', 'address']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'نام و نام خانوادگی'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'آدرس کامل'}),
        }
