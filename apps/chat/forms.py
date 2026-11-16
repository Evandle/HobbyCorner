from django import forms

from apps.shared.images import ACCEPT_PICTURES, check_picture

from .models import Message

MAX_MESSAGE_LENGTH = 500


class MessageForm(forms.ModelForm):
    content = forms.CharField(
        required=False,
        max_length=MAX_MESSAGE_LENGTH,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 2,
            "placeholder": "Write a message",
            "enterkeyhint": "send",
        }),
    )

    class Meta:
        model = Message
        fields = ["content", "image"]
        labels = {"image": "Add a picture (optional)"}
        help_texts = {"image": "JPEG, PNG, GIF or WEBP, up to 2 MB."}
        widgets = {"image": forms.FileInput(attrs={"class": "form-control", "accept": ACCEPT_PICTURES})}

    def clean_image(self):
        return check_picture(self.cleaned_data.get("image"))
