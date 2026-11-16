from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import HubRequestForm
from .models import Hub, HubMembership

MEMBERS_SHOWN = 20


def _require_staff(user):
    # is_staff doubles as the "moderator" flag (see the ERD note on auth_user).
    if not user.is_staff:
        raise PermissionDenied


def _redirect_back(request, fallback, **kwargs):
    """Send the user back to the page they clicked from, if that's a safe URL."""
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect(fallback, **kwargs)


@login_required(login_url="login:login")
def hub_list(request):
    query = request.GET.get("q", "").strip()
    hubs = Hub.objects.filter(status=Hub.Status.APPROVED).annotate(
        member_count=Count("memberships"),
        is_member=Exists(
            HubMembership.objects.filter(hub=OuterRef("pk"), user=request.user)
        ),
    )
    if query:
        hubs = hubs.filter(
            Q(name__icontains=query)
            | Q(category__icontains=query)
            | Q(description__icontains=query)
        )

    my_requests = (
        Hub.objects.filter(requested_by=request.user)
        .exclude(status=Hub.Status.APPROVED)
        .order_by("-created_at")
    )
    pending_review_count = (
        Hub.objects.filter(status=Hub.Status.PENDING).count()
        if request.user.is_staff else 0
    )
    return render(request, "hubs/hub_list.html", {
        "hubs": hubs,
        "query": query,
        "my_requests": my_requests,
        "pending_review_count": pending_review_count,
    })


@login_required(login_url="login:login")
def hub_detail(request, hub_id):
    hub = get_object_or_404(Hub.objects.select_related("requested_by"), pk=hub_id)
    is_owner = hub.requested_by_id == request.user.id
    if hub.status != Hub.Status.APPROVED and not (request.user.is_staff or is_owner):
        raise Http404  # unapproved Hubs are only visible to the requester and moderators

    memberships = hub.memberships.select_related("user").order_by("joined_at")
    member_count = memberships.count()
    return render(request, "hubs/hub_detail.html", {
        "hub": hub,
        "is_member": memberships.filter(user=request.user).exists(),
        "members": memberships[:MEMBERS_SHOWN],
        "member_count": member_count,
        "hidden_members": max(member_count - MEMBERS_SHOWN, 0),
    })


@login_required(login_url="login:login")
@require_POST
def join_hub(request, hub_id):
    hub = get_object_or_404(Hub, pk=hub_id, status=Hub.Status.APPROVED)
    _, created = HubMembership.objects.get_or_create(user=request.user, hub=hub)
    if created:
        messages.success(request, f"You joined {hub.name}.")
    else:
        messages.info(request, f"You're already in {hub.name}.")
    return _redirect_back(request, "hubs:detail", hub_id=hub.id)


@login_required(login_url="login:login")
@require_POST
def leave_hub(request, hub_id):
    hub = get_object_or_404(Hub, pk=hub_id)
    deleted, _ = HubMembership.objects.filter(user=request.user, hub=hub).delete()
    if deleted:
        messages.info(request, f"You left {hub.name}.")
    else:
        messages.info(request, f"You weren't in {hub.name}.")
    return _redirect_back(request, "hubs:list")


@login_required(login_url="login:login")
def request_hub(request):
    if request.method == "POST":
        form = HubRequestForm(request.POST)
        if form.is_valid():
            hub = form.save(commit=False)
            hub.requested_by = request.user
            hub.status = Hub.Status.PENDING
            hub.save()
            messages.success(
                request, f"'{hub.name}' was submitted. A moderator will review it soon."
            )
            return redirect("hubs:list")
    else:
        form = HubRequestForm()
    return render(request, "hubs/hub_request.html", {"form": form})


@login_required(login_url="login:login")
def review_requests(request):
    _require_staff(request.user)
    pending = (
        Hub.objects.filter(status=Hub.Status.PENDING)
        .select_related("requested_by")
        .order_by("created_at")
    )
    return render(request, "hubs/hub_review.html", {"pending": pending})


def _decide(request, hub_id, new_status):
    _require_staff(request.user)
    with transaction.atomic():
        # The row lock means two moderators acting on one request at the same
        # moment can't both succeed: the second one no longer finds it pending.
        hub = get_object_or_404(
            Hub.objects.select_for_update(), pk=hub_id, status=Hub.Status.PENDING
        )
        hub.status = new_status
        hub.save(update_fields=["status"])
        if new_status == Hub.Status.APPROVED:
            # The person who proposed a Hub starts out as its first member.
            HubMembership.objects.get_or_create(user_id=hub.requested_by_id, hub=hub)

    if new_status == Hub.Status.APPROVED:
        messages.success(request, f"Approved '{hub.name}'.")
    else:
        messages.info(request, f"Rejected '{hub.name}'.")
    return redirect("hubs:review")


@login_required(login_url="login:login")
@require_POST
def approve_hub(request, hub_id):
    return _decide(request, hub_id, Hub.Status.APPROVED)


@login_required(login_url="login:login")
@require_POST
def reject_hub(request, hub_id):
    return _decide(request, hub_id, Hub.Status.REJECTED)
