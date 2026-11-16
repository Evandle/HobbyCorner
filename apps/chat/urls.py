from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("<int:hub_id>/", views.room, name="room"),
    path("<int:hub_id>/poll/", views.poll, name="poll"),
    path("<int:hub_id>/messages/<int:message_id>/delete/", views.delete_message, name="delete"),
]
