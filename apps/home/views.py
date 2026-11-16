from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.profile.models import Profile


@login_required(login_url="login:login")
def home_view(request):
    profile = Profile.get_or_create_for(request.user)
    context = {
        "profile": profile,
        "interests": profile.interest_list(),
    }
    return render(request, "home/home.html", context)
