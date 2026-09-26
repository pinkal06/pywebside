from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verification-sent/', views.verification_sent_view, name='verification_sent'),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),
    path('verify-email/<uidb64>/<token>/', views.verify_email_view, name='verify_email'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('password-reset/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset'),
    path('password-reset/done/', views.password_reset_done_view, name='password_reset_done'),
    path('password-reset/complete/', views.password_reset_complete_view, name='password_reset_complete'),
    path('profile/', views.profile_view, name='profile'),
    path('dashboard/', views.buyer_dashboard_view, name='buyer_dashboard'),
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),
    path('notifications/', views.notification_settings_view, name='notification_settings'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('deactivate-account/', views.deactivate_account_view, name='deactivate_account'),
    path('account-deactivated/', views.account_deactivated_view, name='account_deactivated'),
]
