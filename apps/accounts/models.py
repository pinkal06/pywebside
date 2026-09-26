from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class Profile(models.Model):
    LANGUAGE_CHOICES = [('en', 'English'), ('gu', 'Gujarati'), ('hi', 'Hindi')]
    ROLE_BUYER = 'BUYER'
    ROLE_SELLER = 'SELLER'
    ROLE_ADMIN = 'ADMIN'

    ROLE_CHOICES = [
        (ROLE_BUYER, 'Buyer'),
        (ROLE_SELLER, 'Seller'),
        (ROLE_ADMIN, 'Admin'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    full_name = models.CharField(max_length=120)
    mobile_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[RegexValidator(regex=r'^(?:\+91|91)?[6-9]\d{9}$', message='Enter a valid Indian mobile number.')],
    )
    whatsapp_opt_in = models.BooleanField(default=False)
    preferred_language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
    college = models.CharField(max_length=150, blank=True)
    department = models.CharField(max_length=100, blank=True)
    semester = models.CharField(max_length=20, blank=True)
    student_id = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_BUYER)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'

    def __str__(self):
        return f'{self.full_name} ({self.user.email})'

    @property
    def is_account_active(self):
        return bool(self.user.is_active and self.is_active)
