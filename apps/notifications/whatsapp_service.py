import hashlib
import logging
import re
from abc import ABC, abstractmethod

from django.conf import settings
from django.utils import timezone

from .models import WhatsAppNotification

logger = logging.getLogger(__name__)


def mask_phone(phone):
    digits = re.sub(r"\D", "", phone or "")
    return f"+{digits[:2]}******{digits[-2:]}" if len(digits) >= 4 else "unavailable"


class WhatsAppProvider(ABC):
    @abstractmethod
    def send(self, notification, payload):
        raise NotImplementedError


class DevelopmentWhatsAppProvider(WhatsAppProvider):
    def send(self, notification, payload):
        logger.info(
            "[WHATSAPP DEVELOPMENT MODE] recipient=%s type=%s template=%s",
            mask_phone(notification.phone_number),
            notification.notification_type,
            notification.template_name,
        )
        return {"status": WhatsAppNotification.SENT, "message_id": f"dev-{notification.pk}"}


TEMPLATES = {
    "PRODUCT_ADDED": "retiyamarket_product_added",
    "PRODUCT_APPROVED": "retiyamarket_product_approved",
    "PRODUCT_REJECTED": "retiyamarket_product_rejected",
    "ORDER_CONFIRMED": "retiyamarket_order_confirmed",
    "PAYMENT_SUCCESS": "retiyamarket_payment_success",
    "PAYMENT_FAILED": "retiyamarket_payment_failed",
    "ORDER_SHIPPED": "retiyamarket_order_shipped",
    "ORDER_DELIVERED": "retiyamarket_order_delivered",
    "ORDER_CANCELLED": "retiyamarket_order_cancelled",
    "RETURN_REQUESTED": "retiyamarket_return_requested",
    "RETURN_APPROVED": "retiyamarket_return_approved",
    "REFUND_COMPLETED": "retiyamarket_refund_completed",
}


def send_whatsapp_message(user, notification_type, payload=None, reference=None, provider=None, idempotency_suffix=""):
    payload = payload or {}
    profile = getattr(user, "profile", None)
    phone = getattr(profile, "mobile_number", "") or ""
    reference_type = reference.__class__.__name__ if reference is not None else ""
    reference_id = str(reference.pk) if reference is not None else ""
    key_source = f"{user.pk}:{notification_type}:{reference_type}:{reference_id}:{idempotency_suffix}"
    idempotency_key = hashlib.sha256(key_source.encode()).hexdigest()
    existing = WhatsAppNotification.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    status = WhatsAppNotification.PENDING
    error = ""
    if not getattr(profile, "whatsapp_opt_in", False) or not phone:
        status = WhatsAppNotification.SKIPPED
        error = "WhatsApp opt-in is disabled or no phone number is configured."

    notification = WhatsAppNotification.objects.create(
        user=user,
        phone_number=phone,
        notification_type=notification_type,
        template_name=TEMPLATES.get(notification_type, "retiyamarket_transactional"),
        reference_type=reference_type,
        reference_id=reference_id,
        idempotency_key=idempotency_key,
        status=status,
        error_message=error,
    )
    if status == WhatsAppNotification.SKIPPED:
        return notification

    try:
        result = (provider or DevelopmentWhatsAppProvider()).send(notification, payload)
        notification.status = result["status"]
        notification.provider_message_id = result["message_id"]
        notification.sent_at = timezone.now()
    except (KeyError, ValueError, RuntimeError) as exc:
        notification.status = WhatsAppNotification.FAILED
        notification.error_message = str(exc)[:255]
        logger.warning("WhatsApp notification %s failed: %s", notification.pk, exc)
    notification.save(update_fields=("status", "provider_message_id", "sent_at", "error_message", "updated_at"))
    return notification
