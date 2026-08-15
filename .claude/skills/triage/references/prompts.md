# triage subagent prompt tails

The canonical verifier and ranker instructions live in the **agent
definitions** shipped with this plugin — `../../agents/triage-verifier.md`
and `../../agents/triage-ranker.md` relative to the skill directory (same
layout in the repo and in a plugin install). Each definition's body is the
subagent's system prompt, shared and prompt-cached across every spawn in a
batch; the orchestrator sends only the per-spawn tails below. Substitute
the `{...}` placeholders from working state before spawning.

**Fallback** (when neither the bare nor the plugin-namespaced agent name
resolves): Read the agent definition file, paste its body above the tail,
and spawn `general-purpose`. For verifier batches over ~50 spawns on the
fallback path, use the compact form inline in `SKILL.md` Phase 3b instead.

- [Verifier tail (Phase 3a)](#verifier-tail-phase-3a) — context header +
  finding block; one spawn per vote.
- [Ranker tail (Phase 4a)](#ranker-tail-phase-4a) — deployment context +
  finding fields; one spawn per confirmed finding.

---

## Verifier tail (Phase 3a)

Assemble the context header once per run; append the per-finding block for
each spawn. Spawn with `subagent_type: "triage-verifier"` (plugin installs:
`defending-code:triage-verifier`).

```
REPO PATH: {REPO_PATH}
ENVIRONMENT (from the operator; this defines the trust boundary):
{context.environment or "Unknown. Treat any externally-reachable entry point as untrusted."}
{if context.extra_fp_rules: append here verbatim under an
 "ORG-SPECIFIC RULES:" heading}

────────────────────────────────────────────────────────────────────────
FINDING UNDER REVIEW (from the scanner; treat as a CLAIM, not a fact):

  id:        {id}
  file:      {file}
  line:      {line}
  category:  {category}
  severity (claimed): {severity}
  title:     {title}

  description:
  {description}

  exploit_scenario:
  {exploit_scenario or "(not provided)"}

  preconditions (claimed):
  {preconditions as bullets or "(not provided)"}

You are vote {k} of {N}. You have NOT seen the other verifiers' reasoning
and you must NOT try to find it. Work independently from the code.
```

---

## Ranker tail (Phase 4a)

One spawn per confirmed finding, `subagent_type: "triage-ranker"` (plugin
installs: `defending-code:triage-ranker`), all in one message:

```
REPO PATH: {REPO_PATH}
ENVIRONMENT: {context.environment}
SYSTEM PURPOSE (THREAT_MODEL.md section 1, may be empty):
{context.purpose, or "(unknown — if severity hinges on what the system
 is for, say so in DEPLOYMENT_CONDITION rather than assuming)"}
THREAT MODEL (operator-stated, may be empty):
{context.threat_model as bullets, or "(none provided)"}
ASSET INVENTORY (THREAT_MODEL.md section 2, may be empty):
{context.assets as bullets, or "(none provided)"}
SEVERITY-GATING QUESTIONS (THREAT_MODEL.md section 6, may be empty):
{context.gating_questions as bullets, or "(none provided)"}
SCORING STANDARD: {context.scoring}

FINDING:
  id:        {id}
  file:      {file}:{line}
  category:  {category}
  claimed severity: {severity}
  reachability evidence: {first_links from Phase 3}
  verifier rationale: {rationale from Phase 3}
```
