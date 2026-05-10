# Custom model icons / SSO avatars — the perf history

For deployments that ran multi-pod + WebSockets in production before late 2025 and saw payload-driven crashes correlated with rolling updates, custom model icons (and SSO avatars) are a strong second suspect alongside #23733. Most of the bloat is fixed in ≥0.6.42, fully cleaned up by 0.9.4.

This page documents what was broken, what the fix was, and what to spot-check on the upgrade-target version.

## What was wrong (pre-0.6.37, before Nov 2025)

Open WebUI stores admin-uploaded model thumbnails inline. The flow:

1. Admin opens "Edit model" UI, uploads an icon (any image, any size).
2. Backend reads the file and stores it as a `data:image/png;base64,…` string in `model.meta.profile_image_url`.
3. The string lives in a Postgres row. **No image storage. No object storage. Just a multi-MB string in the DB row.**

The `/api/models` endpoint (called on every page load, every Socket.IO reconnect, every model picker open in chat UI) returned `model.info.meta` for every model — **including the full base64 string for every model with a custom icon.**

Numbers from issue #18950 (`Open WebUI deployment with ~350 models`, 2025-11-10):

- Response payload: **4.3 MB** (mostly base64 icons).
- Response time: **~4.7 seconds** (mostly because of an unrelated N+1 on `get_filtered_models` calling `has_access` per-model).

Numbers from issue #11934 (March 2025) and #12325 (April 2025):

- SSO avatars from Microsoft/Entra at 1024×1024 PNG — 1–10 MB per avatar.
- Admin panel `/api/v1/users` endpoint payload: **>100 MB** in some deployments.
- Admin page load: **30 seconds** for 5 users.

Combine this with rollouts at 1000 users:

- During a rolling update, when a pod terminates, every connected browser triggers a Socket.IO reconnect, which triggers a fresh `/api/models` call.
- N pods × M users × P MB simultaneously, on top of the WS amplification (#23733) on whatever conversations were in flight.
- Result: cascade — Valkey saturated, NGINX backend pool exhausted, Postgres connection pool full, more pods crash, more reconnects, etc.

This is the most plausible non-#23733 explanation for "we had to disable multi-pod and websockets."

## The fixes, chronologically

| Date | Version | Fix | What it does |
|---|---|---|---|
| 2025-11-07 | 0.6.37 | PR #19097 (`adam-skalicky`) | Preload user group IDs in `get_filtered_models` (kills N+1). Drop `profile_image_url` from list payloads. New `/api/v1/models/model/profile/image?id=X` endpoint with ETag header. |
| 2025-11-21 | 0.6.37 | tjbck commit `644287194` | Drop `profile_image_url` from `model.info.meta` field in `/api/models` and 14 frontend Svelte components. Single biggest perf win. |
| 2025-11-26 | 0.6.37 | Commit `384753c6c` | "drop profile_image_url field in responses" — applied across user/auth response models (4 files). |
| 2025-12-21 | 0.6.42 | PR #19519 / #18950 follow-up | "API response payload sizes were dramatically reduced by removing base64-encoded profile images from most endpoints, eliminating multi-megabyte responses caused by high-resolution avatars and enabling better browser caching." |
| 2025-12-21 | 0.6.42 | PR #19959 | Cache-Control headers on model avatar so admin model list updates immediately. |
| 2026-04-17 | 0.9.0 | PR #23796 | Reuse request DB session in `get_model_profile_image` (fewer DB roundtrips per icon fetch). |
| 2026-04-24 | 0.9.2 | PR #24015 (`f2cb63140`) | Default model avatar 302 → `/static/favicon.png`. Browsers cache once for all default-icon models. Solves "loading the chat home page hits 350 different image URLs." |
| 2026-04-24 | 0.9.2 | (release notes line 122) | "Model list performance. Model list API responses now strip base64 profile image data from paginated results, and model tags are fetched via a dedicated efficient query instead of loading all models." |
| 2026-05-09 | 0.9.3 | PR #24412 | Arena models reliably display configured profile images instead of falling back to the default icon. |
| 2026-05-09 | 0.9.3 | PR #24420 | `validate_profile_image_url` (sanitization) — "replace brittle profile_image_url allowlist with safe-scheme validation". |
| 2026-05-09 | 0.9.3 | New env var | `ENABLE_PROFILE_IMAGE_URL_FORWARDING` — set `False` to suppress 302 → external profile-image URLs (privacy/perf). |

## What to verify on the upgrade target

**Per `luke-wren`'s audit on issue #18950 (2025-11-19), some non-model endpoints retained base64 images longer than `/api/models` did:**

- `/api/v1/users` — admin user list. Heavy with many SSO-avatar users.
- `/api/v1/tools` — tool list. Heavy if tools have icons.
- `/api/v1/prompts/list` — prompt library. Heavy if prompts have thumbnails.
- `/api/v1/knowledge/list` — knowledge base list. Heavy if knowledge entries have thumbnails.

Spot-check on staging by hitting each as an admin user with a populated dataset and measuring response size. They *should* all be sub-100KB by 0.9.4. If any are still multi-MB, file an issue or set `OAUTH_PICTURE_CLAIM=""` and `OAUTH_UPDATE_PICTURE_ON_LOGIN=false` to stop new SSO avatars from being saved.

## How icons are served now

For DB models (the new path, 0.6.37+):

```
GET /api/v1/models/model/profile/image?id=<model_id>
GET /api/v1/users/{user_id}/profile/image
```

`backend/open_webui/routers/models.py:458-525`. Logic:

- `Models.get_model_meta_by_id(id)` returns `(meta, updated_at)`.
- If `profile_image_url` starts with:
  - `http` → `302 Location: <url>` if `ENABLE_PROFILE_IMAGE_URL_FORWARDING=True`, else fall through to favicon.
  - `data:image` → `StreamingResponse` of the decoded base64 with `Content-Disposition: inline` and `ETag: "{updated_at}"`.
  - other (`/static/...`) → `_safe_static_redirect_path(...)` validation then `RedirectResponse(/static/..., 302)`.
- Default fallback: `RedirectResponse('/static/favicon.png', 302)` — browsers cache one asset for all default-icon models.

ETag handling means the browser revalidates per-model only when the icon changes (driven by `meta.updated_at`). Bandwidth savings vs. the old "every page load = full base64 in JSON" path are 99%+.

## Are images sent over WebSocket?

**No.** `socket/main.py:357-365` explicitly excludes `profile_image_url`, `profile_banner_image_url`, `date_of_birth`, `bio`, and `gender` from what gets stored in `SESSION_POOL`. So the WS Redis hash never contains base64 images.

This was added in the 0.6.37 cycle and means the WS Redis state is small (~1KB per active session) regardless of custom-icon size.

## SSO avatars (separate but related concern)

When the IdP (Keycloak, Microsoft Entra, Okta) returns large profile pictures via the `picture` claim, every login round-trips the avatar through Postgres. Each user's `profile_image_url` ends up as a base64 string in the DB row.

Two env vars kill this:

```bash
OAUTH_PICTURE_CLAIM=""               # ignore the picture claim entirely
OAUTH_UPDATE_PICTURE_ON_LOGIN=false  # keep existing avatars but stop re-syncing
```

Set both. If the user wants their picture, they can upload a sensibly-sized one in the UI.

For Microsoft Entra/Azure AD specifically: the default `picture` claim returns the user's full Office 365 profile photo (1024×1024 PNG, often ~1 MB). Issue #12325 documented 30-second admin page loads with only 5 users in such a setup. Disabling the claim cut load time to <500ms.

## Are custom model icons safe to keep using?

Yes — they work fine in 0.6.42+. The new endpoint serves them on demand with browser ETag caching, and the frontend has been audited to not pull `profile_image_url` into list payloads.

But: **they still live as base64 strings in DB rows.** With hundreds of custom-icon models, those rows are large. There's no S3/blob backing for model icons in Open WebUI — this would be a feature request. For now, prefer:

- Default icons for the bulk of the model catalog.
- Use custom icons only for "featured" models that benefit from visual distinction.
- Keep custom icons under ~200 KB each (resize/optimize before uploading).

## See also

- `references/configuration.md` §OAuth-avatar for `OAUTH_PICTURE_CLAIM` / `OAUTH_UPDATE_PICTURE_ON_LOGIN` / `ENABLE_PROFILE_IMAGE_URL_FORWARDING`.
- `references/known-issues.md` for the source issue numbers behind this timeline.
