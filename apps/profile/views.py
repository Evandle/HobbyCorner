from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import ProfileEditForm
from .models import Profile


@login_required(login_url="login:login")
def profile_view(request):
    profile = Profile.get_or_create_for(request.user)

    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile:profile")
    else:
        form = ProfileEditForm(instance=profile, user=request.user)

    return render(request, "profile/profile.html", {"form": form, "profile": profile})
