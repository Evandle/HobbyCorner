from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render

from apps.hubs.models import Hub

from .forms import ProfileEditForm
from .models import Interest, Profile

SUGGESTED_INTERESTS = 12


@login_required(login_url="login:login")
def profile_view(request):
    profile = Profile.get_or_create_for(request.user)

    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile:profile")
    else:
        form = ProfileEditForm(instance=profile)

    # A failed form has already changed `profile` in memory, so the summary on
    # the left is read fresh from the database.
    shown = Profile.objects.select_related("location").get(pk=profile.pk)
    return render(request, "profile/profile.html", {
        "form": form,
        "profile": shown,
        "interests": list(shown.interests.all()),
        # Read-only view of the Hubs feature, as the dashboard does.
        "joined_hubs": request.user.joined_hubs.filter(status=Hub.Status.APPROVED).order_by("name"),
        "popular_interests": Interest.objects.annotate(
            followers=Count("profile_interests")
        ).order_by("-followers", "name")[:SUGGESTED_INTERESTS],
    })
