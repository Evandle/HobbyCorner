from django.urls import reverse

from apps.hubs.models import Hub, HubMembership

from .base import HubTestCase


class LoginRequiredTests(HubTestCase):
    def test_anonymous_visitors_are_sent_to_login_on_every_page(self):
        pages = [
            reverse("hubs:list"),
            reverse("hubs:request"),
            reverse("hubs:review"),
            reverse("hubs:detail", args=[self.hub.id]),
        ]
        for url in pages:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('login:login')}?next={url}")

    def test_anonymous_visitors_cannot_use_any_action(self):
        pending = self.make_hub("Pending Hub", status=Hub.Status.PENDING)
        actions = {"join": self.hub, "leave": self.hub, "approve": pending, "reject": pending}
        for action, hub in actions.items():
            with self.subTest(action=action):
                response = self.client.post(reverse(f"hubs:{action}", args=[hub.id]))
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(reverse("login:login")))
        pending.refresh_from_db()
        self.assertEqual(pending.status, Hub.Status.PENDING)
        self.assertEqual(HubMembership.objects.count(), 0)


class ModeratorOnlyTests(HubTestCase):
    def setUp(self):
        super().setUp()
        self.pending = self.make_hub("Pending Hub", status=Hub.Status.PENDING)

    def test_regular_members_cannot_open_the_review_page(self):
        self.login(self.member)
        self.assertEqual(self.client.get(reverse("hubs:review")).status_code, 403)

    def test_regular_members_cannot_approve_or_reject(self):
        self.login(self.member)
        for action in ("approve", "reject"):
            with self.subTest(action=action):
                response = self.client.post(reverse(f"hubs:{action}", args=[self.pending.id]))
                self.assertEqual(response.status_code, 403)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Hub.Status.PENDING)
        self.assertFalse(HubMembership.objects.filter(hub=self.pending).exists())

    def test_moderators_can_open_the_review_page(self):
        self.login(self.moderator)
        self.assertEqual(self.client.get(reverse("hubs:review")).status_code, 200)


class NavigationMatchesPermissionsTests(HubTestCase):
    """The Review link must be shown to exactly the people the guard lets in."""

    def test_review_link_is_hidden_from_members_and_shown_to_moderators(self):
        review_url = reverse("hubs:review")
        for user, should_see in ((self.member, False), (self.moderator, True)):
            with self.subTest(user=user.username):
                self.login(user)
                page = self.client.get(reverse("hubs:list"))
                self.assertEqual(review_url in page.content.decode(), should_see)
                self.assertEqual(
                    self.client.get(review_url).status_code, 200 if should_see else 403
                )
