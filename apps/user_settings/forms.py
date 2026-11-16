from django import forms

from .models import UserSettings


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ["dark_mode", "email_notifications"]
        widgets = {
            "dark_mode": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "email_notifications": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
