from django.contrib import admin

from .models import Interest, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "university_email", "location", "created_at")
    search_fields = ("user__username", "university_email")


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    search_fields = ("name",)
