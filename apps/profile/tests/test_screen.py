import io
import os
import shutil
import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from PIL import Image

from apps.hubs.models import Hub, HubMembership
from apps.locations.models import Location
from apps.profile.models import Interest, Profile
from apps.ratings.models import Rating

URL = reverse("profile:profile")
TEMP_MEDIA = tempfile.mkdtemp()


def picture(name="me.png", fmt="PNG", size=(10, 10)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "red").save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProfileScreenTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user("ben", first_name="Ben", last_name="Santos", email="ben@example.com")
        self.client.force_login(self.user)
        self.library = Location.objects.get(name="Library")

    def form_data(self, **overrides):
        data = {
            "first_name": "Ben", "last_name": "Santos", "university_email": "ben@example.com",
            "location": "", "interest_names": "", "bio": "",
        }
        data.update(overrides)
        return data

    def save(self, **overrides):
        return self.client.post(URL, self.form_data(**overrides))

    def mine(self):
        return Profile.objects.get(user=self.user)


class AccessTests(ProfileScreenTestCase):
    def test_anonymous_visitors_are_sent_to_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(URL), f"{reverse('login:login')}?next={URL}")
        response = self.client.post(URL, self.form_data(first_name="Hacked"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("login:login")))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ben")

    def test_first_visit_creates_a_profile_from_the_account_email(self):
        self.assertEqual(self.client.get(URL).status_code, 200)
        self.assertEqual(self.mine().university_email, "ben@example.com")

    def test_you_can_only_ever_edit_your_own_profile(self):
        other = User.objects.create_user("amy", first_name="Amy")
        other_profile = Profile.objects.create(user=other, university_email="amy@example.com")
        self.save(first_name="Ben2", user=other.pk, id=other_profile.pk)
        other.refresh_from_db(); other_profile.refresh_from_db()
        self.assertEqual((other.first_name, other_profile.university_email), ("Amy", "amy@example.com"))
        self.assertEqual(self.mine().user, self.user)


class SavingTests(ProfileScreenTestCase):
    def test_a_valid_form_saves_everything_and_redirects(self):
        response = self.save(
            first_name="  Benedict ", last_name="Santos", university_email="BEN@Example.com",
            location=self.library.pk, bio="Raid nights!", interest_names="Pokemon Go, Cosplay",
        )
        self.assertRedirects(response, URL, fetch_redirect_response=False)
        self.user.refresh_from_db()
        profile = self.mine()
        self.assertEqual(self.user.first_name, "Benedict")
        self.assertEqual(profile.university_email, "ben@example.com")
        self.assertEqual(profile.location, self.library)
        self.assertEqual(profile.bio, "Raid nights!")
        self.assertEqual(profile.interest_list(), ["Cosplay", "Pokemon Go"])

    def test_first_name_is_required_but_last_name_is_optional(self):
        self.assertIn("first_name", self.save(first_name="  ").context["form"].errors)
        self.save(last_name="")
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_name, "")

    def test_a_failed_save_changes_nothing(self):
        response = self.save(first_name="Changed", university_email="not-an-email")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ben")

    def test_after_a_failed_save_the_summary_still_shows_what_is_really_saved(self):
        response = self.save(first_name="", university_email="new@example.com", location=self.library.pk)
        self.assertEqual(response.status_code, 200)
        summary = response.context["profile"]
        self.assertEqual(summary.university_email, "ben@example.com")
        self.assertIsNone(summary.location)

    def test_names_and_profile_are_saved_together_or_not_at_all(self):
        self.client.raise_request_exception = False
        with mock.patch("apps.profile.forms.ProfileEditForm._save_interests", side_effect=RuntimeError("boom")):
            response = self.save(first_name="Half Saved", bio="half saved")
        self.assertEqual(response.status_code, 500)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ben")
        self.assertEqual(self.mine().bio, "")

    def test_the_form_cannot_change_trust_rating_or_owner(self):
        self.save(trust_rating=1, user=999999, created_at="2000-01-01")
        self.assertEqual(self.mine().user, self.user)
        self.assertEqual(self.mine().trust_rating, 100)


class EmailTests(ProfileScreenTestCase):
    def test_a_taken_email_is_rejected_whatever_its_capitalisation(self):
        Profile.objects.create(user=User.objects.create_user("amy"), university_email="amy@example.com")
        response = self.save(university_email="AMY@example.com")
        self.assertIn("university_email", response.context["form"].errors)

    def test_keeping_your_own_email_is_not_a_duplicate(self):
        self.assertEqual(self.save().status_code, 302)

    @override_settings(UNIVERSITY_EMAIL_DOMAINS=["cit.edu"])
    def test_the_university_rule_applies_when_it_is_switched_on(self):
        self.assertIn("university_email", self.save(university_email="ben@gmail.com").context["form"].errors)
        self.assertEqual(self.save(university_email="ben@students.cit.edu").status_code, 302)

    @override_settings(UNIVERSITY_EMAIL_DOMAINS=[])
    def test_any_email_is_fine_while_the_rule_is_off(self):
        self.assertEqual(self.save(university_email="ben@gmail.com").status_code, 302)


