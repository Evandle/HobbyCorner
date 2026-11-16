from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from apps.chat.models import FRESH_START_WINDOW
from apps.hubs.models import Hub
from apps.profile.models import Profile


@login_required(login_url="login:login")
def home_view(request):
    profile = Profile.get_or_create_for(request.user)
    # The dashboard gathers read-only data from other features, which is the one
    # cross-feature dependency the guide allows for a home screen.
    cutoff = timezone.now() - FRESH_START_WINDOW
    joined_hubs = list(
        request.user.joined_hubs.filter(status=Hub.Status.APPROVED)
        .annotate(recent_messages=Count("messages", filter=Q(messages__created_at__gte=cutoff)))
        .order_by("name")
    )
    context = {
        "profile": profile,
        "interests": profile.interest_list(),
        "joined_hubs": joined_hubs,
        "active_hubs": [hub for hub in joined_hubs if hub.recent_messages],
    }
    return render(request, "home/home.html", context)
