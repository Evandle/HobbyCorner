from django.urls import reverse

from apps.hubs.models import Hub, HubMembership

from .base import HubTestCase


class RequestHubTests(HubTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.member)
        self.url = reverse("hubs:request")

    def submit(self, **fields):
        return self.client.post(self.url, {"name": "Cosplay Crafts", **fields})

    def test_a_valid_request_is_saved_as_pending_and_owned_by_the_requester(self):
        response = self.submit(category="Arts", description="Share builds")
        self.assertRedirects(response, reverse("hubs:list"), fetch_redirect_response=False)
        hub = Hub.objects.get(name="Cosplay Crafts")
        self.assertEqual(hub.status, Hub.Status.PENDING)
        self.assertEqual(hub.requested_by, self.member)
        self.assertFalse(hub.memberships.exists())

    def test_the_form_cannot_be_used_to_set_status_or_owner(self):
        self.submit(status="approved", requested_by=self.moderator.id)
        hub = Hub.objects.get(name="Cosplay Crafts")
        self.assertEqual(hub.status, Hub.Status.PENDING)
        self.assertEqual(hub.requested_by, self.member)

    def test_duplicate_names_are_rejected_ignoring_case_and_extra_spaces(self):
        self.make_hub("Waiting Hub", status=Hub.Status.PENDING)
        before = Hub.objects.count()
        for name in ("uma musume", "  UMA   Musume ", "waiting hub"):
            with self.subTest(name=name):
                response = self.submit(name=name)
                self.assertEqual(response.status_code, 200)
                self.assertIn("name", response.context["form"].errors)
        self.assertEqual(Hub.objects.count(), before)

    def test_blank_and_oversized_names_are_rejected(self):
        for name in ("", "   ", "x" * 101):
            with self.subTest(name_length=len(name)):
                response = self.submit(name=name)
                self.assertEqual(response.status_code, 200)
                self.assertIn("name", response.context["form"].errors)
        self.assertFalse(Hub.objects.filter(requested_by=self.member).exists())

    def test_extra_spaces_inside_a_name_are_tidied(self):
        self.submit(name="  Pokemon    Go  ")
        self.assertTrue(Hub.objects.filter(name="Pokemon Go").exists())


class ModerationTests(HubTestCase):
    def setUp(self):
        super().setUp()
        self.pending = self.make_hub(
            "Cosplay Crafts", status=Hub.Status.PENDING, requested_by=self.member
        )
        self.login(self.moderator)

    def decide(self, action, hub=None):
        return self.client.post(reverse(f"hubs:{action}", args=[(hub or self.pending).id]))

    def test_review_page_lists_pending_requests_only(self):
        self.make_hub("Turned Down", status=Hub.Status.REJECTED)
        response = self.client.get(reverse("hubs:review"))
        self.assertEqual([hub.name for hub in response.context["pending"]], ["Cosplay Crafts"])

    def test_approving_publishes_the_hub_and_makes_the_requester_its_first_member(self):
        self.decide("approve")
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Hub.Status.APPROVED)
        self.assertEqual(
            list(self.pending.memberships.values_list("user_id", flat=True)), [self.member.id]
        )

    def test_rejecting_keeps_the_hub_hidden_and_adds_no_members(self):
        self.decide("reject")
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Hub.Status.REJECTED)
        self.assertFalse(self.pending.memberships.exists())

    def test_a_request_can_only_be_decided_once(self):
        self.decide("approve")
        for action in ("approve", "reject"):
            with self.subTest(action=action):
                self.assertEqual(self.decide(action).status_code, 404)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Hub.Status.APPROVED)
        self.assertEqual(self.pending.memberships.count(), 1)

    def test_already_approved_hubs_cannot_be_rejected(self):
        self.assertEqual(self.decide("reject", hub=self.hub).status_code, 404)
        self.hub.refresh_from_db()
        self.assertEqual(self.hub.status, Hub.Status.APPROVED)

    def test_decisions_refuse_get_requests(self):
        for action in ("approve", "reject"):
            with self.subTest(action=action):
                response = self.client.get(reverse(f"hubs:{action}", args=[self.pending.id]))
                self.assertEqual(response.status_code, 405)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Hub.Status.PENDING)

    def test_approved_hub_then_appears_in_the_public_list(self):
        self.decide("approve")
        self.login(self.stranger)
        response = self.client.get(reverse("hubs:list"))
        self.assertIn("Cosplay Crafts", [hub.name for hub in response.context["hubs"]])
