from django.contrib.auth.models import User
from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.chat.models import Message
from apps.hubs.models import Hub, HubMembership


class DashboardJoinedHubsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("member")
        self.owner = User.objects.create_user("owner")
        self.client.force_login(self.user)

    def make_hub(self, name, status=Hub.Status.APPROVED):
        return Hub.objects.create(name=name, status=status, requested_by=self.owner)

    def joined_names(self):
        response = self.client.get(reverse("home:home"))
        return [hub.name for hub in response.context["joined_hubs"]]

    def test_dashboard_lists_the_hubs_the_user_joined_alphabetically(self):
        for name in ("Uma Musume", "Cosplay Crafts"):
            HubMembership.objects.create(user=self.user, hub=self.make_hub(name))
        self.make_hub("Not Joined")
        self.assertEqual(self.joined_names(), ["Cosplay Crafts", "Uma Musume"])

    def test_dashboard_hides_hubs_that_are_not_approved(self):
        pending = self.make_hub("Pending Hub", status=Hub.Status.PENDING)
        HubMembership.objects.create(user=self.user, hub=pending)
        self.assertEqual(self.joined_names(), [])

    def test_dashboard_with_no_hubs_points_to_the_hub_list(self):
        response = self.client.get(reverse("home:home"))
        self.assertContains(response, reverse("hubs:list"))


class DashboardInterestsTests(TestCase):
    def test_dashboard_shows_the_interests_from_the_profile(self):
        from apps.profile.models import Interest, Profile

        user = User.objects.create_user("member")
        profile = Profile.objects.create(user=user, university_email="member@example.com")
        profile.interests.add(Interest.objects.create(name="Cosplay"))
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse("home:home")), "Cosplay")


class DashboardActivityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("member")
        self.other = User.objects.create_user("other")
        self.client.force_login(self.user)

    def hub(self, name, joined=True):
        hub = Hub.objects.create(name=name, requested_by=self.other, status=Hub.Status.APPROVED)
        if joined:
            HubMembership.objects.create(user=self.user, hub=hub)
        return hub

    def talk(self, hub, text, hours_ago=0):
        message = Message.objects.create(hub=hub, sender=self.other, content=text)
        if hours_ago:
            Message.objects.filter(pk=message.pk).update(created_at=timezone.now() - timedelta(hours=hours_ago))

    def counts(self):
        response = self.client.get(reverse("home:home"))
        return {hub.name: hub.recent_messages for hub in response.context["joined_hubs"]}

    def test_counts_are_messages_from_the_last_24_hours_in_hubs_you_joined(self):
        uma, pogo, away = self.hub("Uma Musume"), self.hub("Pokemon Go"), self.hub("Not Joined", joined=False)
        for n in range(3):
            self.talk(uma, f"fresh {n}", hours_ago=n)
        self.talk(uma, "yesterday", hours_ago=30)
        self.talk(away, "elsewhere")
        self.assertEqual(self.counts(), {"Pokemon Go": 0, "Uma Musume": 3})

    def test_the_card_lists_only_active_hubs_with_a_link_to_their_chat(self):
        uma, quiet = self.hub("Uma Musume"), self.hub("Quiet Hub")
        self.talk(uma, "hello")
        page = self.client.get(reverse("home:home"))
        self.assertContains(page, "Recent Hub activity")
        self.assertContains(page, reverse("chat:room", args=[uma.id]))
        self.assertNotContains(page, reverse("chat:room", args=[quiet.id]))

    def test_with_no_activity_the_card_says_so(self):
        self.hub("Quiet Hub")
        self.assertContains(self.client.get(reverse("home:home")), "No new messages in the last 24 hours")

    def test_query_count_does_not_grow_with_the_number_of_hubs(self):
        def queries():
            with CaptureQueriesContext(connection) as captured:
                self.client.get(reverse("home:home"))
            return len(captured)

        self.client.get(reverse("home:home"))  # first visit creates the profile
        baseline = queries()
        for n in range(6):
            self.talk(self.hub(f"Hub {n}"), "hi")
        self.assertEqual(queries(), baseline)
