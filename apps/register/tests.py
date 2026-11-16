from unittest import mock

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.profile.models import Profile

URL = reverse("register:register")
PASSWORD = "Zq7!mK2#vR9xLp"


class RegisterTestCase(TestCase):
    def data(self, **overrides):
        data = {
            "first_name": "Ben", "last_name": "Santos", "username": "ben",
            "university_email": "ben@example.com", "password1": PASSWORD, "password2": PASSWORD,
        }
        data.update(overrides)
        return data

    def signup(self, **overrides):
        return self.client.post(URL, self.data(**overrides))


class SignUpTests(RegisterTestCase):
    def test_a_valid_sign_up_creates_the_user_and_profile_and_goes_to_login(self):
        response = self.signup(first_name="  Ben ", university_email=" BEN@Example.com ")
        self.assertRedirects(response, reverse("login:login"), fetch_redirect_response=False)
        user = User.objects.get(username="ben")
        self.assertEqual((user.first_name, user.last_name), ("Ben", "Santos"))
        self.assertEqual(user.profile.university_email, "ben@example.com")

    def test_the_new_account_can_log_in_and_the_password_is_hashed(self):
        self.signup()
        self.assertNotEqual(User.objects.get(username="ben").password, PASSWORD)
        self.assertTrue(self.client.login(username="ben", password=PASSWORD))

    def test_the_form_cannot_make_you_staff_or_a_superuser(self):
        self.signup(is_staff="on", is_superuser="on")
        user = User.objects.get(username="ben")
        self.assertFalse(user.is_staff or user.is_superuser)

    def test_logged_in_people_are_sent_home(self):
        self.client.force_login(User.objects.create_user("amy"))
        self.assertRedirects(self.client.get(URL), reverse("home:home"), fetch_redirect_response=False)

    def test_international_names_are_kept_intact(self):
        for first, last in (("María José", "Núñez"), ("Nguyễn", "Thị"), ("李", "小龍")):
            with self.subTest(first=first):
                self.client.post(URL, self.data(first_name=first, last_name=last,
                                                username=f"user{ord(first[0])}", university_email=f"u{ord(first[0])}@example.com"))
                user = User.objects.get(username=f"user{ord(first[0])}")
                self.assertEqual((user.first_name, user.last_name), (first, last))

    def test_csrf_protection_is_on(self):
        strict = Client(enforce_csrf_checks=True)
        self.assertEqual(strict.post(URL, self.data()).status_code, 403)
        self.assertFalse(User.objects.exists())


class RejectedSignUpTests(RegisterTestCase):
    def assertRejected(self, response, field):
        self.assertEqual(response.status_code, 200)
        self.assertIn(field, response.context["form"].errors)
        self.assertFalse(User.objects.exists())
        self.assertFalse(Profile.objects.exists())

    def test_first_name_is_required_and_last_name_is_optional(self):
        self.assertRejected(self.signup(first_name="  "), "first_name")
        self.assertEqual(self.signup(last_name="").status_code, 302)

    def test_a_malformed_email_is_rejected(self):
        self.assertRejected(self.signup(university_email="not-an-email"), "university_email")

    def test_a_taken_email_is_rejected_whatever_its_capitalisation(self):
        Profile.objects.create(user=User.objects.create_user("amy"), university_email="ben@example.com")
        before = User.objects.count()
        response = self.signup(university_email="BEN@EXAMPLE.COM")
        self.assertIn("university_email", response.context["form"].errors)
        self.assertEqual(User.objects.count(), before)

    def test_a_taken_username_is_rejected(self):
        User.objects.create_user("ben")
        response = self.signup()
        self.assertIn("username", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_weak_or_mismatched_passwords_are_rejected(self):
        self.assertRejected(self.signup(password1="12345678", password2="12345678"), "password2")
        self.assertRejected(self.signup(password2="Different-Pass-1!"), "password2")

    @override_settings(UNIVERSITY_EMAIL_DOMAINS=["cit.edu"])
    def test_the_university_rule_applies_when_switched_on(self):
        self.assertRejected(self.signup(university_email="ben@gmail.com"), "university_email")
        self.assertEqual(self.signup(university_email="ben@students.cit.edu").status_code, 302)

    @override_settings(UNIVERSITY_EMAIL_DOMAINS=[])
    def test_any_email_is_fine_while_the_rule_is_off(self):
        self.assertEqual(self.signup(university_email="ben@gmail.com").status_code, 302)


class AllOrNothingTests(RegisterTestCase):
    def test_if_the_profile_cannot_be_created_no_account_is_left_behind(self):
        with mock.patch("apps.register.views.Profile.objects.create", side_effect=IntegrityError("taken")):
            response = self.signup()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertFalse(User.objects.exists())


class FormMarkupTests(RegisterTestCase):
    """The sign-up guide's rules, checked on the rendered page."""

    def setUp(self):
        self.html = self.client.get(URL).content.decode()

    def test_password_fields_ask_the_browser_for_a_new_password(self):
        self.assertEqual(self.html.count('autocomplete="new-password"'), 2)

    def test_each_field_has_the_right_type_and_autofill_hint(self):
        for fragment in (
            'type="email"', 'autocomplete="email"', 'inputmode="email"',
            'autocomplete="given-name"', 'autocomplete="family-name"', 'autocomplete="username"',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.html)

    def test_browser_validation_is_left_switched_on(self):
        self.assertNotIn("novalidate", self.html)
        self.assertIn("required", self.html)

    def test_the_old_hint_about_filling_the_email_in_later_is_gone(self):
        self.assertNotIn("after signing up", self.html)
