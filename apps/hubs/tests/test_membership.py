from django.urls import reverse

from apps.hubs.models import Hub, HubMembership

from .base import HubTestCase


class JoinAndLeaveTests(HubTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.member)
        self.join_url = reverse("hubs:join", args=[self.hub.id])
        self.leave_url = reverse("hubs:leave", args=[self.hub.id])

    def memberships(self):
        return HubMembership.objects.filter(user=self.member, hub=self.hub)

    def test_joining_creates_one_membership_even_if_submitted_twice(self):
        self.client.post(self.join_url)
        self.client.post(self.join_url)
        self.assertEqual(self.memberships().count(), 1)

    def test_leaving_removes_the_membership(self):
        HubMembership.objects.create(user=self.member, hub=self.hub)
        self.client.post(self.leave_url)
        self.assertFalse(self.memberships().exists())

    def test_leaving_a_hub_you_are_not_in_is_harmless(self):
        response = self.client.post(self.leave_url)
        self.assertEqual(response.status_code, 302)

    def test_leaving_only_removes_your_own_membership(self):
        HubMembership.objects.create(user=self.member, hub=self.hub)
        HubMembership.objects.create(user=self.stranger, hub=self.hub)
        self.client.post(self.leave_url)
        self.assertEqual(HubMembership.objects.filter(hub=self.hub).count(), 1)
        self.assertTrue(HubMembership.objects.filter(user=self.stranger, hub=self.hub).exists())

    def test_join_and_leave_refuse_get_requests(self):
        for url in (self.join_url, self.leave_url):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)
        self.assertFalse(self.memberships().exists())

    def test_cannot_join_a_hub_that_is_not_approved(self):
        for status in (Hub.Status.PENDING, Hub.Status.REJECTED):
            hub = self.make_hub(f"Hub {status}", status=status)
            with self.subTest(status=status):
                response = self.client.post(reverse("hubs:join", args=[hub.id]))
                self.assertEqual(response.status_code, 404)
                self.assertFalse(HubMembership.objects.filter(hub=hub).exists())


class RedirectBackTests(HubTestCase):
    """The `next` field must never turn Join/Leave into an open redirect."""

    def setUp(self):
        super().setUp()
        self.login(self.member)
        self.url = reverse("hubs:join", args=[self.hub.id])
        self.fallback = reverse("hubs:detail", args=[self.hub.id])

    def post_next(self, next_url):
        return self.client.post(self.url, {"next": next_url})

    def test_a_local_next_page_is_honoured(self):
        response = self.post_next(reverse("hubs:list") + "?q=uma")
        self.assertRedirects(response, "/hubs/?q=uma", fetch_redirect_response=False)

    def test_missing_next_falls_back_to_the_hub_page(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, self.fallback, fetch_redirect_response=False)

    def test_external_or_script_next_values_are_ignored(self):
        for bad in (
            "https://evil.example/phish",
            "//evil.example/phish",
            "http://evil.example",
            "javascript:alert(1)",
            "\\\\evil.example",
        ):
            with self.subTest(next=bad):
                response = self.post_next(bad)
                self.assertRedirects(response, self.fallback, fetch_redirect_response=False)
