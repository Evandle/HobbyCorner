from django import forms

from .models import Profile


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name", "bio", "profile_image", "university_email", "interests"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Your full name"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Tell us about yourself"}),
            "profile_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "university_email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "firstname.lastname@cit.edu"}),
            "interests": forms.TextInput(attrs={"class": "form-control", "placeholder": "Pokemon Go, Uma Musume, Cosplay"}),
        }
        help_texts = {
            "interests": "Comma-separated list of your niche interests.",
            "university_email": "Use your official university email address.",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_university_email(self):
        email = self.cleaned_data["university_email"]
        qs = Profile.objects.filter(university_email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An account with this university email already exists.")
        return email
