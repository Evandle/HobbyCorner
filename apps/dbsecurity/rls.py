"""Keep Supabase's public API out of your tables.

Supabase gives its API roles (anon, authenticated) full rights on every table in
the `public` schema, and a table is open to them until row-level security (RLS)
is switched on. This app is only ever reached through Django, which connects as
the database owner and bypasses RLS, so switching it on with no policies shuts
the public API out and costs the app nothing.

After every `migrate` this makes sure each public table has RLS on, so tables
added by later migrations are protected without anyone remembering to do it.
Switch it off with ENABLE_RLS_ON_MIGRATE = False in settings.
"""
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections


def enable_rls_on_public_tables(connection):
    """Turn RLS on for every public table that doesn't have it yet.

    Returns the names of the tables it changed (empty on databases other than
    PostgreSQL, and when everything is already protected).
    """
    if connection.vendor != "postgresql":
        return []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND NOT rowsecurity ORDER BY tablename"
        )
        names = [row[0] for row in cursor.fetchall()]
        for name in names:
            cursor.execute(f"ALTER TABLE public.{connection.ops.quote_name(name)} ENABLE ROW LEVEL SECURITY")
    return names


def enable_rls_after_migrate(sender, using=DEFAULT_DB_ALIAS, verbosity=1, **kwargs):
    if not getattr(settings, "ENABLE_RLS_ON_MIGRATE", True):
        return
    changed = enable_rls_on_public_tables(connections[using])
    if changed and verbosity >= 1:
        print(f"  Row-level security enabled on {len(changed)} table(s): {', '.join(changed)}")
