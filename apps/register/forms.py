from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# Signup now collects the university email, so Register has to look at Profile
# (to reject an email that is already taken) and create one. This is a narrow,
# one-way dependency: Profile knows nothing about Register.
from apps.profile.models import Profile
from apps.profile.validators import validate_university_email

# name -> extra HTML attributes (autofill, keyboard, spelling), per the sign-up guide
FIELD_ATTRS = {
    "first_name": {"autocomplete": "given-name", "enterkeyhint": "next", "autofocus": True},
    "last_name": {"autocomplete": "family-name", "enterkeyhint": "next"},
    "university_email": {
        "autocomplete": "email", "inputmode": "email", "enterkeyhint": "next",
        "autocapitalize": "off", "spellcheck": "false",
    },
    "username": {
        "autocomplete": "username", "enterkeyhint": "next",
        "autocapitalize": "off", "autocorrect": "off", "spellcheck": "false",
    },
    "password1": {"enterkeyhint": "next"},
    "password2": {"enterkeyhint": "done"},
}


class RegisterForm(UserCreationForm):
    # Two name boxes, not one: the ERD stores first and last name separately
    # (Name is a composite attribute), and Django's user table already has both.
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    university_email = forms.EmailField(
        label="University email",
        validators=[validate_university_email],
        help_text="Use your university email.",
    )

    field_order = ["first_name", "last_name", "university_email", "username", "password1", "password2"]

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({"class": "form-control", **FIELD_ATTRS.get(name, {})})
        # Django autofocuses the username; the first box on the page is first name.
        self.fields["username"].widget.attrs.pop("autofocus", None)
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
        email = self.cleaned_data["university_email"].strip().lower()
        if Profile.objects.filter(university_email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email
