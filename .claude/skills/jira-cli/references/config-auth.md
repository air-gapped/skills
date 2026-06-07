# Config, authentication & instance discovery

## Install

`jira` is a single Go binary. Download from [releases](https://github.com/ankitpokhrel/jira-cli/releases), or:

```bash
brew install ankitpokhrel/jira-cli/jira-cli          # macOS/Linux Homebrew
docker run -it --rm ghcr.io/ankitpokhrel/jira-cli:latest   # try it
# Nix, AUR, Scoop, etc. — see the wiki Installation guide
```

Verify: `jira version` (this skill targets **v1.7.0**).

## The token lives in an env var, not the config

The single most important auth fact: **`JIRA_API_TOKEN` is read from the environment**, never stored in `.config.yml`. Put it in your shell rc (or `.netrc`/keychain), then run `jira init`.

```bash
export JIRA_API_TOKEN="<token-or-password>"   # add to ~/.bashrc / ~/.zshrc
```

## `jira init` — interactive bootstrap

`jira init` writes `~/.config/.jira/.config.yml`. It asks for installation type and connection details:

### Cloud
1. Create an API token at <https://id.atlassian.com/manage-profile/security/api-tokens> and export it as `JIRA_API_TOKEN`.
2. `jira init` → installation type **Cloud** → server URL (`https://your-org.atlassian.net`) → login email → done.
3. Cloud auth = email + **API token** (NOT your password).

### Server / Data Center (on-premise)
Choose installation type **Local**, then an auth type:

| Auth type | How |
|---|---|
| **basic** (most common) | `JIRA_API_TOKEN` = your Jira **password**; provide username at `init`. |
| **bearer** (PAT) | Get a Personal Access Token from your Jira profile; export it as `JIRA_API_TOKEN` **and** set `JIRA_AUTH_TYPE=bearer`. |
| **mtls** (client certs) | `jira init` → Local → auth type `mtls`; provide CA cert, client key, client cert. If `JIRA_API_TOKEN` is also set, it's used together with mTLS. |

> Non-English on-premise Jira: older Jira APIs don't return untranslated `issuetype` names, so epic/issue creation may fail. Fix by hand-filling `epic.name`, `epic.link`, and `issue.types.*.handle` in the generated `.config.yml`.

#### SSO-fronted Server/DC — use a PAT, not basic auth
If the on-prem Jira sits behind SSO (Okta, AD, SAML…), basic auth / email fails: `jira init` hits the SSO web login and gets back HTML, surfacing as `401 Unauthorized` or `Unable to generate configuration: invalid character '<' looking for beginning of value` (the `<` is the HTML login page). The CLI can't drive an interactive SSO flow. **Workaround (#477, #822):**
1. Generate a **Personal Access Token** in Jira (profile picture → Profile → Personal Access Tokens). PATs bypass SSO for API calls.
2. `export JIRA_AUTH_TYPE=bearer` and `export JIRA_API_TOKEN=<the PAT>`.
3. `jira init` → **Local** → bearer. At the login prompt, try your **username** (from your Jira profile page) if the email doesn't work — on Server/DC the identity is the username, not the email.

PATs work against an SSO-fronted self-hosted Server this way; PAT support requires Jira Server/DC 8.14+.

#### `.netrc` on Server/DC
If using `~/.netrc` instead of the env var, the `machine` field must be the **bare host** — `machine jira.corp.internal`, **not** `machine https://jira.corp.internal` (the `https://` prefix breaks resolution; #822).

## Config file & multiple instances

- Default path: `~/.config/.jira/.config.yml`.
- Override per-invocation: `-c <file>` or `JIRA_CONFIG_FILE=<file>`.
- One config file per Jira instance; switch by pointing at a different file. The `JIRA_API_TOKEN` env var must correspond to whichever instance you're calling.

```bash
JIRA_CONFIG_FILE=~/.config/.jira/cloud.yml  jira issue list
jira issue list -c ~/.config/.jira/onprem.yml
jira issue list -p OTHERPROJ                 # different project, same instance
```

### Alternative token sources
The token can also come from `~/.netrc` or the OS keychain instead of the env var — useful for keeping it out of shell history (#356). `.netrc` format (one line; `machine` = bare host, no scheme):

```
machine jira.example.com login you@example.com password <token-or-PAT>
```

`login` is the email on Cloud, the username on Server/DC bearer auth. The keychain option reads from the OS secret store (libsecret/`secret-tool` on Linux, Keychain on macOS).

## Instance discovery recipes (run these first, they're read-only)

A portable automation never assumes project keys, types, statuses, priorities, or custom fields. Learn them from the live instance:

```bash
# Identity + connectivity
jira me
jira serverinfo

# Projects you can use with -p — project list takes NO output flags;
# it prints a tab-separated KEY NAME TYPE LEAD table directly (header always present)
jira project list
jira project list | awk 'NR>1{print $1}'   # just the keys

# Boards (needed to find sprint IDs) — board list also takes no output flags
jira board list
jira sprint list --table --plain --columns id,name,state   # sprint list DOES take output flags

# What field VALUES does a project actually use? Read them off real issues.
jira issue list -p PROJ --plain --no-truncate --paginate 10

# Exact type / status / priority / resolution strings on one issue
jira issue view PROJ-123 --raw \
  | jq '.fields | {type:.issuetype.name, status:.status.name,
                   priority:(.priority.name // null),
                   resolution:(.resolution.name // null)}'

# Custom field IDs (customfield_XXXXX) and their current values
jira issue view PROJ-123 --raw | jq '.fields | with_entries(select(.key|startswith("customfield_")))'

# Link types in use across a project
jira issue list -p PROJ --raw \
  | jq -r '.[].fields.issuelinks[]?.type.name' | sort -u
```

### Transitions are workflow-specific
There is **no global list** of valid target states — they depend on the issue's current status and the project's workflow. To learn the allowed transitions for an issue, run `jira issue move PROJ-123` once **interactively**: it presents exactly the states the workflow permits from the current status. Then script the chosen state string. (Or read the workflow in the Jira admin UI.)

## Config sanity checks

```bash
jira me                                   # 401 here → token/auth-type problem
jira serverinfo                           # confirms URL + reachability
jira issue list --plain --paginate 1      # confirms project + permissions
jira <cmd> <subcmd> --debug               # HTTP-level trace for any failure
```
