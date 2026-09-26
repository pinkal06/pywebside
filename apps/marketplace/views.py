from django.shortcuts import render
from django.db import models
from apps.categories.models import Category
from apps.products.models import Product


def home_view(request):
    context = {
        'page_title': 'RetiyaMarket | Buy. Sell. Connect.',
        'meta_description': 'Discover products, sell faster and connect with trusted buyers and sellers across your campus and city.',
        'categories': Category.objects.filter(is_active=True).annotate(product_count=models.Count("products", filter=models.Q(products__is_active=True))),
        'latest_products': Product.objects.filter(is_active=True).select_related("category", "owner")[:8],
    }
    return render(request, 'marketplace/index.html', context)
