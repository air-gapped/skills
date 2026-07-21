#!/usr/bin/env bash
# audit-values.sh — flag stale keys in a mimir-distributed values file before a hop.
#
#   ./audit-values.sh <current-values.yaml> <target-chart-version>
#   ./audit-values.sh current.yaml 6.0.6
#
# Why this exists: the chart ships NO values.schema.json, so a removed CHART key is a
# silent no-op — the setting simply stops applying and nothing tells you. Mimir, by
# contrast, REJECTS removed app config at startup, so a stale structuredConfig key is a
# crashloop. Two opposite failure modes in one file; this checks both sides.
#
# Exit codes: 0 = clean, 1 = findings, 2 = usage/precondition error.
# Findings are advisory — grep can't parse YAML structure, so verify each hit in context.
set -uo pipefail

VALUES="${1:-}"
TARGET="${2:-}"
[[ -f "$VALUES" && -n "$TARGET" ]] || { echo "usage: $0 <current-values.yaml> <target-chart-version>" >&2; exit 2; }

findings=0
hit() { findings=$((findings+1)); printf '  %-46s %s\n' "$1" "$2"; }
scan() { grep -nE "$1" "$VALUES" >/dev/null 2>&1; }

# Match a key in EITHER spelling. Mimir names the same setting two ways: hyphenated as a
# CLI flag (-query-frontend.downstream-url) and underscored as YAML under structuredConfig
# (downstream_url). A values file uses the YAML idiom, so searching only for the flag
# spelling silently finds nothing — which is the worst possible failure for this check.
scan_key() { grep -nE "$(printf '%s' "$1" | sed 's/[-_]/[-_]/g')" "$VALUES" >/dev/null 2>&1; }

echo "Auditing $VALUES against chart $TARGET"
echo

# ---------------------------------------------------------------- SILENT (chart keys)
echo "SILENT — removed chart keys (no error; the setting just stops applying)"

case "$TARGET" in
  5.8.*|6.*)
    scan '^\s*jaegerReporterMaxQueueSize:' && \
      hit "jaegerReporterMaxQueueSize" "-> <component>.env: OTEL_BSP_MAX_QUEUE_SIZE"
    # stale = object/map form (inline {...} or a nested `key:` child). Correct = list of strings.
    if grep -A1 -E '^\s*toPromQLLabelSelector:' "$VALUES" 2>/dev/null \
         | grep -qE 'toPromQLLabelSelector:\s*\{[^}]|^\s+[a-zA-Z_][a-zA-Z0-9_-]*:'; then
      hit "kedaAutoscaling.toPromQLLabelSelector" "type changed object -> list of strings"
    fi
    ;;
esac

case "$TARGET" in
  6.*)
    scan '^\s*nginx:' && \
      hit "nginx.* (whole section)" "-> gateway.*; PRESERVE DNS NAME via nameOverride"
    scan '^\s*(enterprise|admin_api|graphite|tokengenJob|license|provisioner|kubectlImage|federation_frontend):' && \
      hit "GEM surface (enterprise/admin_api/...)" "removed at 6.0 — delete"
    scan '(distributor|alertmanager)-headless:' && \
      hit "ingress.paths.*-headless" "renamed; leftover = Ingress route to headless svc"
    scan 'enabledNonEnterprise' && \
      hit "gateway.enabledNonEnterprise" "removed at 6.0 (harmless, but misleading)"
    scan 'frontend_address' && \
      hit "frontend_worker.frontend_address" "query-frontend-headless svc deleted at 6.0"
    ;;
esac

case "$TARGET" in
  6.1.*)
    scan '^\s*extraEnv:' && grep -nB5 -E '^\s*extraEnv:' "$VALUES" | grep -q 'kafka:' && \
      hit "kafka.extraEnv" "-> kafka.env (name-keyed merge)"
    scan '^\s*enterprise:' && hit "enterprise.image.tag" "vestigial; removed at 6.1"
    # must be the TOP-LEVEL image: block (2-space indent), not kafka.image.tag etc.
    awk '/^image:/{f=1;next} /^[a-zA-Z]/{f=0} f&&/^  tag:/{found=1} END{exit !found}' "$VALUES" || \
      hit "top-level image.tag NOT pinned" "6.1+ falls back to Chart.AppVersion — pin it for air-gap"
    ;;
esac

[[ $findings -eq 0 ]] && echo "  (none)"
silent=$findings; findings=0
echo

# ------------------------------------------------------- LOUD (app config -> crashloop)
echo "LOUD — removed app config (Mimir rejects at startup; these crashloop)"

case "$TARGET" in
  5.8.*|6.*)
    for k in ooo_native_histograms_ingestion_enabled rule_group_enabled \
             max_cost_attribution_cardinality_per_user instant_queries_with_subquery_spin_off; do
      scan_key "$k" && hit "$k" "removed in app 2.17"
    done
    grep -qE 'log_level:\s*fatal' "$VALUES" 2>/dev/null && \
      hit "log_level: fatal" "no longer a valid level (logrus -> go-kit)"
    ;;
esac

case "$TARGET" in
  6.*)
    for k in downstream_url frontend_address max_outstanding_requests_per_tenant \
             querier_forget_delay stream_chunks_when_using_blocks prune_queries \
             addresses_provider service_overload_status_code_on_rate_limit_enabled; do
      scan_key "$k" && hit "$k" "removed in app 3.0"
    done
    grep -qiE '^\s*backend:\s*redis|redis:' "$VALUES" 2>/dev/null && \
      hit "redis cache backend" "removed entirely in app 3.0"
    ;;
esac

case "$TARGET" in
  6.1.*)
    for k in minimum_step_size cost_attribution_labels prefer_availability_zone \
             grafana_alertmanager_idle_grace_period metric_relabeling_enabled \
             no_blocks_file_cleanup_enabled in_memory_tenant_meta_cache_size \
             eager_loading_startup_enabled shard_active_series_queries \
             use_active_series_decoder response_streaming_enabled \
             dns_ignore_startup_failures; do
      scan_key "$k" && hit "$k" "removed/renamed in app 3.1"
    done
    grep -qE 'heartbeat_(period|timeout):\s*0' "$VALUES" 2>/dev/null && \
      hit "ring.heartbeat_{period,timeout}: 0" "disabling heartbeats removed in 3.1"
    ;;
esac

[[ $findings -eq 0 ]] && echo "  (none)"
loud=$findings
echo
echo "----"
echo "silent findings: $silent   loud findings: $loud"
echo
echo "Next: render and diff, which catches what grep cannot ->"
echo "  helm template <rel> <chart.tgz> -f $VALUES > after.yaml"
echo "  helm get manifest <rel> -n <ns> > before.yaml"
echo "  diff before.yaml after.yaml   # assert: proxy Service name UNCHANGED,"
echo "                                #   no unintended replica decrease, no Kafka STS if classic"

[[ $((silent + loud)) -eq 0 ]] && exit 0 || exit 1
