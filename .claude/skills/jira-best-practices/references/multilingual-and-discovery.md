# Discovery & non-English content — the agent's language-safe backbone

This is the operational heart of the skill for an **agent** driving Jira through `jira-cli` or the **`mcp-atlassian`** MCP server. Two jobs: (1) **discover** the org's real configuration so you never guess values, and (2) handle **non-English** content and configured values correctly — which is fully normal and must never be "fixed" or translated.

## Non-English is normal — the stance

Many self-hosted instances have issue summaries, descriptions, and comments in a local language, AND configured values (issue type, status, priority, resolution, transition, link-type, component, custom-field names) authored in that language — e.g. status "Erledigt", type "Fehler", priority "Hoch". This is normal and correct.

- **Never auto-translate or rewrite a user's content.** Keep summaries/descriptions/comments in the team's working language. When you create or edit an issue on a non-English instance, write in that instance's language.
- **Never assume English configured values.** "Bug", "Done", "High" may not exist on the instance — the equivalent local string does.
- **Some orgs legally must be multilingual** (e.g. Canada's Official Languages Act) — so "standardise on English" is not universally valid advice. Per-team local language is legitimate.

## Discover before you act (agent-executable)

Map each thing you need to learn to the REST endpoint and the tool that fetches it. **Anchor logic on the language-independent column**, never on a display name.

| To learn… | DC REST v2 | `mcp-atlassian` tool | `jira-cli` | Language-safe anchor |
|---|---|---|---|---|
| Issue types (+ `subtask` flag, hierarchy) | `GET /issuetype` | `jira_get_all_projects` / issue meta | `jira issue view K --raw` | numeric `id` |
| Statuses **+ category** | `GET /status` | `jira_get_transitions` (per issue) | `jira issue view K --raw \| jq .fields.status` | **`statusCategory.key`** = `new`/`indeterminate`/`done`/`undefined` |
| Priorities / resolutions | `GET /priority`, `/resolution` | via issue/create meta | `--raw` then `jq` | `id` |
| Link types | `GET /issueLinkType` | `jira_get_link_types` | `jira issue link` help | `id` |
| Components (per project) | `GET /project/{key}/components` | `jira_get_project_components` | `--raw` | `id` |
| Fields (system + custom) | `GET /field` | `jira_search_fields`, `jira_get_field_options` | `jira issue view K --raw \| jq '.fields\|keys'` | **`untranslatedName`**, **`clauseNames`** incl. **`cf[NNNNN]`** |
| Valid transitions from current status | `GET /issue/{key}/transitions` | `jira_get_transitions` | `jira issue move K` (interactive once) | transition **`id`** |
| What a project actually *allows* | `/issue/createmeta`, `/issue/{key}/editmeta` | issue meta | — | reflects real config |
| Projects / boards / sprints | `/project`, agile API | `jira_get_all_projects`, `jira_get_agile_boards`, `jira_get_sprints_from_board` | `jira project list`, `jira board list`, `jira sprint list` | `id`/`key` |

> Read existing issues to *see* the values in use: pull a handful with `jira_search`/`jira issue list --raw` and inspect `fields.issuetype.name`, `fields.status.name` + `fields.status.statusCategory.key`, `fields.priority.name`, etc. That tells you the instance's real, possibly-localized vocabulary.

## The two rules that prevent localized-value bugs

### Rule 1 — anchor on keys, not names

- **JQL:** prefer `statusCategory = Done` (or `In Progress` / `To Do`, or the numeric ids 3/4/2) over `status = "Done"` / `status = "Erledigt"`. The category enum is fixed and language-independent.
- **Custom fields in JQL:** reference by **`cf[NNNNN]`** (from `clauseNames`) rather than the translated display name. System fields use English names in JQL; **custom fields use their *translated* name** — `cf[ID]` sidesteps that asymmetry entirely.
- **Transitions:** act by transition **`id`**, never by the localized transition name (transitions have *no* canonical English handle — AUTO-72). `jira_get_transitions` returns each transition's `id`, localized `name`, and target `to` status (with its `statusCategory`).
- **Recover canonical field names** via `untranslatedName` on `/field` (`jira_search_fields`).

### Rule 2 — get canonical strings via a service account (DC has no per-request override)

On Data Center, REST responses and webhooks are localized to the **authenticating / triggering user's profile language** — there is **no per-request language override** (`X-Force-Accept-Language` is **Cloud-only**; JRASERVER-74088 is still open). So:
- To get stable **canonical** strings, run discovery as a **dedicated service/integration account whose profile language is set to the canonical language** (e.g. English).
- Use an account with **admin-level visibility** — *permissions* decide which statuses/projects you even see (a separate axis from language). A low-privilege account returns a subset.
- **Webhook consumers:** don't string-match status names from webhook payloads — they arrive in the *triggering* user's language. Match on `statusCategory.key` / IDs instead.

## JQL: basic-search vs advanced-search asymmetry

- **Basic Search (Issue Navigator UI)** matches the **translated/localized** name a user sees.
- **JQL / Advanced Search** matches the **canonical** name (JRASERVER-39215, open since 2014). On a natively-non-English instance the canonical *is* the local string (the constant was created as "Erledigt"), so JQL needs that local string. Generic web advice "just use English in JQL" is **wrong** for instances whose constants were authored in a local language. The safe rule: **match the canonical string you discovered, or better, anchor on `statusCategory`/IDs.**

## Search & indexing caveats (set expectations; don't over-promise text search)

- **Indexing Language is a single instance-wide setting** controlling stemming + stop-words. Atlassian steers mixed-language instances to **"Other"**, which **disables stemming and reserved-word filtering** → exact whole-word matching, no stem expansion. There is **no per-field or per-language indexing** on DC.
- Search is **whole-word only** ("cannot search parts of words, only whole words" except stemmed) and **special characters aren't indexed** (only text and numbers).
- **CJK** (Chinese/Japanese/Korean): Lucene indexes overlapping 2-char **bigrams** and the query parser turns CJK queries into phrase queries — recall/precision differ materially from Latin-script search. Don't assume substring search works.
- **Umlaut/accent + wildcard is broken**: "Übersetzung" matches but "Übersetz*" returns nothing when the indexing language is German (JRASERVER-15006). Warn before relying on wildcard search of accented terms.
- **Custom-field *option* values can't be translated natively** (only the field name/description) — so localized dropdown values are simply free text in the admin's language (JRASERVER-40049); a Marketplace app is needed for multilingual options.

When a user's text search "isn't finding things," suspect these limits before assuming the data is missing.

## Practical creation/editing on a non-English instance

- Write summaries/descriptions/comments **in the instance's working language** — don't switch to English.
- When creating, set issue type / priority / etc. using the **exact discovered (possibly localized) values**, or by `id` where the tool allows.
- For transitions, resolve the transition **id** first (`jira_get_transitions`), then transition by id — robust against localization and per-user language.
- Remember the REST transition API **ignores transition screens**, so if Resolution is screen-only, **send the resolution in the transition payload** (this is where `jira-cli`/`mcp-atlassian` callers most often leave Resolution null — see `lean-config.md`).

## Sources
See `references/sources.md`. Key anchors (Tier A): `jira-issue-statuses-as-lozenges` (statusCategory keys); DC REST v2 reference + examples; JRACLOUD-71793/JRASERVER-74088 (no DC language override); `get-custom-field-ids`; `translating-resolutions-priorities-statuses-and-issue-types`; `configure-jira-application-options` (Indexing Language); JRASERVER-{39215,39009,71096,15006}, AUTO-72, JRASERVER-40049; Lucene CJK docs. Plus mcp-atlassian docs (Tier A/B) for the tool mapping.
