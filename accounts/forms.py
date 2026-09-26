from django import forms
from django.contrib.auth import get_user_model, password_validation

from .models import Address, phone_validator

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        label='رمز عبور',
        min_length=6,
        widget=forms.PasswordInput(attrs={'placeholder': 'رمز عبور را وارد کنید'}),
    )

    class Meta:
        model = User
        fields = ['full_name', 'phone', 'email']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'نام و نام خانوادگی'}),
            'phone': forms.TextInput(attrs={'placeholder': 'مثال: ۰۹۱۲۳۴۵۶۷۸۹'}),
            'email': forms.EmailInput(attrs={'placeholder': 'example@gmail.com'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_password(self):
        password = self.cleaned_data['password']
        password_validation.validate_password(password)
        return password

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError('این شماره قبلاً ثبت‌نام کرده است.')
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    phone = forms.CharField(
        label='شماره تلفن',
        validators=[phone_validator],
        widget=forms.TextInput(attrs={'placeholder': 'شماره خود را وارد کنید'}),
    )
    password = forms.CharField(
        label='رمز عبور',
        widget=forms.PasswordInput(attrs={'placeholder': 'رمز عبور خود را وارد کنید'}),
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name', 'email']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'نام و نام خانوادگی'}),
            'email': forms.EmailInput(attrs={'placeholder': 'ایمیل (اختیاری)'}),
        }


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['title', 'receiver', 'phone', 'province', 'city',
                  'postal_code', 'address', 'is_default']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'مثلاً خانه'}),
            'receiver': forms.TextInput(attrs={'placeholder': 'نام گیرنده'}),
            'phone': forms.TextInput(attrs={'placeholder': '۰۹...'}),
            'province': forms.TextInput(attrs={'placeholder': 'استان'}),
            'city': forms.TextInput(attrs={'placeholder': 'شهر'}),
            'postal_code': forms.TextInput(attrs={'placeholder': 'کد پستی'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'نشانی کامل'}),
        }
