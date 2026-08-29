# AI on self-managed GitLab — licence gates and your own inference

**Tag convention.** Untagged claims were verified against a primary source on
2026-08-29. **[A]** = reported but not independently re-verified. **[?]** =
claimed somewhere but contradicted or unsupported when checked.

## Decision table

| Want | Licence needed | Own vLLM/SGLang/Ollama? | Zero egress? |
|---|---|---|---|
| Any GitLab Duo feature at all | **Premium or Ultimate.** Free tier gets none | — | — |
| Duo Core (Code Suggestions + Agentic Chat) | Premium/Ultimate, auto-included, ≥18.0 | **no** — requires GitLab's cloud AI Gateway | **no** |
| Duo Pro / Duo Enterprise, GitLab-hosted models | Premium/Ultimate + seat-based add-on | no | no |
| **Duo Self-Hosted** — Duo features against your model | Premium/Ultimate + **Duo Enterprise** add-on (seats) | **yes**, vLLM is the reference platform | not without the offline path below |
| **Duo Agent Platform Self-Hosted, offline licence** | Premium/Ultimate + **Agent Platform Self-Hosted** add-on (flat-fee ELA) + a sales-approved **offline cloud licence** | **yes** | **yes** |
| **GitLab MCP server** | **Free, Premium or Ultimate — no add-on**, GitLab ≥19.2 | you supply the model entirely | **yes** |
| External agent via REST/GraphQL + webhooks | **none** — a PAT on Free or CE | yes | yes |

**The short answer for an unlicensed instance: run the MCP server.** It is the
only GitLab-maintained AI-adjacent surface that is free, and since 19.2 it needs
neither Duo nor the cloud AI Gateway.

## CE vs Free — settle this before anything else

They are different things and only one of them can ever run Duo.

The chart defaults to **EE**. From the chart's `values.yaml` at master:

```yaml
## https://docs.gitlab.com/charts/installation/deployment#deploy-the-community-edition
edition: ee
```

> "By default, the Helm charts use the Enterprise Edition of GitLab... If
> desired, you can instead use the Community Edition which is licensed under
> the MIT Expat license... `--set global.edition=ce`."

CE is still a real, separately-built option — the `gitlab-webservice-ce` image
repository is live and populated. **[A]** on it still being published for a
specific 19.x tag; the registry API's tag listing cannot sort
reverse-chronologically, so this was not tag-verified.

**Almost every chart install is EE-with-no-licence ("Free tier"), not CE**,
because nobody sets `global.edition=ce` by accident.

**CE cannot accept a licence at all.** The licence gate is what turns Duo on, so
no Duo tier is reachable on CE — not even by buying one. If AI features are ever
wanted, staying on the EE image is the prerequisite, licensed or not.

## Duo tiering as of 19.x

Every Duo docs page carries `Tier: Premium, Ultimate`. **Free-tier self-managed
gets no GitLab AI features.**

| Product | Requires | Notes |
|---|---|---|
| **Duo Core** | Premium/Ultimate, ≥18.0, auto-included | Code Suggestions + Agentic Chat. Non-Agentic Chat **removed from Core 2026-05-21 (19.0)**. **Unavailable on an offline licence**, because it requires GitLab's cloud AI Gateway |
| **Duo Pro** | + seat-based add-on | Code Suggestions, Non-Agentic Chat, IDE explain/refactor/fix/test-gen |
| **Duo Enterprise** | + seat-based add-on, self-managed ≥17.3 | adds Code Review, Root Cause Analysis, Vulnerability Explanation/Resolution, MR summaries. **This is the add-on Duo Self-Hosted requires** |
| **Duo Agent Platform** | Premium/Ultimate | GA 18.8+ |
| **Duo Agent Platform Self-Hosted** | separate add-on, ≥18.8, **flat-fee ELA** | required for **offline-licence** customers wanting self-hosted models. Online-licence sites can use self-hosted models in the Agent Platform without it, billed by usage |

## Duo Self-Hosted

**Licence, verbatim and unambiguous:**

> "To use GitLab Duo features with GitLab Duo Self-Hosted, you must have the
> GitLab Duo Enterprise add-on. This applies even if you can use these features
> with GitLab Duo Core or GitLab Duo Pro when GitLab hosts and connects to those
> models through the cloud-based AI Gateway."

