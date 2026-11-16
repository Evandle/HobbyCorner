# Plan: Profile screen on the revised ERD (with Register's email intake)

Status: **COMPLETE**

## Goal, as measurable success criteria
1. **Models match the revised ERD.** `python manage.py makemigrations --check --dry-run` reports no drift; the database has the revised ERD's 15 tables.
2. **Migrations work two ways on real PostgreSQL 16:** from zero (a brand-new Supabase project), and upgrading from today's schema. Both are reversible.
3. **Profile screen is complete.** Edit first/last name, email, bio, photo, location (pick), interests (type, up to 10). Page shows joined Hubs and a derived trust rating.
4. **Email rule switchable without code.** `UNIVERSITY_EMAIL_DOMAINS=` empty accepts any valid email; `=cit.edu` accepts only that domain and its subdomains.
5. **Register collects name and email** and creates user + profile atomically.

## Answers recorded (approval round)
- Existing Supabase data: **nothing worth keeping**; a brand-new database is also fine.
- Accepted as recommended: email-domain env var (subdomains count), seed ~8 generic locations (pick-only), free-typed interests (max 10) with suggestions, derived trust rating, Register imports Profile, Meetup.location becomes a Location FK now, photo limits (images only, 2 MB, local storage).

## Phases (execution order)

### P1. Models + migrations (size M) | Blocked by: none
- New app `apps/locations` (`Location`, table `locations`) with a seed migration of generic campus areas.
- `apps/profile`: `Interest` (`interests`), `ProfileInterest` (`profile_interests`, unique pair), `Profile.location` (nullable FK, SET_NULL), `Profile.interests` (many-to-many through the junction), derived `trust_rating`, email validator reading `UNIVERSITY_EMAIL_DOMAINS`, emails stored lowercase. Removes `full_name`, text `interests`, stored `trust_rating`, `current_location`.
- `apps/discovery`: `Meetup.location` becomes a non-null FK to Location (PROTECT). Existing meetup rows are deleted by the migration (none are real; agreed).
- Minimal code edits so the site stays green: profile form fields, profile template, profile admin.
- Files: `apps/locations/*`, `apps/profile/{models,validators,forms,admin}.py`, `apps/profile/migrations/0003_*`, `apps/discovery/{models,admin}.py`, `apps/discovery/migrations/0002_*`, `config/settings.py`, `.env.example`, `templates/profile/profile.html`
- Seam: model/DB behaviour through Django tests; migrations through the real migration executor on PostgreSQL 16.
- Verify: `python manage.py test apps.profile apps.home` and `PYTHONPATH=/tmp:. python3 /tmp/verify_migrations.py` (fresh database, upgrade from `0002` state, roll back, roll forward)

### P2. Profile screen (size M) | Blocked by: P1
- Form: first name, last name, email, bio, photo, location (select), interests (text + clickable suggestions).
- Page: joined Hubs (read-only), interest pills, location, derived trust rating.
- Photo: JPEG/PNG/GIF/WEBP only, at most 2 MB. Interests: trimmed, de-duplicated ignoring case, at most 10, each at most 100 characters.
- Files: `apps/profile/{forms,views}.py`, `templates/profile/profile.html`, `static/{css,js}/profile/*`
- Verify: `python manage.py test apps.profile` (includes a query-count test)

### P3. Register intake (size S) | Blocked by: P1 (can run alongside P2)
- First name, last name, email, username, password. User and Profile created in one transaction.
- Files: `apps/register/{forms,views}.py`, `templates/register/register.html`
- Verify: `python manage.py test apps.register`

### P4. Verify and package (size S) | Blocked by: P2, P3
- Full suite on SQLite and real PostgreSQL 16; mutation test of the new guards; zip with install notes including the Supabase steps.
- Verify: `python manage.py test`, `python3 /tmp/mutate.py`

## Decision log
- **D1** Profile first, together with Register's email intake: the revised ERD lands there.
- **D2** Email rule via env var `UNIVERSITY_EMAIL_DOMAINS` (empty = any email).
- **D3 (REVISED after approval)** One clean migration per app, no backfill. Reason: nothing worth keeping, so carry-over code would be complexity with no payoff. Still reversible; still tested from zero and from today's schema. If real data ever matters, expand/contract returns.
- **D4** Locations in their own small shared app so profile and discovery don't depend on each other.
- **D5** Register imports Profile (signup must create the profile because the email is collected there). Reverses the earlier decoupling.
- **D6** Trust rating derived: average rating over 5 as a percentage; 100 when unrated; reports ignored until that screen exists.
- **D7** Interests typed freely (max 10); locations pick-only.

## Not yet specified (fog)
Email verification flow; trust formula with reports; Discovery's Location matching; production photo storage.

## Always / Never
- **Always:** test first and prove tests can fail; verify on real PostgreSQL; leave Hubs and Settings untouched.
- **Never:** touch your Supabase from here; send real emails; build rating, report or chat screens.

## Progress
| Phase | Status |
|---|---|
| P1 Models + migrations | done (63 tests; real PostgreSQL: fresh, upgrade, rollback, roll-forward) |
| P2 Profile screen | done (92 tests; N+1 guard proven by mutation) |
| P3 Register intake | done (110+ tests; 25 guard mutations caught) |
| P4 Verify and package | done (113 tests on SQLite and PostgreSQL 16) |

## Outcome
- 113 tests pass on SQLite and on real PostgreSQL 16. 25 guards mutation-tested (16 profile, 9 register); one gap found and closed.
- Migrations verified on PostgreSQL: brand-new database, upgrade from the old schema, rollback with a meetup present, roll-forward.
- A Postgres-only bug (cannot ALTER a table after deleting its rows in one transaction) was found by the real-database run and fixed; SQLite tests could not have caught it.
- Deliberately not done: email verification, show-password toggle and forgot-password link (sign-up guide), single password box (guide prefers it; kept the confirm box for now).
