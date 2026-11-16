from django.contrib import admin

from .models import Meetup, MeetupRSVP


@admin.register(Meetup)
class MeetupAdmin(admin.ModelAdmin):
    list_display = ("hub", "location", "scheduled_time", "created_by")


@admin.register(MeetupRSVP)
class MeetupRSVPAdmin(admin.ModelAdmin):
    list_display = ("meetup", "user", "status")
