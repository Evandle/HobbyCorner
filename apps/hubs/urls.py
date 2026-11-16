from django.urls import path

from . import views

app_name = "hubs"

urlpatterns = [
    path("", views.hub_list, name="list"),
    path("request/", views.request_hub, name="request"),
    path("review/", views.review_requests, name="review"),
    path("<int:hub_id>/", views.hub_detail, name="detail"),
    path("<int:hub_id>/join/", views.join_hub, name="join"),
    path("<int:hub_id>/leave/", views.leave_hub, name="leave"),
    path("<int:hub_id>/approve/", views.approve_hub, name="approve"),
    path("<int:hub_id>/reject/", views.reject_hub, name="reject"),
]
