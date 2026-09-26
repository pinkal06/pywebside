import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm
from django.core.exceptions import ValidationError

from .models import Profile

ALLOWED_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def validate_profile_photo(file):
    if not file:
        return file
    if file.size > 2 * 1024 * 1024:
        raise ValidationError('Profile photo must be 2MB or smaller.')
    extension = (file.name or '').lower()
    if not extension.endswith(ALLOWED_IMAGE_EXTENSIONS):
        raise ValidationError('Only JPG, JPEG, PNG, and WEBP images are allowed.')
    content_type = getattr(file, 'content_type', '') or ''
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError('Only JPG, JPEG, PNG, and WEBP images are allowed.')
    return file


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com', 'autocomplete': 'email'}),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password', 'autocomplete': 'current-password'}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Invalid email or password.',
        'inactive': 'Your account is inactive or deactivated. Please contact support.',
    }

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(self.error_messages['inactive'], code='inactive')
        profile = getattr(user, 'profile', None)
        if profile is not None and not profile.is_active:
            raise ValidationError(self.error_messages['inactive'], code='inactive')
        if profile is not None and not profile.is_email_verified:
            raise ValidationError('Please verify your email before logging in.', code='email_not_verified')


class UserRegistrationForm(forms.Form):
    full_name = forms.CharField(
        max_length=120,
        label='Full Name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name', 'autocomplete': 'name'}),
    )
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com', 'autocomplete': 'email'}),
    )
    mobile_number = forms.CharField(
        required=False,
        label='Mobile Number',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98765 43210', 'autocomplete': 'tel'}),
    )
    password1 = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create a strong password', 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat your password', 'autocomplete': 'new-password'}),
    )
    profile_photo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}))
    college = forms.CharField(required=False, max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    department = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    semester = forms.CharField(required=False, max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    student_id = forms.CharField(required=False, max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    city = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    state = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))

    def clean_full_name(self):
        full_name = ' '.join(self.cleaned_data.get('full_name', '').split())
        if not full_name:
            raise ValidationError('Full name is required.')
        if len(full_name) < 2:
            raise ValidationError('Please enter a valid full name.')
        return full_name

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email

    def clean_mobile_number(self):
        value = (self.cleaned_data.get('mobile_number') or '').strip()
        if not value:
            return ''
        normalized = value.replace(' ', '').replace('-', '')
        if not re.fullmatch(r'(?:\+91|91)?[6-9]\d{9}', normalized):
            raise ValidationError('Enter a valid Indian mobile number.')
        return normalized

    def clean_profile_photo(self):
        file = self.cleaned_data.get('profile_photo')
        return validate_profile_photo(file)

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password and len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long.')
        if password and not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least 1 uppercase letter.')
        if password and not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least 1 lowercase letter.')
        if password and not re.search(r'\d', password):
            raise ValidationError('Password must contain at least 1 number.')
        if password and not re.search(r'[^A-Za-z0-9]', password):
            raise ValidationError('Password must contain at least 1 special character.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user_model = get_user_model()
        email = self.cleaned_data['email'].strip().lower()
        user = user_model.objects.create_user(
            username=email,
            email=email,
            password=self.cleaned_data['password1'],
            first_name=self.cleaned_data['full_name'].split()[0],
            last_name=' '.join(self.cleaned_data['full_name'].split()[1:]),
            is_active=True,
        )

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.full_name = self.cleaned_data['full_name']
        profile.mobile_number = self.cleaned_data.get('mobile_number') or ''
        profile.college = self.cleaned_data.get('college') or ''
        profile.department = self.cleaned_data.get('department') or ''
        profile.semester = self.cleaned_data.get('semester') or ''
        profile.student_id = self.cleaned_data.get('student_id') or ''
        profile.city = self.cleaned_data.get('city') or ''
        profile.state = self.cleaned_data.get('state') or ''
        profile.role = Profile.ROLE_BUYER
        profile.is_email_verified = False
        profile.is_active = True
        if self.cleaned_data.get('profile_photo'):
            profile.profile_photo = self.cleaned_data['profile_photo']
        profile.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_photo', 'full_name', 'mobile_number', 'whatsapp_opt_in', 'preferred_language', 'college', 'department', 'semester', 'student_id', 'city', 'state']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98765 43210'}),
            'college': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'College / Institute'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}),
            'semester': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Semester'}),
            'student_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student ID'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_profile_photo(self):
        file = self.cleaned_data.get('profile_photo')
        return validate_profile_photo(file)

    def clean_full_name(self):
        full_name = ' '.join(self.cleaned_data.get('full_name', '').split())
        if not full_name:
            raise ValidationError('Full name is required.')
        return full_name

    def clean_mobile_number(self):
        value = (self.cleaned_data.get('mobile_number') or '').strip()
        if not value:
            return ''
        normalized = value.replace(' ', '').replace('-', '')
        if not re.fullmatch(r'(?:\+91|91)?[6-9]\d{9}', normalized):
            raise ValidationError('Enter a valid Indian mobile number.')
        return normalized


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current password'}),
        label='Current Password',
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password'}),
        label='New Password',
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        label='Confirm New Password',
    )


class EmailForm(forms.Form):
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com', 'autocomplete': 'email'}),
    )


class ResetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password'}),
        label='New Password',
    )
    new_password2 = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        label='Confirm New Password',
    )