class InterestTests(ProfileScreenTestCase):
    def interests(self):
        return self.mine().interest_list()

    def test_spaces_commas_and_case_are_tidied_and_duplicates_collapse(self):
        self.save(interest_names=" Pokemon   Go ,, pokemon go , Cosplay ,")
        self.assertEqual(self.interests(), ["Cosplay", "Pokemon   Go".replace("   ", " ")])

    def test_typing_an_existing_interest_reuses_it_ignoring_case(self):
        existing = Interest.objects.create(name="Cosplay")
        self.save(interest_names="cosplay")
        self.assertEqual(Interest.objects.filter(name__iexact="cosplay").count(), 1)
        self.assertEqual(list(self.mine().interests.all()), [existing])

    def test_removing_an_interest_unlinks_it_but_keeps_it_for_others(self):
        self.save(interest_names="Cosplay, Anime")
        self.save(interest_names="Anime")
        self.assertEqual(self.interests(), ["Anime"])
        self.assertTrue(Interest.objects.filter(name="Cosplay").exists())

    def test_clearing_the_box_removes_all_interests(self):
        self.save(interest_names="Cosplay")
        self.save(interest_names="")
        self.assertEqual(self.interests(), [])

    def test_at_most_ten_interests(self):
        many = ", ".join(f"Interest {n}" for n in range(11))
        self.assertIn("interest_names", self.save(interest_names=many).context["form"].errors)
        self.assertEqual(self.interests(), [])
        self.assertEqual(self.save(interest_names=", ".join(f"Interest {n}" for n in range(10))).status_code, 302)

    def test_repeats_do_not_count_towards_the_cap(self):
        ten_plus_a_repeat = ", ".join([f"Interest {n}" for n in range(10)] + ["interest 0"])
        self.assertEqual(self.save(interest_names=ten_plus_a_repeat).status_code, 302)
        self.assertEqual(len(self.interests()), 10)

    def test_each_interest_is_at_most_100_characters(self):
        self.assertIn("interest_names", self.save(interest_names="x" * 101).context["form"].errors)

    def test_markup_in_an_interest_is_shown_as_text(self):
        self.save(interest_names="<script>alert(1)</script>")
        page = self.client.get(URL)
        self.assertNotContains(page, "<script>alert(1)</script>")
        self.assertContains(page, "&lt;script&gt;alert(1)&lt;/script&gt;")


class LocationTests(ProfileScreenTestCase):
    def test_pick_change_and_clear_a_location(self):
        self.save(location=self.library.pk)
        self.assertEqual(self.mine().location, self.library)
        self.save(location="")
        self.assertIsNone(self.mine().location)

    def test_a_location_that_does_not_exist_is_rejected(self):
        self.assertIn("location", self.save(location=999999).context["form"].errors)


class PhotoTests(ProfileScreenTestCase):
    def upload(self, file):
        return self.client.post(URL, {**self.form_data(), "profile_image": file})

    def test_a_small_png_is_accepted(self):
        self.assertEqual(self.upload(picture()).status_code, 302)
        self.assertTrue(self.mine().profile_image)

    def test_every_allowed_format_works(self):
        for fmt in ("JPEG", "PNG", "GIF", "WEBP"):
            with self.subTest(fmt=fmt):
                self.assertEqual(self.upload(picture(f"me.{fmt.lower()}", fmt)).status_code, 302)

    def test_something_that_is_not_an_image_is_rejected_even_if_named_png(self):
        response = self.upload(SimpleUploadedFile("evil.png", b"<script>alert(1)</script>", content_type="image/png"))
        self.assertIn("profile_image", response.context["form"].errors)
        self.assertFalse(self.mine().profile_image)

    def test_other_image_formats_are_rejected(self):
        response = self.upload(picture("me.bmp", "BMP"))
        self.assertIn("profile_image", response.context["form"].errors)

    def test_pictures_over_2_mb_are_rejected(self):
        buffer = io.BytesIO()
        Image.frombytes("RGB", (1200, 1200), os.urandom(1200 * 1200 * 3)).save(buffer, "PNG")
        self.assertGreater(buffer.tell(), 2 * 1024 * 1024)
        big = SimpleUploadedFile("big.png", buffer.getvalue(), content_type="image/png")
        self.assertIn("profile_image", self.upload(big).context["form"].errors)


class PageTests(ProfileScreenTestCase):
    def test_the_page_shows_name_trust_rating_location_and_interests(self):
        self.save(location=self.library.pk, interest_names="Cosplay")
        Rating.objects.create(rater=User.objects.create_user("amy"), rated_user=self.user, score=4)
        page = self.client.get(URL)
        for text in ("Ben Santos", "80%", "Library", "Cosplay"):
            self.assertContains(page, text)

    def test_only_approved_joined_hubs_are_listed(self):
        owner = User.objects.create_user("owner")
        good = Hub.objects.create(name="Uma Musume", requested_by=owner, status=Hub.Status.APPROVED)
        waiting = Hub.objects.create(name="Waiting Hub", requested_by=owner, status=Hub.Status.PENDING)
        Hub.objects.create(name="Not Joined", requested_by=owner, status=Hub.Status.APPROVED)
        for hub in (good, waiting):
            HubMembership.objects.create(user=self.user, hub=hub)
        names = [hub.name for hub in self.client.get(URL).context["joined_hubs"]]
        self.assertEqual(names, ["Uma Musume"])

    def test_query_count_does_not_grow_with_hubs_or_interests(self):
        def queries():
            with CaptureQueriesContext(connection) as captured:
                self.client.get(URL)
            return len(captured)

        self.client.get(URL)  # the first visit creates the profile; don't count that
        baseline = queries()
        owner = User.objects.create_user("owner")
        profile = self.mine()
        for n in range(8):
            hub = Hub.objects.create(name=f"Hub {n}", requested_by=owner, status=Hub.Status.APPROVED)
            HubMembership.objects.create(user=self.user, hub=hub)
            profile.interests.add(Interest.objects.create(name=f"Interest {n}"))
        self.assertEqual(queries(), baseline)
