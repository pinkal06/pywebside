from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from config.health import health_view
from config.sitemaps import CategorySitemap, ProductSitemap
from apps.accounts.views_language import set_language

sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.marketplace.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('i18n/setlang/', set_language, name='set_language'),
    path('products/', include('apps.products.urls')),
    path('categories/', include('apps.categories.urls')),
    path('category/', include('apps.categories.urls')),
    path('orders/', include('apps.orders.urls')),
    path('chat/', include('apps.chat.urls')),
    path('messages/', include('apps.chat.urls')),
    path('api/chat/', include('apps.chat.urls_api')),
    path('notifications/', include('apps.notifications.urls')),
    path('admin-panel/', include('apps.admin_panel.urls')),
    path('seller/', include('apps.accounts.urls_dashboard')),
    path('health/', health_view, name='health'),
    path('robots.txt', TemplateView.as_view(
        template_name='robots.txt',
        content_type='text/plain',
    ), name='robots'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
