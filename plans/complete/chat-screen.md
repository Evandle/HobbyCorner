# Plan: Fresh Start chat screen

Status: **COMPLETE**

## Goal, as measurable success criteria
1. A Hub member can open a chat page, read the last 24 hours of messages, and send text (up to 500 characters) and/or a picture (JPEG/PNG/GIF/WEBP, up to 2 MB).
2. New messages from others appear without reloading (checked every few seconds, paused while the tab is hidden).
3. You can delete your own messages (and the picture file goes with them). Nobody can edit.
4. Non-members see nothing and can do nothing. Unapproved Hubs don't exist as far as chat is concerned.
5. `python manage.py purge_expired_messages` deletes messages older than 24 hours and their picture files; the page hides them regardless.
6. The dashboard's "Recent Hub activity" shows real counts; Hub pages link members to the chat.

## Approved decisions
- **D1** Live updates by polling every ~4 s (no websockets, no new servers).
- **D2** Only members of an approved Hub can read or post.
- **D3** Text up to 500 chars; optional picture with the same rules as profile photos.
- **D4** Cleanup is a management command you schedule later; views hide expired messages anyway.
- **D5** Delete own messages only; no editing.
- **D6** Block and report are left to the Safety screen.

## Small decisions made while researching (not asked; reversible; tell me to change any)
- **D7** Sending is a normal form post (page reloads); polling handles incoming messages. A no-reload send can be added later.
- **D8** The poll endpoint returns server-rendered HTML fragments inside JSON, so there is one source of message markup and Django's escaping protects against script injection.
- **D9** At most 200 messages per page or poll. Polling pauses while the tab is hidden and backs off after errors.
- **D10** Messages deleted or expired while you're looking at the page disappear on reload, not live.
- **D11** A non-member opening the chat is sent to the Hub page with a note; other non-member requests get 403.
- **D12** Dashboard "Recent Hub activity" = number of messages in the last 24 h for each Hub you joined.
- **D13** The picture rules move to a tiny shared module (`apps/shared/images.py`) used by both Profile and Chat, so the security-relevant check can't drift. Profile's existing tests guard the refactor.
- **D14** No schema change: the 500-character limit lives in the form, and `models.py` only gains a constant. No migration.

## Phases
### P1. Chat room core (size M) | Blocked by: none
Page, send text/picture, delete own message, membership checks, shared picture validator, templates, CSS/JS.
Files: `apps/shared/images.py`, `apps/profile/forms.py` (use shared check), `apps/chat/{models,forms,views,urls}.py`, `templates/chat/{room,_message}.html`, `static/{css,js}/chat/*`, `config/urls.py`
Verify: `python manage.py test apps.chat apps.profile`

### P2. Live updates (size S) | Blocked by: P1
Poll endpoint (new messages after an id, within 24 h, members only), polling script, polite live region, scroll handling.
Verify: `python manage.py test apps.chat`

### P3. Cleanup command (size S) | Blocked by: P1
`purge_expired_messages` with `--dry-run`; deletes picture files too.
Verify: `python manage.py test apps.chat`

### P4. Integration (size S) | Blocked by: P1
"Open chat" button on the Hub page for members; real "Recent Hub activity" on the dashboard.
Verify: `python manage.py test apps.hubs apps.home`

### P5. Verify and package (size S) | Blocked by: P2, P3, P4
Full suite on SQLite and PostgreSQL 16; mutation test of the new guards; zip with install notes.

## Not yet specified
Replies/reactions; unread counts and new-message notifications (Notifications screen); hiding blocked people (Safety screen); production picture storage; true real-time.

## Always / Never
- **Always:** test first and prove tests can fail; verify on real PostgreSQL; keep chat text escaped (never `|safe`, never `innerHTML` with user text).
- **Never:** show chat to non-members; touch your Supabase; change Hubs behaviour beyond one link.

## Progress
| Phase | Status |
|---|---|
| P1 Chat room core | done (145 tests incl. profile photo tests guarding the shared validator) |
| P2 Live updates | done (161 Python tests + 36 JS checks; 12/12 JS mutations caught) |
| P3 Cleanup command | done (168 tests) |
| P4 Integration | done (174 tests) |
| P5 Verify and package | done (174 tests on SQLite and PostgreSQL 16) |

## Outcome
- 174 Python tests pass on SQLite and on real PostgreSQL 16 (55 of them chat). 36 behaviour checks of the polling script pass in a simulated browser (jsdom), not a real one.
- Mutation testing: 30 chat guards on the Python side, all caught; 12 on the script, all caught. Two gaps found in the script's tests (tab hidden mid-request; tab flicker mid-request) and closed.
- No migration needed; `makemigrations --check` reports no drift.
- Found and fixed along the way: chat CSS/JS were silently not written because their folders didn't exist (tests don't load static files); a placeholder test that checked nothing; a harness bug that doubled script initialisation.
- Not done (on purpose): no-reload sending, live removal of deleted/expired messages, unread counts, blocking/reporting, notifications.