Bringing your own GPU does not buy you out of the add-on. It buys you control of
where inference happens.

**Version history:** feature-flagged (`ai_custom_model`) from 17.1 → enabled
self-managed 17.6 → flag removed 17.8 → GA **17.9** → extended to Premium at
18.0. Agent Platform self-hosted models: 18.8. AI Gateway internal TLS: 19.1.
TLS cipher config: 19.2. Cosign-signed FIPS images: 19.3.

**vLLM is the reference platform, not a tolerated third party.** The official
offline runbook deploys `docker.io/vllm/vllm-openai` directly, and the
serving-platforms page states: *"You should install version **v0.18.1** or
later."* A prescriptive "Serve GPT OSS 120B with vLLM" guide ships alongside it.

**The gateway speaks LiteLLM.** *"The AI Gateway supports multiple LLM providers
through LiteLLM"* — so any LiteLLM-compatible provider is mechanically
reachable, while the *validated* list is: vLLM (self-hosted), AWS Bedrock,
Amazon Bedrock Mantle, Gemini Enterprise Agent Platform, Azure OpenAI,
Anthropic, OpenAI. Multiple models and platforms can serve different features on
one instance.

**The version gate churns hard.** Secondary copies of this page still show a
v0.6.4.post1 pin — roughly a dozen vLLM minors of drift. Read the canonical page,
and note it **moved**: `.../administration/self_hosted_models/supported_llm_serving_platforms/`
now 403s while `.../administration/gitlab_duo_self_hosted/supported_llm_serving_platforms/`
returns 200. A 403 on a GitLab docs URL is more often a stale path than a block.

### Two config traps that cost an afternoon

**The endpoint URL must be suffixed with `/v1`.** Default vLLM →
`https://<hostname>:8000/v1`. Behind a proxy or load balancer the port may be
omitted, but the `/v1` never is.

**The model identifier is prefixed, and the name is not the one you served
under.** Query the running server and use `data.id` verbatim:

```bash
curl --header "Authorization: Bearer API_KEY" \
     --header "Content-Type: application/json" \
     http://your-vllm-server:8000/v1/models
```

If `data.id` is `Mixtral-8x22B-Instruct-v0.1`, the GitLab model identifier is
**`custom_openai/Mixtral-8x22B-Instruct-v0.1`**.

**Production latency:** serve with `--disable-log-requests`. Upstream reports
verbose request logging as a notable latency cost under load.

### The AI Gateway is mandatory, and it is not open source

- **Always required** for any Duo Self-Hosted or Agent Platform Self-Hosted
  configuration. There is no direct GitLab→model path.
- **It ships as a subchart of the GitLab chart** from 10.x — `ai-gateway`,
  gated on `ai-gateway.install` (**`false` by default**), *"a single pod serving
  both the HTTP API (for AI features like code suggestions) and the gRPC
  duo-workflow-service"*, with service discovery under `global.ai-gateway`.
  Two things follow: it is one values flag away from being deployed, and it is
  **another image source for an air-gap mirror list**.
  **Check the dependency channel before trusting it** — at chart 10.3.1 the
  pinned `ai-gateway` 0.15.1 comes from a repository path ending `/helm/devel`.
- Source is public: `gitlab-org/modelops/applied-ml/code-suggestions/ai-assist`.
- **Licence is the GitLab Enterprise Edition licence**, not MIT or Apache.
  Inspectable and self-buildable; "open source" in the OSI sense is the wrong
  word. Its use is governed by the EE licence and, functionally, by a JWT auth
  flow tying it back to a licensed instance.
- Image:
  `registry.gitlab.com/gitlab-org/modelops/applied-ml/code-suggestions/ai-assist/model-gateway:self-hosted-vX.Y.Z-ee`.
  A Helm chart exists, taking `serviceAccount` annotations and
  `extraEnvironmentVariables` (the documented path for AWS IRSA and for secret
  references).
- **Footprint is trivial:** ~340 MB image, minimum 512 MB RAM, 2 CPUs, **no
  GPU**. All GPU cost sits on the model server you already run.
