from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CategoryForm
from .models import Category
from apps.products.models import Product


def category_list(request):
    categories = Category.objects.filter(is_active=True)
    return render(request, "categories/category_list.html", {"categories": categories, "page_title": "Categories"})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = category.products.filter(is_active=True).select_related("owner", "category")
    query = request.GET.get("q", "").strip()
    condition = request.GET.get("condition", "").strip()
    sort = request.GET.get("sort", "-created_at")
    if query:
        products = products.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(owner__profile__full_name__icontains=query)
            | Q(location__icontains=query)
        )
    if condition:
        products = products.filter(condition=condition)
    if sort in {"price", "-price", "-created_at", "title"}:
        products = products.order_by(sort)
    return render(request, "categories/category_detail.html", {
        "category": category, "products": products,
        "product_conditions": Product.CONDITION_CHOICES, "page_title": category.name,
    })


def _staff_required(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(_staff_required)
def category_create(request):
    form = CategoryForm(request.POST or None)
    if form.is_valid():
        category = form.save()
        messages.success(request, "Category created.")
        return redirect(category)
    return render(request, "categories/category_form.html", {"form": form, "page_title": "Add category"})


@user_passes_test(_staff_required)
def category_update(request, slug):
    category = get_object_or_404(Category, slug=slug)
    form = CategoryForm(request.POST or None, instance=category)
    if form.is_valid():
        form.save()
        messages.success(request, "Category updated.")
        return redirect(category)
    return render(request, "categories/category_form.html", {"form": form, "page_title": "Edit category"})


@user_passes_test(_staff_required)
def category_delete(request, slug):
    category = get_object_or_404(Category, slug=slug)
    if request.method == "POST":
        try:
            category.delete()
        except ProtectedError:
            messages.error(request, "This category still has products. Reassign them before deleting it.")
            return redirect(category)
        messages.success(request, "Category deleted.")
        return redirect("category_list")
    return render(request, "categories/category_confirm_delete.html", {"category": category, "page_title": "Delete category"})
