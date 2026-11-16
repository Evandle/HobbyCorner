import io
from contextlib import redirect_stdout
from unittest import mock, skipIf, skipUnless

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings

from apps.dbsecurity.rls import enable_rls_after_migrate, enable_rls_on_public_tables

ON_POSTGRES = connection.vendor == "postgresql"
TARGET = "apps.dbsecurity.rls.enable_rls_on_public_tables"


@skipIf(ON_POSTGRES, "this checks the behaviour on databases other than PostgreSQL")
class OffPostgresTests(TestCase):
    def test_nothing_happens_and_nothing_breaks(self):
        self.assertEqual(enable_rls_on_public_tables(connection), [])

    def test_migrate_still_works(self):
        call_command("migrate", verbosity=0)


class SwitchTests(TestCase):
    def run_hook(self, **kwargs):
        with mock.patch(TARGET, return_value=["a", "b"]) as protect:
            enable_rls_after_migrate(sender=None, **kwargs)
        return protect

    def test_it_runs_by_default(self):
        self.assertEqual(self.run_hook(verbosity=0).call_count, 1)

    @override_settings(ENABLE_RLS_ON_MIGRATE=False)
    def test_it_can_be_switched_off_in_settings(self):
        self.assertEqual(self.run_hook(verbosity=0).call_count, 0)

    def test_it_tells_you_what_it_protected_unless_told_to_be_quiet(self):
        loud, quiet = io.StringIO(), io.StringIO()
        with redirect_stdout(loud):
            self.run_hook(verbosity=1)
        with redirect_stdout(quiet):
            self.run_hook(verbosity=0)
        self.assertIn("2 table(s): a, b", loud.getvalue())
        self.assertEqual(quiet.getvalue(), "")


class WiringTests(TestCase):
    def test_migrate_runs_the_hook_exactly_once(self):
        with mock.patch(TARGET, return_value=[]) as protect:
            call_command("migrate", verbosity=0)
        self.assertEqual(protect.call_count, 1)


@skipUnless(ON_POSTGRES, "row-level security exists only on PostgreSQL")
class PostgresTests(TestCase):
    def unprotected_tables(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND NOT rowsecurity")
            return sorted(row[0] for row in cursor.fetchall())

    def make_table(self, name):
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE TABLE public.{name} (id integer)")

    def test_every_table_the_migrations_created_is_already_protected(self):
        self.assertEqual(self.unprotected_tables(), [])

    def test_a_new_table_is_protected_once_and_only_once(self):
        self.make_table("late_arrival")
        self.assertEqual(self.unprotected_tables(), ["late_arrival"])
        self.assertEqual(enable_rls_on_public_tables(connection), ["late_arrival"])
        self.assertEqual(self.unprotected_tables(), [])
        self.assertEqual(enable_rls_on_public_tables(connection), [])

    def test_table_names_that_need_quoting_are_handled(self):
        with connection.cursor() as cursor:
            cursor.execute('CREATE TABLE public."Odd Name" (id integer)')
        self.assertEqual(enable_rls_on_public_tables(connection), ["Odd Name"])
        self.assertEqual(self.unprotected_tables(), [])

    def test_running_migrate_protects_tables_added_since_the_last_run(self):
        self.make_table("added_later")
        call_command("migrate", verbosity=0)
        self.assertEqual(self.unprotected_tables(), [])

    def test_other_database_roles_see_nothing_but_the_owner_still_sees_everything(self):
        User.objects.create_user("ben")
        with connection.cursor() as cursor:
            cursor.execute("CREATE ROLE rls_probe_reader NOLOGIN")
            cursor.execute("GRANT SELECT ON auth_user TO rls_probe_reader")
            cursor.execute("SET ROLE rls_probe_reader")
            cursor.execute("SELECT count(*) FROM auth_user")
            as_outsider = cursor.fetchone()[0]
            cursor.execute("RESET ROLE")
            cursor.execute("SELECT count(*) FROM auth_user")
            as_owner = cursor.fetchone()[0]
        self.assertEqual((as_outsider, as_owner), (0, 1))
