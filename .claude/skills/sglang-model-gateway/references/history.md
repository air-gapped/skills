# Chat history backends — `/v1/responses`, `/v1/conversations`, MCP sessions

This is the operator-side reference for the gateway's `--history-backend` flag and the OpenAI-compat surface that depends on it. Most operators don't need this — see "When you can ignore this entirely" first.

## What gets persisted

The gateway routes three kinds of stateful traffic through the configured `--history-backend`:

| Endpoint group | Routes (`src/server.rs:549-574`) | What lives in the backend |
|---|---|---|
| **Responses API** | `POST /v1/responses`, `GET /v1/responses/{id}`, `POST /v1/responses/{id}/cancel`, `DELETE /v1/responses/{id}`, `GET /v1/responses/{id}/input_items` | Background-response objects, their input items, status (`queued`/`in_progress`/`completed`/`failed`/`cancelled`), output payloads |
| **Conversations API** | `POST /v1/conversations`, `GET/POST/DELETE /v1/conversations/{id}`, `GET/POST /v1/conversations/{id}/items`, `GET/DELETE /v1/conversations/{id}/items/{item_id}` | Conversation metadata + ordered item lists (messages, tool calls, results) |
| **MCP sessions** | (no dedicated routes — internal) | Multi-turn agentic state created by `/v1/responses` runs that loop over MCP tool calls |

Plain `POST /v1/chat/completions` and `POST /v1/completions` do **not** use the history backend. Those are stateless — the client sends the full transcript on every call and the gateway forwards it. This is the OpenAI SDK's default mode and what most clients use.

## The two OpenAI features that need persistence

### `/v1/responses` — agentic background runs

The newer OpenAI Responses API. The client submits a prompt and the server runs a multi-turn agentic loop — calling MCP tools, making follow-up model calls, optionally streaming partial output. Each response gets an ID and can be:

- Polled later: `GET /v1/responses/{id}`.
- Cancelled: `POST /v1/responses/{id}/cancel`.
- Inspected: `GET /v1/responses/{id}/input_items`.
- Deleted: `DELETE /v1/responses/{id}`.

Server-side persistence matters because the loop may take seconds-to-minutes to converge, especially with MCP tool calls. The client doesn't have to hold a connection. It can disconnect, fail over, come back with a different process, retrieve by ID. **State has to live somewhere.**

If you only ever drive `/v1/responses` synchronously (single client, single connection, no retrieval-by-ID), `memory` works. If you scale the gateway to N replicas and a client may poll a different replica than the one that started the run, you need a shared backend.

### `/v1/conversations` — stored conversational context

Stored multi-turn conversations the model can be pointed at by ID instead of the client resending the full transcript on every call. Two reasons it exists:

1. **Bandwidth / token economy** — long transcripts are expensive to retransmit on every turn. A stored conversation lets the client send only the new turn.
2. **Cross-model context reuse** — the same conversation can drive multiple models in your fleet (route turn 1 to Llama-70B, turn 2 to Gemma-3-4B, etc.) without the client re-stitching the transcript.

If your clients always send the full transcript every turn (the OpenAI SDK default), you don't need this.

## The privacy / proxy angle

This is the strongest case for using a non-`memory` backend. Per the upstream doc:

> "Conversation and response history is stored at the router tier (memory, none, Oracle ATP, or PostgreSQL). The same history can power multiple models or MCP loops without sending data to upstream vendors."

Concretely: with `--backend openai --worker-urls https://api.openai.com`, the gateway proxies OpenAI-compatible traffic to a vendor (OpenAI, xAI, Azure OpenAI, etc.) **but stores the rolling conversation in your local backend**. The vendor only sees the current turn, never the full transcript. Multiple models in your fleet can share the same conversation. This is the "enterprise privacy" claim — useful for regulated workloads where transcripts can't leave your infra.

This is the niche where `--history-backend redis|postgres|oracle` clearly earns its keep.

## When you can ignore this entirely

```
--history-backend none
```

Pick this if all the following hold:

- Clients use `/v1/chat/completions` and `/v1/completions` only — never `/v1/responses` or `/v1/conversations`.
- No MCP tooling that runs through the gateway's agentic loop.
- No need to proxy a vendor while keeping local transcripts.

This is the common case. Don't pay for Redis you don't need.

## Backend catalog

From `src/main.rs:437`: `value_parser = ["memory", "none", "oracle", "postgres", "redis"]`.

| Backend | When to pick it | Notes |
|---|---|---|
| `memory` (default) | Single-replica gateway, dev/test, latency-sensitive prototyping | Lost on restart. **Not shared across replicas.** |
| `none` | You don't use stateful endpoints | Calls to `/v1/responses` / `/v1/conversations` will return errors or empty results — verify with your clients before flipping to `none`. |
| `redis` | Default choice for a multi-replica gateway that needs shared history. Fast, simple ops, retention is configurable. | Env vars: `REDIS_URL`, `REDIS_POOL_MAX`, `REDIS_RETENTION_DAYS` (or CLI: `--redis-url`, `--redis-pool-max-size`, `--redis-retention-days`). Default retention 30 days; `-1` for persistent. |
| `postgres` | You already run Postgres in the cluster and want one persistence layer for everything. Survives restarts. | Env: `POSTGRES_DB_URL`. |
| `oracle` | Enterprise / Oracle Autonomous Database shop. The gateway has first-class ATP wallet + TNS support. | Env: `ATP_DSN` *or* `ATP_TNS_ALIAS` + `ATP_WALLET_PATH`; `ATP_USER`, `ATP_PASSWORD`, `ATP_POOL_MIN`, `ATP_POOL_MAX`. |

