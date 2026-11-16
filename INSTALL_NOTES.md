# Hobby Corner: integrated project (Profile + Hubs + Chat + RLS)

Included: login, register (name + email), home dashboard, profile, settings, hubs, chat,
locations, ratings (model only), discovery (MODELS ONLY), dbsecurity (RLS after migrate).

NOT included yet (unfinished): the Discovery screen. Its views, forms, queries, urls,
templates, static files and tests are deliberately left out. The dashboard's "Nearby Discovery"
card stays a placeholder.

## Order to run (from the project folder, venv active)
1. python manage.py check
2. python manage.py makemigrations     # creates hubs, chat, ratings, discovery, and profile 0002
3. python manage.py test               # throwaway SQLite database, never Supabase
4. python manage.py migrate            # applies to Supabase (reads DATABASE_URL from .env)
5. python manage.py runserver

## Optional
- .env: UNIVERSITY_EMAIL_DOMAINS=      (empty = any email; later e.g. cit.edu)
- Django admin -> Locations: rename the 8 generic campus areas to real ones.
- Chat cleanup (messages expire after 24 h): python manage.py purge_expired_messages
  Schedule it later (Windows Task Scheduler). The chat page hides old messages anyway.
- Moderators: Django admin -> Users -> tick "Staff status". Superusers can approve Hubs.
