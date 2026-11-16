from django.contrib import admin

from .models import Hub, HubMembership


@admin.register(Hub)
class HubAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "status", "requested_by", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "category")


@admin.register(HubMembership)
class HubMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "hub", "joined_at")