For full env-var details and connection-string formats, see the upstream docs (`docs/advanced_features/sgl_model_gateway.md` "History and Data Connectors") rather than duplicating them here.

## Mesh vs history — they are NOT the same

A common confusion when planning multi-replica deployments:

| Concern | Mechanism | Storage layer |
|---|---|---|
| Worker registry, cache_aware tree, rate-limit window shared across gateway replicas | `--enable-mesh` | CRDT gossip between gateway pods. No external service. |
| `/v1/responses` / `/v1/conversations` shared across gateway replicas | `--history-backend redis|postgres|oracle` | External database. |

You typically want **both** when running N gateway replicas with stateful endpoints. Mesh handles routing-locality state; history backend handles client-visible persistence. Don't try to make one cover the other — they're different consistency models (eventual gossip vs transactional DB).

## Redis recipe (the most common shared-history setup)

Minimal K8s wiring:

```yaml
# Redis (use Bitnami chart, KubeBlocks, or a managed service in production)
# Then on the gateway:
env:
  - name: REDIS_URL
    valueFrom:
      secretKeyRef: {name: gateway-redis, key: url}     # redis://user:pass@redis-master:6379/0
args:
  - --history-backend=redis
  - --redis-pool-max-size=16
  - --redis-retention-days=30        # or -1 for persistent
```

Considerations:

- Use a separate Redis from any application-level cache. The gateway owns these keys; collisions with app data create silent corruption.
- Set `--redis-retention-days` based on how long clients realistically retrieve responses by ID. Most agentic flows finish in seconds-to-minutes; 30-day default is generous.
- Redis HA (Sentinel / Redis Enterprise) only matters if `/v1/responses` retrieval is on a critical client path. For "fire-and-forget" agentic runs where the client tolerates losing the response, single-instance Redis is fine.

## Postgres recipe (when you already run Postgres)

```yaml
env:
  - name: POSTGRES_DB_URL
    valueFrom:
      secretKeyRef: {name: gateway-postgres, key: url}  # postgres://user:pass@host:5432/gateway_history
args:
  - --history-backend=postgres
```

Schema is created on first connect. No migration tooling needed from the operator side — verify by checking the gateway log for "history backend ready" on startup.

## Oracle recipe

If you have an Oracle ATP wallet and TNS alias:

```yaml
env:
  - name: ATP_TNS_ALIAS
    value: "sglroutertestatp_high"
  - name: ATP_WALLET_PATH
    value: "/wallet"
  - name: ATP_USER
    valueFrom: {secretKeyRef: {name: atp-creds, key: user}}
  - name: ATP_PASSWORD
    valueFrom: {secretKeyRef: {name: atp-creds, key: password}}
volumeMounts:
  - {name: wallet, mountPath: /wallet, readOnly: true}
volumes:
  - name: wallet
    secret: {secretName: atp-wallet}
args:
  - --history-backend=oracle
```

Or with a raw DSN:

```yaml
env:
  - name: ATP_DSN
    value: "(description=(address=(protocol=tcps)(port=1522)(host=adb.region.oraclecloud.com))(connect_data=(service_name=svc_high)))"
  - name: ATP_USER
    valueFrom: {secretKeyRef: {name: atp-creds, key: user}}
  - name: ATP_PASSWORD
    valueFrom: {secretKeyRef: {name: atp-creds, key: password}}
args:
  - --history-backend=oracle
  - --oracle-dsn=$(ATP_DSN)
```

`ATP_POOL_MIN` and `ATP_POOL_MAX` tune the connection pool — defaults are usually fine.

## Decision summary

```
Are clients using /v1/responses or /v1/conversations? Or is the gateway proxying a vendor for privacy?
├── No → --history-backend none. Done.
└── Yes:
    ├── Single-replica gateway, can lose state on restart? → memory
    ├── Single-replica, must survive restarts? → redis (or postgres if you already run it)
    └── Multi-replica gateway? → redis|postgres|oracle (must be shared, never memory)
```

## Pitfalls

1. **`memory` backend with multiple gateway replicas silently degrades the API.** Each replica has its own in-memory state. A client that creates a response on gateway-A and polls gateway-B gets `404`. Always pick a shared backend for N>1 replicas.
2. **Mesh does NOT sync history.** Don't expect `--enable-mesh` to substitute for a Redis. They cover different concerns. Run both if you need both.
3. **Retention-day defaults are silent.** Redis defaults to 30-day retention; clients retrieving older responses get nothing. Set `--redis-retention-days=-1` for persistent storage if you don't want this.
4. **Postgres URL must be reachable from inside the gateway pod.** The most common K8s mistake is a `localhost` URL inherited from a dev `.env` file. Use the in-cluster Service DNS name.
5. **Oracle wallets must mount as a directory containing `cwallet.sso`, `tnsnames.ora`, etc.** Mounting a single file as a Secret key won't work — wallet auth needs the whole directory.

## Sources

- Endpoint registration: `sgl-model-gateway/src/server.rs:549-574`.
- Backend enum and CLI: `sgl-model-gateway/src/main.rs:437`, `src/main.rs:486-497`, `src/main.rs:846-870`, `src/main.rs:945-965`.
- Upstream docs (env-var reference): `docs/advanced_features/sgl_model_gateway.md` "History and Data Connectors" section.
