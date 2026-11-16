from django import forms
from django.conf import settings
from django.db import transaction

from apps.shared.images import ACCEPT_PICTURES, check_picture

from .models import Interest, Profile

MAX_INTERESTS = 10
MAX_INTEREST_LENGTH = 100  # matches Interest.name


class ProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "family-name"}),
    )
    interest_names = forms.CharField(
        label="Interests",
        required=False,
        max_length=1100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Pokemon Go, Uma Musume, Cosplay",
            "autocapitalize": "words",
            "spellcheck": "false",
        }),
        help_text=f"Separate with commas, up to {MAX_INTERESTS}.",
    )

    field_order = [
        "first_name", "last_name", "university_email", "location",
        "interest_names", "bio", "profile_image",
    ]

    class Meta:
        model = Profile
        fields = ["university_email", "location", "bio", "profile_image"]
        labels = {"university_email": "University email", "profile_image": "Profile photo"}
        widgets = {
            "university_email": forms.EmailInput(attrs={
                "class": "form-control", "autocomplete": "email", "inputmode": "email",
                "autocapitalize": "off", "spellcheck": "false",
            }),
            "location": forms.Select(attrs={"class": "form-select"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Tell us about yourself"}),
            "profile_image": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": ACCEPT_PICTURES,
            }),
        }
        help_texts = {"profile_image": "JPEG, PNG, GIF or WEBP, up to 2 MB."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.initial.setdefault("first_name", user.first_name)
        self.initial.setdefault("last_name", user.last_name)
        self.initial.setdefault("interest_names", ", ".join(self.instance.interest_list()))
        self.fields["location"].empty_label = "Not set"
        domains = getattr(settings, "UNIVERSITY_EMAIL_DOMAINS", [])
        if domains:
            self.fields["university_email"].help_text = (
                "Must be a " + " or ".join(f"@{d}" for d in domains) + " address."
            )

    def clean_first_name(self):
        return " ".join(self.cleaned_data["first_name"].split())

    def clean_last_name(self):
        return " ".join(self.cleaned_data["last_name"].split())

    def clean_university_email(self):
        return self.cleaned_data["university_email"].strip().lower()

    def clean_interest_names(self):
        names, seen = [], set()
        for piece in self.cleaned_data["interest_names"].split(","):
            name = " ".join(piece.split())
            if not name or name.lower() in seen:
                continue
            if len(name) > MAX_INTEREST_LENGTH:
                raise forms.ValidationError(
                    f"Each interest must be {MAX_INTEREST_LENGTH} characters or fewer."
                )
            seen.add(name.lower())
            names.append(name)
        if len(names) > MAX_INTERESTS:
            raise forms.ValidationError(f"Please list at most {MAX_INTERESTS} interests.")
        return names

    def clean_profile_image(self):
        return check_picture(self.cleaned_data.get("profile_image"))

    def save(self, commit=True):
        # Always saves: name, profile and interest changes belong together.
        profile = super().save(commit=False)
        with transaction.atomic():
            user = profile.user
            user.first_name = self.cleaned_data["first_name"]
            user.last_name = self.cleaned_data["last_name"]
            user.save(update_fields=["first_name", "last_name"])
            profile.save()
            self._save_interests(profile)
        return profile

    def _save_interests(self, profile):
        chosen = []
        for name in self.cleaned_data["interest_names"]:
            interest = Interest.objects.filter(name__iexact=name).first()
            chosen.append(interest or Interest.objects.create(name=name))
        profile.interests.set(chosen)
