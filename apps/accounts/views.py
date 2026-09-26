from datetime import datetime, timedelta, timezone as datetime_timezone

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import activate
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.db.models import Count, Sum

from .forms import (
    CustomPasswordChangeForm,
    EmailForm,
    LoginForm,
    ProfileUpdateForm,
    ResetPasswordForm,
    UserRegistrationForm,
)
from .models import Profile
from .tokens import email_verification_token
from apps.notifications.models import Notification
from apps.orders.models import Cart, Order
from apps.products.models import Product, Wishlist


def _role_required(request, role):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != role or not profile.is_active:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied


@login_required
def buyer_dashboard_view(request):
    _role_required(request, Profile.ROLE_BUYER)
    orders = Order.objects.filter(buyer=request.user).select_related("product", "seller")
    cart = Cart.objects.filter(user=request.user).first()
    context = {
        "page_title": "Buyer Dashboard",
        "orders": orders,
        "recent_orders": orders[:5],
        "recent_wishlist": Wishlist.objects.filter(user=request.user).select_related("product", "product__category")[:5],
        "notifications": Notification.objects.filter(user=request.user).order_by("-created_at")[:5],
        "total_orders": orders.count(),
        "pending_orders": orders.filter(status__in=[Order.PENDING, Order.CONFIRMED, Order.PROCESSING, Order.SHIPPED]).count(),
        "completed_orders": orders.filter(status__in=[Order.DELIVERED, Order.COMPLETED]).count(),
        "wishlist_count": Wishlist.objects.filter(user=request.user).count(),
        "cart_count": cart.items.count() if cart else 0,
        "total_spent": orders.exclude(status=Order.CANCELLED).aggregate(total=Sum("total_price"))["total"] or 0,
    }
    return render(request, "accounts/buyer_dashboard.html", context)


@login_required
def seller_dashboard_view(request):
    _role_required(request, Profile.ROLE_SELLER)
    products = Product.objects.filter(owner=request.user)
    orders = Order.objects.filter(seller=request.user).select_related("product", "buyer")
    eligible = orders.exclude(status__in=[Order.CANCELLED, Order.REJECTED])
    context = {
        "page_title": "Seller Dashboard",
        "total_products": products.count(),
        "active_products": products.filter(is_active=True, status=Product.STATUS_ACTIVE).count(),
        "pending_products": products.filter(status=Product.STATUS_PENDING).count(),
        "sold_out_products": products.filter(stock_quantity=0).count(),
        "total_orders": orders.count(),
        "pending_orders": orders.filter(status__in=[Order.PENDING, Order.CONFIRMED, Order.PROCESSING]).count(),
        "completed_orders": orders.filter(status__in=[Order.DELIVERED, Order.COMPLETED]).count(),
        "total_sales": eligible.aggregate(total=Sum("total_price"))["total"] or 0,
        "recent_orders": orders[:5],
        "recent_products": products.select_related("category")[:5],
        "notifications": Notification.objects.filter(user=request.user).order_by("-created_at")[:5],
    }
    return render(request, "accounts/seller_dashboard.html", context)


@login_required
def seller_analytics_view(request):
    _role_required(request, Profile.ROLE_SELLER)
    orders = Order.objects.filter(seller=request.user).exclude(status__in=[Order.CANCELLED, Order.REJECTED])
    top_products = orders.values("product__title").annotate(
        units=Sum("quantity"), revenue=Sum("total_price")
    ).order_by("-units")[:10]
    context = {
        "page_title": "Seller Analytics",
        "total_sales": orders.aggregate(total=Sum("total_price"))["total"] or 0,
        "total_orders": orders.count(),
        "average_order_value": orders.aggregate(value=Sum("total_price"))["value"] or 0,
        "products_sold": orders.aggregate(units=Sum("quantity"))["units"] or 0,
        "top_products": top_products,
    }
    return render(request, "accounts/seller_analytics.html", context)


def _increment_login_failures(request):
    attempts = request.session.get('login_attempts', 0) + 1
    request.session['login_attempts'] = attempts
    if attempts >= 5:
        request.session['login_lock_until'] = (timezone.now() + timedelta(minutes=15)).timestamp()
        request.session['login_attempts'] = 5


def _is_login_locked(request):
    lock_until = request.session.get('login_lock_until')
    if not lock_until:
        return False
    if timezone.now() >= datetime.fromtimestamp(lock_until, tz=datetime_timezone.utc):
        request.session.pop('login_lock_until', None)
        request.session['login_attempts'] = 0
        return False
    return True


def _lockout_message(attempts):
    remaining = max(0, 5 - attempts)
    if remaining <= 0:
        return 'Too many failed login attempts. Please try again later.'
    return f'Invalid email or password. {remaining} attempt(s) remaining.'


