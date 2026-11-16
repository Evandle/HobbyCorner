from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import UserSettingsForm
from .models import UserSettings


@login_required(login_url="login:login")
def settings_view(request):
    settings_obj = UserSettings.get_or_create_for(request.user)

    if request.method == "POST":
        form = UserSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved.")
            return redirect("user_settings:settings")
    else:
        form = UserSettingsForm(instance=settings_obj)

    return render(request, "user_settings/settings.html", {"form": form})
