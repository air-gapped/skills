# /threat-model interview

> **Re-read note:** If you need this file mid-session and the Read tool
> reports "file unchanged", the prior result was evicted from context; reload
> with `cat .claude/skills/threat-model/interview.md` via Bash.

Build a threat model by interviewing the application owner using the
**four-question framework**. The owner is in the session; your job is to ask,
listen, ground their answers in the code where you can, and emit
`THREAT_MODEL.md` per `schema.md`.

The four questions (use this exact wording when you introduce each phase; the
phrasing is deliberate):

1. **What are we working on?**
2. **What can go wrong?**
3. **What are we going to do about it?**
4. **Did we do a good job?**

Reference: Shostack, *The Four Question Framework for Threat Modeling* (2024).

---

## Inputs

- `<target-dir>` (required): local checkout. You will read it to ground
  answers; you will not execute it.
- `--design-doc <path>` (optional): architecture or design document. Read it
  before asking Q1 so you can summarize back instead of starting cold.
- `--seed <THREAT_MODEL.md>` (optional): a prior `bootstrap` output. If
  present, the interview focuses on its `## 6. Open questions` and any threat
  rows with uncertain likelihood, instead of building from scratch.

---

## Provenance discipline

Every fact you write into `THREAT_MODEL.md` carries one of two tags in your
working notes:

- `[Code-verified]` — you read the source in `<target-dir>` and confirmed it.
- `[Owner-states]` — the owner told you and you have not (or cannot) verify it
  in code.

The final `THREAT_MODEL.md` does not include the tags inline (they would
clutter the table), but every `[Owner-states]` fact that affects a likelihood
or status score MUST be listed in `## 6. Open questions` as a follow-up to
verify. This is how an interview-mode threat model stays honest about what is
asserted versus observed.

---

## Method

Work through the four questions in order. Within each, ask one thing at a
time, wait for the answer, then move on. Do not dump a questionnaire.

### Q1 — What are we working on?

Goal: fill `## 1. System context`, `## 2. Assets`, `## 3. Entry points & trust
boundaries`.

If `--design-doc` was provided: read it, then **summarize the system back to
the owner in 4-6 sentences** and ask "Is this right? What did I miss?" This is
faster than asking them to describe it cold and surfaces drift between doc and
reality.

If no design doc: ask directly. Prompts, in order:

- "In two or three sentences, what does this system do and who uses it?"
- "What data does it hold or pass through that would be bad to lose, leak, or
  tamper with?" → assets table.
- "Where does input come from? Walk me from the outside in: network, files,
  CLI, other services, anything a user or another system hands you." → entry
  points.
- "Where does privilege change? Unauth to auth, user to admin, one service
  trusting another?" → trust boundaries.

While the owner answers, **read the code** in `<target-dir>` to corroborate:
look for `main`, route definitions, file-open calls, socket listeners,
deserializers, `argv` parsing. Where code confirms the owner, tag
`[Code-verified]`. Where code shows an entry point the owner did not mention,
ask about it: "I see a `/admin/debug` route in `routes.py:88`; is that
reachable in production?"

If `--seed` was provided: read its sections 1-3, summarize back, and ask only "What's
wrong or missing here?"

### Q2 — What can go wrong?

Goal: fill `## 4. Threats` rows (id, threat, actor, surface, asset).

Start open: **"For each of those entry points, what can go wrong? What's the
worst thing someone could do?"** Let the owner answer in their own words
first. Capture each answer as a candidate threat row.

When the owner stalls or stays vague, switch to structured prompts. Walk each
entry point from section 3 through STRIDE:

| | Ask |
|---|---|
| **S**poofing | "Could someone pretend to be a user or service they're not, here?" |
| **T**ampering | "Could input or stored data be modified in transit or at rest?" |
| **R**epudiation | "If someone did something bad here, would you know who?" |
| **I**nformation disclosure | "Could this leak data it shouldn't?" |
| **D**enial of service | "Could someone make this unavailable or too expensive to run?" |
| **E**levation of privilege | "Could someone end up with more access than they started with?" |

Not every letter applies to every entry point, and asking all six everywhere
burns the owner's patience on questions with an obvious "no". Ask the letters
that fit the kind of entry point:

| entry point kind | ask |
|---|---|
| network (HTTP, RPC, socket) | all six |
| IPC / message queue | T, I, E |
| file or directory input | T, I, D |
| CLI / job parameter | T, E |
| deserialization / plugin load | T, E |
| anything else | T, I |

Ask a skipped letter anyway the moment the owner's answer suggests it — the
table sets the default order, not a ceiling.

Then derive the domain-specific classes. From the section 1 context (stack,
language, deployment, data flows), name the 5-8 attack classes most likely
to matter for *this* system. Derive from what the owner described, not from
a generic checklist. Name classes at the granularity of "IDOR on dataset
rows" or "integer overflow on length fields", not "web vulnerabilities" or
"memory bugs".

Show the derived list to the owner: "Based on what you've described, these
are the classes I'd focus on. Anything you'd add from incidents you've seen
here or on similar systems?" Their additions are high-signal; weight them
above your own.

**Then check the derived list against the baseline for this repo's kind(s).**
A repo usually has more than one kind — a Rust service with a Helm chart is
`native` + `web-api` + `iac` — so take the union. Recognize the kind from
what section 1 established, not by asking:

