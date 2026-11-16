from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.hubs.models import Hub, HubMembership
from apps.hubs.views import MEMBERS_SHOWN

from .base import HubTestCase


class HubListTests(HubTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.member)

    def hubs_in_context(self, **params):
        response = self.client.get(reverse("hubs:list"), params)
        return {hub.name: hub for hub in response.context["hubs"]}

    def test_only_approved_hubs_are_listed(self):
        self.make_hub("Waiting Hub", status=Hub.Status.PENDING)
        self.make_hub("Turned Down Hub", status=Hub.Status.REJECTED)
        self.assertEqual(list(self.hubs_in_context()), ["Uma Musume"])

    def test_member_count_and_membership_flag_are_per_hub(self):
        other_hub = self.make_hub("Pokemon Go")
        HubMembership.objects.create(user=self.member, hub=self.hub)
        HubMembership.objects.create(user=self.stranger, hub=self.hub)
        hubs = self.hubs_in_context()
        self.assertEqual(hubs["Uma Musume"].member_count, 2)
        self.assertTrue(hubs["Uma Musume"].is_member)
        self.assertEqual(hubs[other_hub.name].member_count, 0)
        self.assertFalse(hubs[other_hub.name].is_member)

    def test_search_matches_name_category_and_description_ignoring_case(self):
        self.make_hub("Pokemon Go", category="Mobile", description="Raid nights")
        for query, expected in (
            ("uma", ["Uma Musume"]),
            ("GAMES", ["Uma Musume"]),
            ("raid", ["Pokemon Go"]),
            ("  pokemon  ", ["Pokemon Go"]),
            ("nothing matches this", []),
        ):
            with self.subTest(query=query):
                self.assertEqual(list(self.hubs_in_context(q=query)), expected)

    def test_search_treats_special_characters_as_plain_text(self):
        for query in ("%", "_", "'; DROP TABLE hubs; --", "<script>"):
            with self.subTest(query=query):
                self.assertEqual(list(self.hubs_in_context(q=query)), [])

    def test_list_makes_the_same_number_of_queries_however_many_hubs_exist(self):
        url = reverse("hubs:list")

        def count_queries():
            with CaptureQueriesContext(connection) as queries:
                self.client.get(url)
            return len(queries)

        HubMembership.objects.create(user=self.stranger, hub=self.hub)
        queries_with_one_hub = count_queries()
        for number in range(8):
            hub = self.make_hub(f"Extra Hub {number}")
            HubMembership.objects.create(user=self.stranger, hub=hub)
            HubMembership.objects.create(user=self.member, hub=hub)
        self.assertEqual(count_queries(), queries_with_one_hub)

    def test_my_requests_shows_my_unapproved_hubs_only(self):
        self.make_hub("Mine Pending", status=Hub.Status.PENDING, requested_by=self.member)
        self.make_hub("Mine Rejected", status=Hub.Status.REJECTED, requested_by=self.member)
        self.make_hub("Theirs Pending", status=Hub.Status.PENDING, requested_by=self.stranger)
        response = self.client.get(reverse("hubs:list"))
        names = {hub.name for hub in response.context["my_requests"]}
        self.assertEqual(names, {"Mine Pending", "Mine Rejected"})


class HubDetailTests(HubTestCase):
    def test_approved_hub_is_visible_to_everyone_logged_in(self):
        self.login(self.member)
        response = self.client.get(reverse("hubs:detail", args=[self.hub.id]))
        self.assertContains(response, "Uma Musume")

    def test_unapproved_hubs_are_visible_only_to_requester_and_moderators(self):
        for status in (Hub.Status.PENDING, Hub.Status.REJECTED):
            hub = self.make_hub(f"Hub {status}", status=status, requested_by=self.member)
            url = reverse("hubs:detail", args=[hub.id])
            for user, expected in (
                (self.member, 200),
                (self.moderator, 200),
                (self.stranger, 404),
            ):
                with self.subTest(status=status, user=user.username):
                    self.login(user)
                    self.assertEqual(self.client.get(url).status_code, expected)

    def test_only_members_of_an_approved_hub_are_offered_the_chat(self):
        chat_url = reverse("chat:room", args=[self.hub.id])
        detail = reverse("hubs:detail", args=[self.hub.id])
        self.login(self.stranger)
        self.assertNotContains(self.client.get(detail), chat_url)
        HubMembership.objects.create(user=self.stranger, hub=self.hub)
        self.assertContains(self.client.get(detail), chat_url)

    def test_a_hub_that_is_not_approved_has_no_chat_link(self):
        pending = self.make_hub("Waiting Hub", status=Hub.Status.PENDING, requested_by=self.member)
        HubMembership.objects.create(user=self.member, hub=pending)
        self.login(self.member)
        page = self.client.get(reverse("hubs:detail", args=[pending.id]))
        self.assertNotContains(page, reverse("chat:room", args=[pending.id]))

    def test_missing_hub_is_a_404(self):
        self.login(self.member)
        self.assertEqual(self.client.get(reverse("hubs:detail", args=[999999])).status_code, 404)

    def test_member_list_is_capped_and_the_rest_are_counted(self):
        extra = MEMBERS_SHOWN + 5
        users = User.objects.bulk_create([User(username=f"fan{i}") for i in range(extra)])
        users = list(User.objects.filter(username__startswith="fan"))
        HubMembership.objects.bulk_create(
            [HubMembership(user=user, hub=self.hub) for user in users]
        )
        self.login(self.member)
        response = self.client.get(reverse("hubs:detail", args=[self.hub.id]))
        self.assertEqual(response.context["member_count"], extra)
        self.assertEqual(len(response.context["members"]), MEMBERS_SHOWN)
        self.assertEqual(response.context["hidden_members"], 5)
