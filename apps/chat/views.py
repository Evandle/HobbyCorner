from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.hubs.models import Hub, HubMembership

from .forms import MessageForm
from .models import Message

MESSAGES_SHOWN = 200
LARGEST_ID = 2**63 - 1  # the biggest id the database can hold


def _chat_hub(hub_id):
    # Only approved Hubs have a chat.
    return get_object_or_404(Hub, pk=hub_id, status=Hub.Status.APPROVED)


def _is_member(user, hub):
    return HubMembership.objects.filter(user=user, hub=hub).exists()


@login_required(login_url="login:login")
def room(request, hub_id):
    hub = _chat_hub(hub_id)
    if not _is_member(request.user, hub):
        messages.info(request, f"Join {hub.name} to see its chat.")
        return redirect("hubs:detail", hub_id=hub.id)

    if request.method == "POST":
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.hub = hub
            message.sender = request.user
            message.save()
            return redirect(reverse("chat:room", args=[hub.id]) + "#latest")
    else:
        form = MessageForm()

    newest = hub.messages.recent().select_related("sender").order_by("-id")[:MESSAGES_SHOWN]
    chat_messages = list(newest)[::-1]  # oldest first, like a conversation
    return render(request, "chat/room.html", {
        "hub": hub,
        "form": form,
        "chat_messages": chat_messages,
        "last_id": chat_messages[-1].id if chat_messages else 0,
    })


@login_required(login_url="login:login")
@require_POST
def delete_message(request, hub_id, message_id):
    hub = _chat_hub(hub_id)
    if not _is_member(request.user, hub):
        raise PermissionDenied
    # Only your own messages: anyone else's is simply "not found".
    message = get_object_or_404(Message, pk=message_id, hub=hub, sender=request.user)
    if message.image:
        message.image.delete(save=False)  # remove the file from disk too
    message.delete()
    messages.info(request, "Message deleted.")
    return redirect("chat:room", hub_id=hub.id)


@login_required(login_url="login:login")
@require_GET
@never_cache
def poll(request, hub_id):
    """New messages after ?after=<id>, as ready-made HTML, for the live updates."""
    hub = _chat_hub(hub_id)
    if not _is_member(request.user, hub):
        raise PermissionDenied
    try:
        after = int(request.GET.get("after", "0"))
    except ValueError:
        after = -1
    if not 0 <= after <= LARGEST_ID:
        return JsonResponse({"error": "after must be a whole number"}, status=400)

    # Oldest first, in batches: if more than MESSAGES_SHOWN are waiting, the
    # next poll (from the new last_id) picks up the rest, so none are skipped.
    new = list(
        hub.messages.recent().filter(id__gt=after).select_related("sender").order_by("id")[:MESSAGES_SHOWN]
    )
    html = "".join(
        render_to_string("chat/_message.html", {"message": message, "hub": hub}, request=request)
        for message in new
    )
    return JsonResponse({"html": html, "last_id": new[-1].id if new else after, "count": len(new)})