| kind | recognize it by | baseline classes |
|---|---|---|
| `web-api` | a network entry point, a web framework in the manifests, or an OpenAPI/proto/GraphQL artefact | broken access control (IDOR, forced browsing, privilege escalation) · injection (SQL/NoSQL/OS/LDAP/template/header) · authentication and session failures (weak session, JWT flaws) · SSRF · XSS · CSRF or state-changing GET · cryptographic failures (plaintext transport or secrets) · security misconfiguration (default creds, debug on, permissive CORS) · unsafe deserialization or unsigned updates · insecure design (no rate limit, assumed-trust boundary) |
| `native` | C, C++, Rust, or Objective-C in the primary languages | buffer overflow, stack or heap · use-after-free and double-free · integer overflow feeding an allocation · format string · TOCTOU · OS command injection via `system`/`exec` |
| `mobile` | `AndroidManifest.xml`, `Info.plist`, or a `Podfile` in the tree | improper credential usage (hardcoded keys, token leakage) · insecure authentication or authorization · insecure communication (no cert pinning, cleartext traffic) · misconfiguration (exported components, debuggable build) · insecure data storage (world-readable prefs, unencrypted DB) |
| `iac` | `.tf`/`.hcl`, a Helm chart, `kustomization.yaml`, or CI pipeline definitions | over-permissive IAM or RBAC (wildcard actions, cluster-admin) · public network exposure (0.0.0.0/0, hostNetwork, public bucket) · plaintext secrets in config or env · privileged or root containers, missing securityContext · disabled TLS or unencrypted storage |
| `library` | none of the above — the default | injection via untrusted caller input · unsafe deserialization · path traversal in file-handling APIs · ReDoS or algorithmic-complexity DoS |

**The baseline is a recall aid, not a threat generator.** For each class,
look for a matching surface in what sections 1-3 already established. If one
exists and no threat covers it, that is a gap — raise it with the owner. If
no such surface exists here, **drop it silently**: a row emitted because a
checklist named it, with no surface behind it, is noise that costs the owner
attention on every future read of the model. Never present the baseline to
the owner as a list to answer — it is yours to check against, and the
question you bring back is about the specific gap you found.

Walk each section 3 entry point through STRIDE plus the derived-and-confirmed
classes. For each candidate threat, pin down: **actor** (who, from the enum in
`schema.md`), **surface** (which section 3 entry point), **asset** (which section 2 row).
Phrase the threat at the level where it survives a patch: "RCE via untrusted
WAV parsing", not "missing bounds check at line 412".

If `--seed` was provided: walk the seed's section 4 table row by row and ask "Does
this apply? Is the actor right?" Then ask "What's missing?"

### Q3 — What are we going to do about it?

Goal: fill `impact`, `likelihood`, `status`, `controls` for every section 4 row, and
fill `## 5. Deprioritized`.

For each threat row, ask:

- "What's in place today that stops or limits this?" → `controls`. Verify in
  code where possible (`[Code-verified]` vs `[Owner-states]`).
- "If it happened anyway, how bad is it?" → `impact` (read them the scale
  from `schema.md` if needed).
- "How likely is it that someone tries and succeeds, given the controls?" →
  `likelihood`. If past incidents, CVEs, or pentest findings exist for this
  surface, list them in `evidence` and weight likelihood up.
- "Is this mitigated, partially mitigated, unmitigated, or are you accepting
  the risk?" → `status`. **If the owner says "risk accepted", capture their
  reason verbatim** and put the row in section 5 with that reason.

The answer to Q3 is allowed to be "nothing, and we're not going to":
deprioritized threats with a recorded reason are a valid output. "Threat
modeling can result in knowing what we're not going to do and why."

After scoring, ask one closing question per **threat class** (not per row):
"If we could land one engineering control that makes this whole class go
away or shrink, what would it be?" Record the answer (or your own proposal
if the owner punts) as a section 8 row: `mitigation | threat_ids | closes_class |
effort`. Prefer controls that survive the next bug (sandboxing, type-safe
parsers, parameterized queries, CSP, allocation caps) over patches for the
last one.

### Q4 — Did we do a good job?

Goal: validate before writing.

- Read the draft section 4 table back to the owner, sorted by impact × likelihood.
  Ask: **"Does the top of this list match your gut? Is anything ranked too
  high or too low?"** Adjust.
- Ask: **"Is there anything you've been worried about that isn't on this
  list?"** Add it.
- Check coverage yourself: for every row in section 3, the `entry_point` name must
  appear verbatim in at least one section 4 `surface` cell, OR a section 5 row must say
  "<entry_point>: out of scope because …". If neither, either add a threat for
  that surface or ask the owner why it's safe and record the answer in section 5.
- Ask: **"Would you do this again for the next service? What would make it
  easier?"** Record the answer in your hand-back to the user (not in the
  file); it's feedback for this skill.

---

## Emit

Write `<target-dir>/THREAT_MODEL.md` per `schema.md`. Set `## 7. Provenance`:

```
- mode: interview
- date: <today>
- target: <target-dir> @ <git rev-parse HEAD if available>
- inputs: <design-doc path or "none">; <seed path or "none">
- owner: <name the user gave, or "present, unnamed">
```

Then hand back to the user:

1. Path to the file.
2. Top 5 threats by impact × likelihood, one line each.
3. The section 8 recommended mitigations, top 3 by (closes_class, effort asc).
4. Every `[Owner-states]` claim that affects a score, as a follow-up list.
   Format each as a section 6 bullet: `- [Owner-states] <claim>. Affects: <Tn
   field>. Verify by: <suggested check>.`
5. If `--seed` was provided: a short diff summary ("added T7-T9, downgraded T2
   likelihood from likely → possible because owner confirmed input is
   size-capped").
