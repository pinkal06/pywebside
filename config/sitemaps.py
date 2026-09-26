from django.contrib.sitemaps import Sitemap

from apps.categories.models import Category
from apps.products.models import Product


class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Product.objects.filter(
            is_active=True,
            status=Product.STATUS_ACTIVE,
        ).select_related("owner")

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at
