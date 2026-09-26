import uuid
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profile
from apps.categories.models import Category
from apps.chat.models import Conversation
from apps.orders.models import Cart, CartItem, PickupSchedule
from apps.products.models import Product


User = get_user_model()


class SellerPickupFlowTests(TestCase):
    def setUp(self):
        suffix = uuid.uuid4().hex[:8]
        self.category = Category.objects.create(name=f"Books {suffix}", slug=f"books-{suffix}")

        self.seller = User.objects.create_user(email="seller@example.com", username="seller", password="StrongPass123!")
        self.buyer = User.objects.create_user(email="buyer@example.com", username="buyer", password="StrongPass123!")

        self.seller.profile.full_name = "Seller One"
        self.seller.profile.role = Profile.ROLE_SELLER
        self.seller.profile.is_email_verified = True
        self.seller.profile.is_active = True
        self.seller.profile.save()

        self.buyer.profile.full_name = "Buyer One"
        self.buyer.profile.role = Profile.ROLE_BUYER
        self.buyer.profile.is_email_verified = True
        self.buyer.profile.is_active = True
        self.buyer.profile.save()

        self.product = Product.objects.create(
            owner=self.seller,
            category=self.category,
            title="Used Chemistry Book",
            description="Good condition book",
            price=250,
            stock_quantity=2,
            location="Navrangpura",
            fulfillment_method=Product.FULFILLMENT_PICKUP,
        )
        self.conversation = Conversation.objects.create(buyer=self.buyer, seller=self.seller, product=self.product)
        self.schedule = PickupSchedule.objects.create(
            product=self.product,
            buyer=self.buyer,
            seller=self.seller,
            conversation=self.conversation,
            pickup_location="Main Market, Ahmedabad",
            pickup_date=date.today() + timedelta(days=2),
            pickup_time=time(17, 30),
            status=PickupSchedule.CONFIRMED,
            reminder_sent_at=None,
        )

    def test_category_detail_has_sell_in_category_cta_for_sellers(self):
        self.client.force_login(self.seller)
        response = self.client.get(reverse("category_detail", args=[self.category.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sell in this category")
        self.assertContains(response, f"{reverse('product_create')}?category={self.category.pk}")

    def test_reminder_action_marks_reminder_sent(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse("pickup_detail", args=[self.schedule.pk]),
            {"action": "reminder", "message": "Please remember to collect on time."},
            follow=True,
        )

        self.assertRedirects(response, reverse("pickup_detail", args=[self.schedule.pk]))
        self.schedule.refresh_from_db()
        self.assertIsNotNone(self.schedule.reminder_sent_at)
        self.assertIn("Please remember to collect on time.", self.schedule.seller_message)


class CartCheckoutTests(TestCase):
    def setUp(self):
        suffix = uuid.uuid4().hex[:8]
        self.category = Category.objects.create(name=f"Books {suffix}", slug=f"books-{suffix}")
        self.seller = User.objects.create_user(email=f"seller_{suffix}@example.com", username=f"seller_{suffix}", password="StrongPass123!")
        self.buyer = User.objects.create_user(email=f"buyer_{suffix}@example.com", username=f"buyer_{suffix}", password="StrongPass123!")

        self.seller.profile.full_name = "Seller One"
        self.seller.profile.role = Profile.ROLE_SELLER
        self.seller.profile.is_email_verified = True
        self.seller.profile.is_active = True
        self.seller.profile.save()

        self.buyer.profile.full_name = "Buyer One"
        self.buyer.profile.role = Profile.ROLE_BUYER
        self.buyer.profile.is_email_verified = True
        self.buyer.profile.is_active = True
        self.buyer.profile.save()

        self.product = Product.objects.create(
            owner=self.seller,
            category=self.category,
            title=f"Checkout Product {suffix}",
            description="Available product",
            price=199.00,
            stock_quantity=5,
            location="Ahmedabad",
            fulfillment_method=Product.FULFILLMENT_PICKUP,
            is_active=True,
        )

        self.cart = Cart.objects.create(user=self.buyer)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)

    def test_checkout_redirects_without_name_error(self):
        self.client.force_login(self.buyer)
        response = self.client.post(reverse("checkout"), {"shipping_address": "ahemdabad"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("order_confirmation"))
        self.assertTrue(self.cart.items.count() == 0)
