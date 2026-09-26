from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import Profile
from apps.categories.models import Category
from apps.chat.models import Conversation, Message, MessageReport
from apps.orders.models import Order
from apps.products.models import Product, ProductReport
from .models import AuditLog, SecurityLog

User = get_user_model()


class AdminPanelSecurityAndManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin User
        self.admin_user = User.objects.create_superuser(
            username="admin@retiyabazar.com",
            email="admin@retiyabazar.com",
            password="AdminPassword123!",
        )
        Profile.objects.filter(user=self.admin_user).update(
            role=Profile.ROLE_ADMIN, is_email_verified=True, is_active=True
        )

        # Buyer User
        self.buyer_user = User.objects.create_user(
            username="buyer@retiyabazar.com",
            email="buyer@retiyabazar.com",
            password="BuyerPassword123!",
        )
        Profile.objects.filter(user=self.buyer_user).update(
            role=Profile.ROLE_BUYER, is_email_verified=True, is_active=True
        )

        # Seller User
        self.seller_user = User.objects.create_user(
            username="seller@retiyabazar.com",
            email="seller@retiyabazar.com",
            password="SellerPassword123!",
        )
        Profile.objects.filter(user=self.seller_user).update(
            role=Profile.ROLE_SELLER, is_email_verified=True, is_active=True
        )

        # Category
        self.category = Category.objects.create(
            name="Books & Study Material",
            slug="books-study-material",
            description="Academic textbooks and notes",
            is_active=True,
        )

        # Product
        self.product = Product.objects.create(
            owner=self.seller_user,
            category=self.category,
            title="Data Structures & Algorithms in Python",
            description="Excellent condition university textbook",
            price=450.00,
            stock_quantity=2,
            condition="like_new",
            status=Product.STATUS_PENDING,
            is_active=False,
        )

        # Order
        self.order = Order.objects.create(
            product=self.product,
            buyer=self.buyer_user,
            seller=self.seller_user,
            quantity=1,
            total_price=450.00,
            status=Order.PENDING,
            shipping_address="Room 204, Campus Hostel A",
        )

    # 1. SECURITY & PERMISSION TESTS
    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get(reverse("admin_panel:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_buyer_forbidden_from_admin_panel(self):
        self.client.login(username="buyer@retiyabazar.com", password="BuyerPassword123!")
        response = self.client.get(reverse("admin_panel:dashboard"))
        self.assertEqual(response.status_code, 403)

        # Verify SecurityLog created
        self.assertTrue(
            SecurityLog.objects.filter(
                user=self.buyer_user, event_type="UNAUTHORIZED_ADMIN_ACCESS"
            ).exists()
        )

    def test_seller_forbidden_from_admin_panel(self):
        self.client.login(username="seller@retiyabazar.com", password="SellerPassword123!")
        response = self.client.get(reverse("admin_panel:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_dashboard(self):
        self.client.login(username="admin@retiyabazar.com", password="AdminPassword123!")
        response = self.client.get(reverse("admin_panel:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Dashboard")

    # 2. USER MANAGEMENT & SUPER ADMIN PROTECTION
    def test_admin_can_deactivate_and_activate_user(self):
        self.client.login(username="admin@retiyabazar.com", password="AdminPassword123!")

        # Deactivate buyer
        response = self.client.post(reverse("admin_panel:user_toggle_status", kwargs={"pk": self.buyer_user.pk}))
        self.assertEqual(response.status_code, 302)
        self.buyer_user.refresh_from_db()
        self.assertFalse(self.buyer_user.is_active)
        self.assertFalse(self.buyer_user.profile.is_active)

        # Verify AuditLog created
        self.assertTrue(AuditLog.objects.filter(action="USER_DEACTIVATED", object_id=str(self.buyer_user.pk)).exists())

        # Reactivate buyer
        response = self.client.post(reverse("admin_panel:user_toggle_status", kwargs={"pk": self.buyer_user.pk}))
        self.assertEqual(response.status_code, 302)
        self.buyer_user.refresh_from_db()
        self.assertTrue(self.buyer_user.is_active)

    def test_super_admin_deactivation_protection(self):
        self.client.login(username="admin@retiyabazar.com", password="AdminPassword123!")
        # Attempt to deactivate the only active superuser
        response = self.client.post(reverse("admin_panel:user_toggle_status", kwargs={"pk": self.admin_user.pk}))
        self.assertEqual(response.status_code, 302)
        self.admin_user.refresh_from_db()
        # Must remain active
        self.assertTrue(self.admin_user.is_active)

    # 3. PRODUCT APPROVAL & REJECTION
    def test_admin_can_approve_product(self):
        self.client.login(username="admin@retiyabazar.com", password="AdminPassword123!")
        response = self.client.post(reverse("admin_panel:product_approve", kwargs={"pk": self.product.pk}))
        self.assertEqual(response.status_code, 302)

        self.product.refresh_from_db()
        self.assertEqual(self.product.status, Product.STATUS_ACTIVE)
        self.assertTrue(self.product.is_active)

        # AuditLog verified
        self.assertTrue(AuditLog.objects.filter(action="PRODUCT_APPROVED", object_id=str(self.product.pk)).exists())

    def test_admin_can_reject_product_with_reason(self):
        self.client.login(username="admin@retiyabazar.com", password="AdminPassword123!")
        reason_text = "Missing clear picture of the textbook spine."
        response = self.client.post(
            reverse("admin_panel:product_reject", kwargs={"pk": self.product.pk}),
            {"reason": reason_text},
        )
        self.assertEqual(response.status_code, 302)

        self.product.refresh_from_db()
        self.assertEqual(self.product.status, Product.STATUS_REJECTED)
        self.assertFalse(self.product.is_active)
        self.assertEqual(self.product.rejection_reason, reason_text)

        # AuditLog verified
        self.assertTrue(AuditLog.objects.filter(action="PRODUCT_REJECTED", object_id=str(self.product.pk)).exists())

    # 4. CATEGORY MANAGEMENT & DELETE PROTECTION
    def test_category_delete_protection_with_existing_products(self):
        self.client.login(username="admin@retiyabazar.com", password="AdminPassword123!")
        # Category contains self.product, so delete must be blocked
        response = self.client.post(reverse("admin_panel:category_delete", kwargs={"slug": self.category.slug}))
        self.assertEqual(response.status_code, 302)
        # Category should still exist
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_category_create_and_empty_delete(self):
        self.client.login(username="admin@retiyabazar.com", password="AdminPassword123!")
        # Create new category
        response = self.client.post(
            reverse("admin_panel:category_create"),
            {"name": "Electronics & Gadgets", "slug": "electronics-gadgets", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 302)
        new_cat = Category.objects.get(slug="electronics-gadgets")

        # Delete empty category
        del_response = self.client.post(reverse("admin_panel:category_delete", kwargs={"slug": new_cat.slug}))
        self.assertEqual(del_response.status_code, 302)
        self.assertFalse(Category.objects.filter(slug="electronics-gadgets").exists())

    # 5. ORDER STATUS WORKFLOW
    def test_valid_order_status_transition(self):
        self.client.login(username="admin@retiyabazar.com", password="AdminPassword123!")
        # PENDING -> CONFIRMED is valid
        response = self.client.post(
            reverse("admin_panel:order_status_update", kwargs={"pk": self.order.pk}),
            {"status": Order.CONFIRMED},
        )
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.CONFIRMED)

    def test_invalid_order_status_transition_blocked(self):
        self.client.login(username="admin@retiyabazar.com", password="AdminPassword123!")
        # PENDING -> DELIVERED directly is invalid
        response = self.client.post(
            reverse("admin_panel:order_status_update", kwargs={"pk": self.order.pk}),
            {"status": Order.DELIVERED},
        )
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        # Must still be PENDING
        self.assertEqual(self.order.status, Order.PENDING)

    # 6. REPORT MODERATION
    def test_moderation_product_report_status_update(self):
        self.client.login(username="admin@retiyabazar.com", password="AdminPassword123!")
        report = ProductReport.objects.create(
            product=self.product,
            reported_by=self.buyer_user,
            reason="fake",
            description="Suspected non-original edition",
            status="open",
        )
        response = self.client.post(
            reverse("admin_panel:product_report_update_status", kwargs={"pk": report.pk}),
            {"status": "resolved"},
        )
        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, "resolved")
