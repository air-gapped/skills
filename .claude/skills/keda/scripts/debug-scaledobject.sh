#!/usr/bin/env bash
# Probe a KEDA ScaledObject end-to-end.
# Usage: debug-scaledobject.sh <name> [namespace] [keda-namespace]
# Example: debug-scaledobject.sh order-worker apps keda
set -u

NAME="${1:-}"
NS="${2:-default}"
KEDA_NS="${3:-keda}"

if [[ -z "$NAME" ]]; then
  echo "Usage: $0 <scaledobject-name> [namespace] [keda-namespace]" >&2
  exit 2
fi

banner() {
  echo
  echo "=============================================================="
  echo "  $*"
  echo "=============================================================="
}

run() {
  echo "\$ $*"
  "$@" 2>&1 || echo "  (command exited $?)"
  echo
}

banner "1. ScaledObject status ($NAME in $NS)"
run kubectl describe scaledobject -n "$NS" "$NAME"

banner "2. ScaledObject YAML"
run kubectl get scaledobject -n "$NS" "$NAME" -o yaml

banner "3. Managed HPA (keda-hpa-$NAME)"
run kubectl get hpa -n "$NS" "keda-hpa-$NAME" -o yaml

banner "4. external.metrics.k8s.io APIService state"
run kubectl get apiservice v1beta1.external.metrics.k8s.io

banner "5. Metrics exposed by keda-operator-metrics-apiserver"
kubectl get --raw "/apis/external.metrics.k8s.io/v1beta1" 2>/dev/null \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); names=[r["name"] for r in d.get("resources",[])]; print("\n".join(sorted(names)))' \
  | grep -i "$NAME" || echo "(no metric names matching $NAME)"
echo

banner "6. Raw metric values (per trigger s0, s1, ...)"
# Read trigger types from the ScaledObject; metric names are s<index>-<type>-<hash>
TRIGGER_COUNT=$(kubectl get scaledobject -n "$NS" "$NAME" -o json 2>/dev/null \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d.get("spec",{}).get("triggers",[])))' \
  2>/dev/null || echo 0)

if [[ "$TRIGGER_COUNT" -gt 0 ]]; then
  # Fetch all metric names and match each s<i>-* prefix
  ALL_METRICS=$(kubectl get --raw "/apis/external.metrics.k8s.io/v1beta1" 2>/dev/null \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); [print(r["name"]) for r in d.get("resources",[])]' 2>/dev/null)
  for ((i=0; i<TRIGGER_COUNT; i++)); do
    METRIC=$(echo "$ALL_METRICS" | grep -E "^s${i}-" | head -1 || true)
    if [[ -n "$METRIC" ]]; then
      echo "--- trigger #$i: metric=$METRIC"
      URL="/apis/external.metrics.k8s.io/v1beta1/namespaces/$NS/$METRIC?labelSelector=scaledobject.keda.sh%2Fname%3D$NAME"
      run kubectl get --raw "$URL"
    else
      echo "--- trigger #$i: no metric name found"
    fi
  done
else
  echo "(could not determine trigger count)"
fi

banner "7. keda-operator logs (last 300 lines matching $NAME)"
kubectl logs -n "$KEDA_NS" deploy/keda-operator --tail=500 2>/dev/null \
  | grep -i "$NAME" | tail -n 100 || echo "(no operator log lines matching $NAME)"
echo

banner "8. keda-operator-metrics-apiserver logs (last 100 lines)"
run kubectl logs -n "$KEDA_NS" deploy/keda-operator-metrics-apiserver --tail=100

banner "9. keda-admission-webhooks logs (last 50 lines)"
run kubectl logs -n "$KEDA_NS" deploy/keda-admission-webhooks --tail=50

banner "10. Target workload and its current replica count"
TARGET_KIND=$(kubectl get scaledobject -n "$NS" "$NAME" -o jsonpath='{.spec.scaleTargetRef.kind}' 2>/dev/null || echo Deployment)
TARGET_NAME=$(kubectl get scaledobject -n "$NS" "$NAME" -o jsonpath='{.spec.scaleTargetRef.name}' 2>/dev/null)
if [[ -n "$TARGET_NAME" ]]; then
  run kubectl get "$TARGET_KIND" -n "$NS" "$TARGET_NAME"
else
  echo "(could not determine scaleTargetRef)"
fi

echo
echo "=============================================================="
echo "  Done. Review sections 1-3 first (ScaledObject + HPA state);"
echo "  sections 4-6 diagnose metric pipeline issues;"
echo "  sections 7-9 show operator/webhook errors."
echo "=============================================================="