- Config: `AIGW_GITLAB_URL`, `AIGW_GITLAB_API_URL`,
  `AIGW_SELF_SIGNED_JWT__SIGNING_KEY` / `__VALIDATION_KEY`,
  `DUO_WORKFLOW_AUTH__ENABLED`, `DUO_WORKFLOW_SELF_SIGNED_JWT__*`,
  `AIGW_CUSTOMER_PORTAL_URL`, `DUO_WORKFLOW_AUTH__OIDC_CUSTOMER_PORTAL_URL`.

**The trap that costs 20 seconds per request.** The AI Gateway reaches out to
`customers.gitlab.com` for licence validation by default:

> "The AI Gateway requires outbound access to... customers.gitlab.com for
> license validation, unless you use an offline license."

If that host is unreachable and `AIGW_CUSTOMER_PORTAL_URL` /
`DUO_WORKFLOW_AUTH__OIDC_CUSTOMER_PORTAL_URL` are not overridden to the local
instance, **every request eats a 20-second delay** — a timeout, not a clean
failure. On a restricted network this presents as "the AI is incredibly slow",
not as an egress error.

## Air-gapped Duo

The offline path exists and is documented, but it starts with sales, not config:

> "you must receive an opt-out exemption of cloud licensing prior to purchase.
> For more details, contact your GitLab sales representative."

With an offline licence **and** the Agent Platform Self-Hosted add-on, the
instance does not contact CustomersDot (`customers.gitlab.com`), the cloud AI
Gateway (`cloud.gitlab.com`), or the Cloud Workflow Service
(`duo-workflow-svc.runway.gitlab.net`). Billing becomes a flat-fee ELA rather
than usage metering.

Side-load via `skopeo` or physical media: the AI Gateway image
(`self-hosted-vX.Y.Z-ee`), the Agent Platform Flows executor image, the vLLM
image, and the model weights (`hf download` or `git lfs` on a connected
machine). FIPS-validated, cosign-signed AI Gateway images exist for regulated
environments from 19.3.

**There is no unmediated fully-disconnected deployment.** Without the
sales-issued offline licence the instance cannot validate, and Duo stays off.

**What leaves the network on an *online* licence with self-hosted models:**
billing metadata only — `InstanceId`, a SHA-256-derived de-identified
`GlobalUserId`, call count, timestamp.

> "Inference data, including code inputs, model prompts, and model responses,
> does not leave the customer network... GitLab does not capture which model or
> model provider the customer uses."

That is GitLab's own assertion about software you build from their source. It is
documented, not independently audited.

## The zero-licence path: the MCP server

**This is the actionable answer for a Free-tier install, and it is new.**

GitLab 19.2 (GA 2026-08-04) **decoupled the MCP server from Duo entirely**. From
the resolving comment on the upstream issue:

> "The MCP server now has its own independent availability toggle, completely
> decoupled from Duo Agent Platform (DAP) and Duo availability settings. On
> self-managed instances, an admin enables it via Admin > Settings > General >
> Visibility and access controls > Enable MCP server."

An earlier comment on the same issue states the mechanism plainly: *"MCP server
itself does not require the cloud AI Gateway to function; it only needs to be
reachable from clients on the same secured network as your GitLab instance."*

The MCP server docs page carries `Tier: Free, Premium, Ultimate`.

**Consequences:**

- A Free-tier EE instance on ≥19.2 can serve GitLab's own MCP tool surface to
  any MCP-capable agent, backed by whatever model you like.
- No add-on, no seat count, no egress, no AI Gateway.
- Below 19.2 this does not work — the MCP server was gated behind Duo's
  cloud-gateway requirement, which was a real filed bug, not a docs gap.

**Fallback if MCP is unavailable or administratively locked:** the REST and
GraphQL APIs plus webhooks work unconditionally on Free *and* CE with a PAT.
Same practical outcome — an external agent on your own inference reading and
writing issues, MRs and pipelines — at the cost of more integration work and no
GitLab-maintained tool schema.

## Air-gap interaction

Standard self-managed Duo requires egress to GitLab's AI Gateway and is
therefore **off** at an air-gapped site until the offline-licence process
completes. The MCP server is not affected. → `references/air-gap.md`
