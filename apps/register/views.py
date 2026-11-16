from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect

from apps.profile.models import Profile

from .forms import RegisterForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home:home")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                # The account and its profile are created together, or not at all.
                with transaction.atomic():
                    user = form.save()
                    Profile.objects.create(
                        user=user, university_email=form.cleaned_data["university_email"]
                    )
            except IntegrityError:
                # Someone else claimed the username or email a moment ago.
                form.add_error(None, "That username or email was just taken. Please try again.")
            else:
                messages.success(request, "Account created! Please log in.")
                return redirect("login:login")
    else:
        form = RegisterForm()

    return render(request, "register/register.html", {"form": form})
