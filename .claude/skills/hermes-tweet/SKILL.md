---
name: hermes-tweet
description: >-
  Use Hermes Tweet when a Hermes Agent workflow needs X/Twitter search, trend
  checks, account reads, monitors, media, draws, extraction, or approval-gated
  publishing through the native Hermes Tweet plugin.
when_to_use: >-
  Trigger on "Hermes Tweet", "X/Twitter from Hermes", "search tweets with
  Hermes", "monitor this hashtag", "read tweet replies", "check X trends",
  "export followers", "post from Hermes", "reply on X", "Hermes Agent Twitter
  plugin", or any Hermes Agent workflow that needs X/Twitter reads or controlled
  account actions.
---

# Hermes Tweet

Use this skill to route Hermes Agent X/Twitter work through Hermes Tweet, the
native Hermes Agent plugin published at:

https://github.com/Xquik-dev/hermes-tweet

## Operating Mode

Act as a Hermes Tweet operator, not as a generic social media API client.

Prefer:

- `tweet_explore` before live calls
- `tweet_read` for catalog-listed read-only routes
- `tweet_action` only after explicit approval and runtime action-gate enablement
- runtime environment secrets instead of chat-provided credentials
- concrete catalog paths instead of guessed endpoint URLs

Stop if Hermes Tweet is unavailable. Do not simulate X/Twitter results or route
around the plugin with browser automation when the Hermes Tweet tools fit.

## Install

Install and enable Hermes Tweet on the Hermes runtime host:

```bash
hermes plugins install Xquik-dev/hermes-tweet --enable
```

Hermes should prompt for `XQUIK_API_KEY` during interactive install. In
non-interactive installs, configure the key in the runtime environment or
Hermes env file before calling live read routes.

For remote gateway and desktop profiles, configure Hermes Tweet where plugin
code runs. The chat surface should not receive API keys unless it is also the
runtime host.

## Routing

### Explore

Use `tweet_explore` when the exact route is unknown. It should discover
available catalog endpoints without making a live network call.

Use it to find routes for:

- tweet and user search
- replies, quotes, likes, and timelines
- trends, radar, monitors, and webhooks
- media, draws, exports, and extraction jobs

### Read

Use `tweet_read` for catalog-listed read-only routes.

Good read workflows:

- social listening
- launch monitoring
- support triage
- creator or brand research
- giveaway and community audits
- trend and account context checks

Return concise evidence and preserve privacy. Do not publish private account
details into public PRs, issues, comments, docs, or logs.

### Act

Use `tweet_action` only when all are true:

1. the user explicitly approved the exact action
2. `HERMES_TWEET_ENABLE_ACTIONS=true` is configured in the runtime
3. the target, payload, expected effect, and rollback limits are clear

Action-like tasks include posting, replying, reposting, liking, following,
unfollowing, DMs, media uploads, monitor changes, and webhook changes.

## Safety Rules

- Never ask for API keys, browser session artifacts, or account credentials in
  chat.
- Never invent endpoint paths. Discover them with `tweet_explore`.
- Never bypass the action gate.
- Never publish or mutate account state without explicit approval.
- Keep action payloads small, reviewable, and tied to one user-approved target.
- Use read-only workflows when the task is research, monitoring, or triage.

## References

- Hermes Tweet: https://github.com/Xquik-dev/hermes-tweet
- Hermes Agent plugin docs: https://github.com/NousResearch/hermes-agent
