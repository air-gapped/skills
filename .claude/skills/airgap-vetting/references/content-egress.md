# Q6 — Content Egress & Offline Feature Degradation (+ identity/inbound sub-checks)

**Contents:** AI assist features · gravatar · maps/GeoIP · link previews ·
CDN frontend assets · the feature-degradation-table green flag. Sub-checks:
identity against vendor cloud · inbound expectations · connectivity probes.

Q1 covers telemetry — metadata *about* usage. Q6 covers features that ship
user **content** (code, queries, schemas, email hashes, geo lookups) and
the inventory of what silently dies offline. "Runs offline" can mean "runs
with its three best features silently dead." Output: a per-feature table —
feature → destination → default on/off → kill switch → what's lost offline.

## AI assist features (the defaults-on risk)

AI/LLM-assist features route user content (code, queries, schemas, panel
data, chat) to a hosted model API. Vet three things:

1. **Destination** — vendor-run AI gateway vs a configurable
   OpenAI-compatible endpoint.
2. **Default** — some products switch AI features ON automatically the
   moment a license or provider key is present; "off until configured" is
   the safe pattern.
3. **Self-hosted path** — can the endpoint be pointed at an internal LLM
   (vLLM/Ollama-class), and is that path documented rather than implied?

**Grading rule:** AI feature with a documented self-hosted-LLM path =
documented-degradation sub-case of `possible-with-mirror`. Default-on AI
routed only through vendor cloud caps the grade.

## Gravatar — email-hash leak by default

Avatar features commonly fetch
`secure.gravatar.com/avatar/<md5(email)>` — an email-hash leak, frequently
on by default in self-hosted web apps. Find the disable setting, then
**verify with a network trace, not the config key** — gravatar toggles
have a history of being ignored in some code paths.

## Maps / GeoIP

Map widgets default to vendor tile services; GeoIP enrichment
auto-downloads databases (the MaxMind GeoLite2 pattern). Hunt the tile/
GeoIP service hostnames in config defaults, plus the disable and
self-host/mirror settings. Key lesson: **a documented kill switch ≠ clean
offline degradation** — disabling a map/tile service has broken adjacent
features in real products; test the feature offline, not the flag.

## Link previews / URL unfurling

Server-side fetches of user-posted URLs. Off-by-default with an explicit
SSRF blacklist required to enable is the good pattern; anything else gets
disabled inside a gap and noted in the degradation table.

## CDN frontend assets — a layer backend greps miss

Backend clean, binary runs with zero egress, but the web UI pulls
fonts/JS/CSS from CDNs → broken or half-styled UI inside the gap.

- Static: grep built HTML/templates/bundles for
  `fonts\.googleapis\.com|fonts\.gstatic\.com|unpkg\.com|cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com`.
- Dynamic: browser console errors while under egress deny
  (`references/dynamic-harness.md` step 6).

## Green flag: a published feature-degradation table

A published **feature-degradation table** is to Q6 what an image list is to
Q4 — the vendor enumerates what dies offline, per feature, with the
mirror/disable path for each. Its absence means this vet must build that
table itself; its presence (typically on a dedicated air-gap/offline docs
page) is strong Q8 evidence.

---

## Sub-check: identity against vendor cloud (feeds Q3)

The engine can be fully self-hosted while the *login* still needs the
internet. Patterns to check:

- **Mandatory account login on a locally-running tool** — search the issue
  tracker for login-requirement complaints; long-running open issues are
  the signal.
- **Login-optional ≠ offline-capable** — a lifted login requirement does
  not mean the product runs with zero egress; vet the two separately.
- **Offline workarounds that must be pre-configured while still online** —
  if the exemption/config requires reaching the vendor cloud once, it must
  happen before the gap closes; call this out explicitly in the report.
- **Open client, closed coordination server** — open-source clients do not
  make the control plane self-hostable; a community substitute server is a
  separate product to vet.
- **License-via-cloud-account** — self-hosted paid features that require
  creating the org/license in the vendor's cloud first; trial licenses
  frequently don't work air-gapped at all.

Grading: cloud-login with no offline workaround = `proxy-in-disguise`
trigger.

## Sub-check: inbound expectations

Rare but invisible to every egress-focused test:

- **Chat-platform integrations** — Events-API-style integrations require a
  **public inbound HTTPS URL reachable from the platform's cloud**;
  Socket-Mode-style integrations (outbound WebSocket) work behind a
  firewall. Check which mode the candidate's integration uses (Slack
  documents both).
- **Mobile push** — only the vendor holds the Apple/Google push keys, so
  self-hosted deployments typically relay push notifications outbound
  through vendor infrastructure — un-mirrorable coupling by design. Check
  what the payloads carry and whether push can be disabled.

## Sub-check: connectivity probes / hardcoded resolvers (feeds Q4)

Captive-portal-style checks (`connectivity-check.*`) and hardcoded
`8.8.8.8`/`1.1.1.1` resolvers show up directly in the dynamic DNS/egress
capture. Interpret a probe-then-behavior-fork as a Q4 red flag, not benign
noise.