def _send_verification_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    verification_url = request.build_absolute_uri(reverse('verify_email', args=[uid, token]))
    subject = 'Verify your RetiyaMarket account'
    body = render_to_string('accounts/email_verification_message.txt', {'user': user, 'verification_url': verification_url})
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def _send_password_reset_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = request.build_absolute_uri(reverse('password_reset', args=[uid, token]))
    subject = 'Reset your RetiyaMarket password'
    body = render_to_string('accounts/password_reset_message.txt', {'user': user, 'reset_url': reset_url})
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            user.profile.is_email_verified = False
            user.profile.save(update_fields=['is_email_verified'])
            _send_verification_email(request, user)
            messages.success(request, 'Account created successfully. Verification email sent.')
            return redirect('verification_sent')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form, 'page_title': 'Create an account'})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if _is_login_locked(request):
        messages.error(request, 'Too many failed login attempts. Please try again later.')
        return render(request, 'accounts/login.html', {'form': LoginForm(), 'page_title': 'Login'})

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            profile = getattr(user, 'profile', None)
            if not user.is_active or (profile and not profile.is_active):
                messages.error(request, 'Your account is currently inactive. Please contact support.')
                return redirect('account_deactivated')
            if profile and not profile.is_email_verified:
                messages.warning(request, 'Your email address is not verified. Please verify your email before logging in.')
                return redirect('verification_sent')
            login(request, user)
            activate(profile.preferred_language if profile else 'en')
            request.session['login_attempts'] = 0
            request.session.pop('login_lock_until', None)
            messages.success(request, f'Logged in successfully. Welcome back, {profile.full_name or user.email}.')
            return redirect('profile')

        _increment_login_failures(request)
        if request.session.get('login_attempts', 0) >= 5:
            messages.error(request, 'Too many failed login attempts. Please try again later.')
        else:
            messages.error(request, _lockout_message(request.session.get('login_attempts', 0)))
        form = LoginForm()
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form, 'page_title': 'Login'})


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('home')


def verification_sent_view(request):
    return render(request, 'accounts/verification_sent.html', {'page_title': 'Verification sent'})


def resend_verification_view(request):
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            user = get_user_model().objects.filter(email__iexact=email).first()
            if user and getattr(user.profile, 'is_email_verified', False) is False:
                _send_verification_email(request, user)
            messages.success(request, 'If an account exists and is unverified, a new verification email has been sent.')
            return redirect('verification_sent')
    else:
        form = EmailForm()
    return render(request, 'accounts/verification_sent.html', {'form': form, 'page_title': 'Resend verification email'})


def verify_email_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None

    if user is not None and email_verification_token.check_token(user, token):
        profile = getattr(user, 'profile', None)
        if profile:
            profile.is_email_verified = True
            profile.save(update_fields=['is_email_verified'])
        messages.success(request, 'Email verified successfully. You can now log in.')
        return render(request, 'accounts/verify_email.html', {'verified': True, 'page_title': 'Email verified'})

    messages.error(request, 'This verification link is invalid or has expired.')
    return render(request, 'accounts/verify_email.html', {'verified': False, 'page_title': 'Verification failed'})


def forgot_password_view(request):
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            user = get_user_model().objects.filter(email__iexact=email).first()
            if user:
                _send_password_reset_email(request, user)
            messages.success(request, 'If an account exists for that email, a password reset link has been sent.')
            return redirect('forgot_password')
    else:
        form = EmailForm()
    return render(request, 'accounts/forgot_password.html', {'form': form, 'page_title': 'Forgot password'})


def password_reset_confirm_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None

    valid_token = user is not None and default_token_generator.check_token(user, token)
    if not valid_token:
        messages.error(request, 'This password reset link is invalid or has expired.')
        return render(request, 'accounts/password_reset.html', {'validlink': False, 'page_title': 'Password reset'})

    if request.method == 'POST':
        form = ResetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Password changed successfully.')
            return redirect('password_reset_done')
    else:
        form = ResetPasswordForm(user)

    return render(request, 'accounts/password_reset.html', {'form': form, 'validlink': True, 'page_title': 'Set a new password'})


def password_reset_done_view(request):
    return render(request, 'accounts/password_reset_done.html', {'page_title': 'Password reset complete'})


def password_reset_complete_view(request):
    return redirect('login')


@login_required
def profile_view(request):
    profile = request.user.profile
    completion_fields = [
        profile.full_name,
        profile.mobile_number,
        profile.college,
        profile.department,
        profile.semester,
        profile.student_id,
        profile.city,
        profile.state,
        profile.profile_photo,
    ]
    completed = sum(1 for value in completion_fields if value and str(value).strip())
    profile_completion = int((completed / len(completion_fields)) * 100)
    context = {
        'profile': profile,
        'page_title': 'My profile',
        'profile_completion': profile_completion,
        'meta_description': 'View and manage your personal account details.',
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save()
            request.user.first_name = profile.full_name.split()[0]
            request.user.last_name = ' '.join(profile.full_name.split()[1:])
            request.user.save(update_fields=['first_name', 'last_name'])
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)

    return render(request, 'accounts/edit_profile.html', {'form': form, 'page_title': 'Edit profile'})


@login_required
def notification_settings_view(request):
    profile = request.user.profile
    if request.method == "POST":
        profile.whatsapp_opt_in = request.POST.get("whatsapp_opt_in") == "on"
        profile.save(update_fields=["whatsapp_opt_in"])
        messages.success(request, "Notification settings updated.")
        return redirect("notification_settings")
    return render(request, "accounts/notification_settings.html", {
        "profile": profile,
        "page_title": "Notification settings",
    })


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('profile')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form, 'page_title': 'Change password'})


@login_required
def deactivate_account_view(request):
    if request.method == 'POST':
        user = request.user
        profile = getattr(user, 'profile', None)
        if profile:
            profile.is_active = False
            profile.save(update_fields=['is_active'])
        user.is_active = False
        user.save(update_fields=['is_active'])
        logout(request)
        messages.info(request, 'Your account has been deactivated.')
        return redirect('account_deactivated')

    return render(request, 'accounts/deactivate_account.html', {'page_title': 'Deactivate account'})


def account_deactivated_view(request):
    return render(request, 'accounts/account_deactivated.html', {'page_title': 'Account deactivated'})
