import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.categories.models import Category
from apps.products.models import Product


class CometChatTokenAndAccessTests(TestCase):
    def setUp(self):
        suffix = uuid.uuid4().hex[:8]
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username=f"buyer_{suffix}@example.com",
            email=f"buyer_{suffix}@example.com",
            password="StrongPass123!",
        )
        self.user.profile.full_name = "Buyer User"
        self.user.profile.is_email_verified = True
        self.user.profile.is_active = True
        self.user.profile.role = "BUYER"
        self.user.profile.save()

        self.seller = self.user_model.objects.create_user(
            username=f"seller_{suffix}@example.com",
            email=f"seller_{suffix}@example.com",
            password="StrongPass123!",
        )
        self.seller.profile.full_name = "Seller User"
        self.seller.profile.is_email_verified = True
        self.seller.profile.is_active = True
        self.seller.profile.role = "SELLER"
        self.seller.profile.save()

        self.category = Category.objects.create(name=f"Books {suffix}", slug=f"books-{suffix}")
        self.product = Product.objects.create(
            owner=self.seller,
            category=self.category,
            title=f"Sample Book {suffix}",
            description="A sample product.",
            price=199.00,
            stock_quantity=1,
            location="Ahmedabad",
            is_active=True,
        )

    def test_guest_cannot_request_token(self):
        response = self.client.post(reverse("cometchat_token"))
        self.assertIn(response.status_code, (302, 403))

    @patch("apps.chat.views.ensure_cometchat_user")
    @patch("apps.chat.views.generate_cometchat_auth_token")
    def test_authenticated_user_can_request_token(self, mock_token, mock_create_user):
        mock_create_user.return_value = {"uid": f"rm_{self.user.id}"}
        mock_token.return_value = "demo-token"

        self.client.force_login(self.user)
        response = self.client.post(reverse("cometchat_token"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["uid"], f"rm_{self.user.id}")
        self.assertEqual(payload["authToken"], "demo-token")
        self.assertNotIn("REST_API_KEY", payload)
        self.assertNotIn("authKey", payload)
        mock_create_user.assert_called_once_with(f"rm_{self.user.id}", "Buyer User")
        mock_token.assert_called_once_with(f"rm_{self.user.id}")

    def test_seller_cannot_chat_with_themselves(self):
        self.client.force_login(self.seller)
        response = self.client.get(reverse("conversation_start", args=[self.product.pk]))
        self.assertEqual(response.status_code, 403)

    def test_existing_user_data_remains_unchanged_by_token_request(self):
        self.client.force_login(self.user)
        before = {
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "full_name": self.user.profile.full_name,
            "role": self.user.profile.role,
        }

        with patch("apps.chat.views.ensure_cometchat_user") as mock_create_user, patch(
            "apps.chat.views.generate_cometchat_auth_token"
        ) as mock_token:
            mock_create_user.return_value = {"uid": f"rm_{self.user.id}"}
            mock_token.return_value = "demo-token"
            self.client.post(reverse("cometchat_token"))

        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.email, before["email"])
        self.assertEqual(self.user.first_name, before["first_name"])
        self.assertEqual(self.user.last_name, before["last_name"])
        self.assertEqual(self.user.profile.full_name, before["full_name"])
        self.assertEqual(self.user.profile.role, before["role"])
