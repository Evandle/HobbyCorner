from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.discovery.models import Meetup
from apps.hubs.models import Hub
from apps.locations.models import Location
from apps.profile.models import Interest, Profile, ProfileInterest
from apps.profile.validators import validate_university_email
from apps.ratings.models import Rating


def make_profile(username="ben", email=None):
    user = User.objects.create_user(username)
    return Profile.objects.create(user=user, university_email=email or f"{username}@example.com")


class TrustRatingTests(TestCase):
    def setUp(self):
        self.profile = make_profile("ben")
        self.raters = [User.objects.create_user(f"rater{i}") for i in range(3)]

    def rate(self, rater, score, target=None):
        Rating.objects.create(rater=rater, rated_user=target or self.profile.user, score=score)

    def test_an_unrated_member_starts_at_100(self):
        self.assertEqual(self.profile.trust_rating, 100)

    def test_it_is_the_average_score_as_a_percentage(self):
        self.rate(self.raters[0], 5)
        self.rate(self.raters[1], 3)
        self.assertEqual(self.profile.trust_rating, 80)

    def test_a_single_low_rating_pulls_it_down(self):
        self.rate(self.raters[0], 1)
        self.assertEqual(self.profile.trust_rating, 20)

    def test_ratings_you_give_do_not_count_towards_your_own_score(self):
        self.rate(self.profile.user, 1, target=self.raters[0])
        self.assertEqual(self.profile.trust_rating, 100)


class InterestTests(TestCase):
    def test_interest_list_is_sorted_by_name(self):
        profile = make_profile()
        for name in ("Uma Musume", "Cosplay", "Pokemon Go"):
            ProfileInterest.objects.create(profile=profile, interest=Interest.objects.create(name=name))
        self.assertEqual(profile.interest_list(), ["Cosplay", "Pokemon Go", "Uma Musume"])

    def test_a_profile_cannot_have_the_same_interest_twice(self):
        profile = make_profile()
        interest = Interest.objects.create(name="Cosplay")
        ProfileInterest.objects.create(profile=profile, interest=interest)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProfileInterest.objects.create(profile=profile, interest=interest)

    def test_interest_names_are_unique(self):
        Interest.objects.create(name="Cosplay")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Interest.objects.create(name="Cosplay")

    def test_many_profiles_can_share_one_interest(self):
        interest = Interest.objects.create(name="Cosplay")
        for username in ("ben", "amy"):
            ProfileInterest.objects.create(profile=make_profile(username), interest=interest)
        self.assertEqual(interest.profiles.count(), 2)


class UniversityEmailRuleTests(TestCase):
    def accepts(self, email):
        try:
            validate_university_email(email)
        except ValidationError:
            return False
        return True

    @override_settings(UNIVERSITY_EMAIL_DOMAINS=[])
    def test_with_no_domains_configured_any_email_is_accepted(self):
        for email in ("ben@gmail.com", "a@cit.edu", "x@anything.example"):
            with self.subTest(email=email):
                self.assertTrue(self.accepts(email))

    def test_a_missing_setting_behaves_like_no_restriction(self):
        with self.settings():
            del settings.UNIVERSITY_EMAIL_DOMAINS
            self.assertTrue(self.accepts("ben@gmail.com"))

    @override_settings(UNIVERSITY_EMAIL_DOMAINS=["cit.edu"])
    def test_the_configured_domain_and_its_subdomains_are_accepted(self):
        for email in ("a@cit.edu", "a@students.cit.edu", "A@CIT.EDU"):
            with self.subTest(email=email):
                self.assertTrue(self.accepts(email))

    @override_settings(UNIVERSITY_EMAIL_DOMAINS=["cit.edu"])
    def test_other_domains_and_look_alikes_are_rejected(self):
        for email in ("a@gmail.com", "a@notcit.edu", "a@evilcit.edu", "a@cit.edu.evil.com", "a@cit.edu@evil.com"):
            with self.subTest(email=email):
                self.assertFalse(self.accepts(email))

    @override_settings(UNIVERSITY_EMAIL_DOMAINS=["cit.edu", "school.edu.ph"])
    def test_several_domains_can_be_allowed(self):
        self.assertTrue(self.accepts("a@school.edu.ph"))
        self.assertTrue(self.accepts("a@cit.edu"))
        self.assertFalse(self.accepts("a@gmail.com"))

    @override_settings(UNIVERSITY_EMAIL_DOMAINS=["cit.edu"])
    def test_the_model_field_applies_the_rule_too(self):
        profile = Profile(user=User.objects.create_user("ben"), university_email="ben@gmail.com")
        with self.assertRaises(ValidationError) as caught:
            profile.full_clean()
        self.assertIn("university_email", caught.exception.message_dict)


class EmailStorageTests(TestCase):
    def test_emails_are_stored_lowercase_and_trimmed(self):
        profile = make_profile("ben", email="  Ben@Example.COM ")
        profile.refresh_from_db()
        self.assertEqual(profile.university_email, "ben@example.com")

    def test_two_spellings_of_one_email_collide(self):
        make_profile("ben", email="ben@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_profile("amy", email="BEN@example.com")


class GetOrCreateForTests(TestCase):
    def test_uses_the_account_email_when_there_is_one(self):
        user = User.objects.create_user("ben", email="ben@example.com")
        self.assertEqual(Profile.get_or_create_for(user).university_email, "ben@example.com")

    def test_without_an_email_a_clearly_fake_placeholder_is_used(self):
        profile = Profile.get_or_create_for(User.objects.create_user("ben"))
        self.assertTrue(profile.university_email.endswith(".invalid"))

    def test_calling_twice_returns_the_same_profile(self):
        user = User.objects.create_user("ben")
        self.assertEqual(Profile.get_or_create_for(user).pk, Profile.get_or_create_for(user).pk)
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)


class LocationTests(TestCase):
    def test_some_campus_areas_are_seeded(self):
        self.assertGreaterEqual(Location.objects.count(), 8)
        self.assertTrue(Location.objects.filter(name="Library").exists())

    def test_location_names_are_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Location.objects.create(name="Library")

    def test_deleting_a_location_clears_profiles_that_used_it(self):
        spot = Location.objects.create(name="Rooftop Garden")
        profile = make_profile()
        profile.location = spot
        profile.save()
        spot.delete()
        profile.refresh_from_db()
        self.assertIsNone(profile.location)

    def test_a_location_with_meetups_cannot_be_deleted(self):
        owner = User.objects.create_user("owner")
        hub = Hub.objects.create(name="Uma Musume", requested_by=owner, status=Hub.Status.APPROVED)
        spot = Location.objects.create(name="Rooftop Garden")
        Meetup.objects.create(hub=hub, created_by=owner, location=spot,
                              scheduled_time=timezone.now() + timedelta(days=1))
        with self.assertRaises(ProtectedError):
            spot.delete()
