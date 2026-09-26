import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Prefetch
from django.db import transaction
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.notifications.utils import notify
from apps.products.models import Product
from .cometchat import CometChatError, ensure_cometchat_user, generate_cometchat_auth_token
from .forms import MessageForm
from .models import Conversation, Message

logger = logging.getLogger("apps.chat.views")


def _participant_or_403(conversation, user):
    if not conversation.has_participant(user):
        raise PermissionDenied


@login_required
def conversation_list(request):
    conversations = Conversation.objects.filter(
        Q(buyer=request.user) | Q(seller=request.user)
    ).select_related("product", "buyer", "buyer__profile", "seller", "seller__profile").prefetch_related(
        Prefetch("messages", queryset=Message.objects.order_by("-created_at")[:1], to_attr="latest_messages")
    ).annotate(
        unread_count=models.Count(
            "messages",
            filter=~Q(messages__sender=request.user) & Q(messages__is_read=False),
        )
    )
    query = request.GET.get("q", "").strip()
    if query:
        conversations = conversations.filter(
            Q(product__title__icontains=query)
            | Q(buyer__profile__full_name__icontains=query)
            | Q(seller__profile__full_name__icontains=query)
        )
    return render(request, "chat/conversation_list.html", {
        "conversations": conversations, "query": query, "page_title": "Messages",
    })


@login_required
def conversation_start(request, product_id):
    product = get_object_or_404(Product.objects.select_related("owner"), pk=product_id, is_active=True)
    if product.owner_id == request.user.id:
        raise PermissionDenied
    conversation, _ = Conversation.objects.get_or_create(
        product=product, buyer=request.user, seller=product.owner,
    )
    return redirect("conversation_detail", pk=conversation.pk)


@login_required
@require_POST
def cometchat_token_view(request):
    uid = f"rm_{request.user.pk}"
    profile = getattr(request.user, "profile", None)
    display_name = (profile.full_name or request.user.email or uid).strip()

    try:
        ensure_cometchat_user(uid, display_name)
        auth_token = generate_cometchat_auth_token(uid)
    except CometChatError as exc:
        logger.exception("CometChat token generation failed for user %s", request.user.pk)
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse({
        "uid": uid,
        "authToken": auth_token,
        "name": display_name,
    })


@login_required
def conversation_detail(request, pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related(
            "product", "buyer", "buyer__profile", "seller", "seller__profile"
        ), pk=pk
    )
    _participant_or_403(conversation, request.user)
    conversation.messages.filter(
        is_read=False
    ).exclude(sender=request.user).update(is_read=True, read_at=timezone.now())
    form = MessageForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        if conversation.status != conversation.STATUS_ACTIVE:
            form.add_error(None, "This conversation is not accepting new messages.")
        else:
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            if form.cleaned_data.get("audio_file"):
                message.message_type = Message.TYPE_VOICE
                message.audio_duration = max(0, min(int(form.data.get("audio_duration", 0) or 0), 300))
            with transaction.atomic():
                message.save()
                conversation.save(update_fields=("updated_at",))
            recipient = conversation.seller if request.user.pk == conversation.buyer_id else conversation.buyer
            subject = conversation.product.title if conversation.product_id else "your conversation"
            notify(
                recipient,
                f"New message about {subject}",
                "conversation_detail",
                {"pk": conversation.pk},
            )
            return redirect("conversation_detail", pk=conversation.pk)
    messages = conversation.messages.select_related("sender")
    pickup_schedules = conversation.pickup_schedules.select_related("product", "buyer", "seller")
    subject = conversation.product.title if conversation.product_id else "General conversation"
    return render(request, "chat/conversation_detail.html", {
        "conversation": conversation, "chat_messages": messages, "form": form,
        "pickup_schedules": pickup_schedules,
        "quick_suggestions": [
            "Is this available?", "What is the final price?", "Where is pickup?",
            "When can I come?", "Can you deliver?", "Can you send more photos?",
        ],
        "page_title": f"Chat: {subject}",
    })
