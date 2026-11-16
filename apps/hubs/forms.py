from django import forms

from .models import Hub


class HubRequestForm(forms.ModelForm):
    class Meta:
        model = Hub
        fields = ["name", "category", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Uma Musume"}),
            "category": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Games, Anime, Sports"}),
            "description": forms.Textarea(attrs={
                "class": "form-control", "rows": 4,
                "placeholder": "What is this Hub about, and who is it for?",
            }),
        }
        help_texts = {
            "name": "Be specific: 'Uma Musume' or 'Pokemon Go', not 'Gaming'.",
            "category": "A broad label to help people find it (optional).",
        }

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if Hub.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError(
                "A Hub with this name already exists (or has already been requested)."
            )
        return name
