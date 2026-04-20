# Helm Production Patterns Reference

## Table of Contents
- [ServiceMonitor / PodMonitor](#servicemonitor--podmonitor)
- [HPA with API Version Detection](#hpa-with-api-version-detection)
- [PodDisruptionBudget](#poddisruptionbudget)
- [Persistence (PVC / StatefulSet)](#persistence-pvc--statefulset)
- [ConfigMap Checksum Annotations](#configmap-checksum-annotations)
- [Extension Points (extra* Values)](#extension-points-extra-values)
- [Multi-Component Chart Organization](#multi-component-chart-organization)
- [Resource Presets](#resource-presets)
- [Deployment Mode Switching](#deployment-mode-switching)
- [Upgrade Compatibility](#upgrade-compatibility)
- [Probe Patterns](#probe-patterns)
- [NOTES.txt](#notestxt)

---

## ServiceMonitor / PodMonitor

For Prometheus Operator integration. Gate on both user toggle and API availability.

### values.yaml

```yaml
metrics:
  enabled: false
  serviceMonitor:
    enabled: false
    namespace: ""           # Override: deploy to monitoring namespace
    interval: "30s"
    scrapeTimeout: ""
    additionalLabels: {}    # For Prometheus selector matching
    honorLabels: false
    metricRelabelings: []
    relabelings: []
```

### Template

```yaml
{{- if and .Values.metrics.enabled .Values.metrics.serviceMonitor.enabled }}
{{- if .Capabilities.APIVersions.Has "monitoring.coreos.com/v1" }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "mychart.fullname" . }}
  namespace: {{ .Values.metrics.serviceMonitor.namespace | default .Release.Namespace }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
    {{- with .Values.metrics.serviceMonitor.additionalLabels }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
spec:
  selector:
    matchLabels:
      {{- include "mychart.selectorLabels" . | nindent 6 }}
  endpoints:
    - port: http-metrics
      interval: {{ .Values.metrics.serviceMonitor.interval | default "30s" }}
      {{- with .Values.metrics.serviceMonitor.scrapeTimeout }}
      scrapeTimeout: {{ . }}
      {{- end }}
      {{- if .Values.metrics.serviceMonitor.honorLabels }}
      honorLabels: true
      {{- end }}
      {{- with .Values.metrics.serviceMonitor.metricRelabelings }}
      metricRelabelings:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.metrics.serviceMonitor.relabelings }}
      relabelings:
        {{- toYaml . | nindent 8 }}
      {{- end }}
{{- end }}
{{- end }}
```

Add a named port `http-metrics` to the Service template for the metrics endpoint.

---

## HPA with API Version Detection

### values.yaml

```yaml
autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: ""
  behavior: {}
```

### Template

```yaml
{{- if .Values.autoscaling.enabled }}
{{- $apiVersion := "autoscaling/v2" -}}
{{- if not (.Capabilities.APIVersions.Has "autoscaling/v2") -}}
  {{- $apiVersion = "autoscaling/v2beta2" -}}
{{- end }}
apiVersion: {{ $apiVersion }}
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "mychart.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "mychart.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    {{- if .Values.autoscaling.targetCPUUtilizationPercentage }}
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
    {{- end }}
    {{- if .Values.autoscaling.targetMemoryUtilizationPercentage }}
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetMemoryUtilizationPercentage }}
    {{- end }}
  {{- with .Values.autoscaling.behavior }}
  behavior:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end }}
```

In the Deployment, conditionally skip `replicas` when HPA is enabled:

```yaml
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
```

---

## PodDisruptionBudget

### values.yaml

```yaml
pdb:
  enabled: false
  minAvailable: ""       # Use one or the other, not both
  maxUnavailable: 1
```

### Template

```yaml
{{- if .Values.pdb.enabled }}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "mychart.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  {{- with .Values.pdb.minAvailable }}
  minAvailable: {{ . }}
  {{- end }}
  {{- with .Values.pdb.maxUnavailable }}
  maxUnavailable: {{ . }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "mychart.selectorLabels" . | nindent 6 }}
{{- end }}
```

---

## Persistence (PVC / StatefulSet)

### values.yaml

```yaml
persistence:
  enabled: true
  storageClass: ""          # Empty = default StorageClass
  accessModes: ["ReadWriteOnce"]
  size: 8Gi
  existingClaim: ""         # Use existing PVC (Deployment only)
  annotations: {}
```

### Deployment with Existing PVC

```yaml
volumes:
  {{- if .Values.persistence.enabled }}
  - name: data
    persistentVolumeClaim:
      claimName: {{ .Values.persistence.existingClaim | default (include "mychart.fullname" .) }}
  {{- else }}
  - name: data
    emptyDir: {}
  {{- end }}
```

### StatefulSet with volumeClaimTemplates

```yaml
{{- if .Values.persistence.enabled }}
volumeClaimTemplates:
  - metadata:
      name: data
      {{- with .Values.persistence.annotations }}
      annotations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
    spec:
      accessModes:
        {{- toYaml .Values.persistence.accessModes | nindent 8 }}
      {{- if .Values.persistence.storageClass }}
      storageClassName: {{ .Values.persistence.storageClass | quote }}
      {{- end }}
      resources:
        requests:
          storage: {{ .Values.persistence.size }}
{{- end }}
```

**Note**: `volumeClaimTemplates` generate PVCs named `<template>-<pod>`. Cannot
be modified after creation.

---

## ConfigMap Checksum Annotations

Force pod restart when ConfigMap or Secret content changes:

```yaml
spec:
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        checksum/secret: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
```

**Library chart variant**: `$.Template.BasePath` is unavailable in library charts.
Use `{{ include "mylibchart.configmap" . | sha256sum }}` instead.

---

## Extension Points (extra* Values)

Standard pattern found across all major charts (ArgoCD, Bitnami, ingress-nginx):

### values.yaml

```yaml
extraContainers: []          # Sidecar containers
extraInitContainers: []      # Init containers
extraVolumes: []             # Additional volumes
extraVolumeMounts: []        # Additional mounts for main container
extraEnvVars: []             # Additional environment variables
extraEnvVarsCM: ""           # ConfigMap name for extra env vars
extraEnvVarsSecret: ""       # Secret name for extra env vars
extraArgs: []                # Additional command arguments
extraPorts: []               # Additional container ports
podAnnotations: {}           # Additional pod annotations
podLabels: {}                # Additional pod labels
```

### Usage in Deployment

```yaml
spec:
  template:
    metadata:
      {{- with .Values.podAnnotations }}
      annotations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      labels:
        {{- include "mychart.labels" . | nindent 8 }}
        {{- with .Values.podLabels }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
    spec:
      {{- with .Values.extraInitContainers }}
      initContainers:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
        - name: {{ .Chart.Name }}
          env:
            {{- with .Values.extraEnvVars }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
          envFrom:
            {{- if .Values.extraEnvVarsCM }}
            - configMapRef:
                name: {{ .Values.extraEnvVarsCM }}
            {{- end }}
            {{- if .Values.extraEnvVarsSecret }}
            - secretRef:
                name: {{ .Values.extraEnvVarsSecret }}
            {{- end }}
          args:
            {{- with .Values.extraArgs }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
          volumeMounts:
            {{- with .Values.extraVolumeMounts }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
        {{- with .Values.extraContainers }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      volumes:
        {{- with .Values.extraVolumes }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
```

---

## Multi-Component Chart Organization

Pattern from ArgoCD: three-tier hierarchy with per-component standard structure.

### values.yaml Structure

```yaml
# Global defaults
global:
  image:
    registry: docker.io

# Per-component (repeated for each component)
server:
  replicas: 1
  image:
    repository: ""     # Inherits global if empty
    tag: ""
  resources: {}
  containerSecurityContext:
    runAsNonRoot: true
    readOnlyRootFilesystem: true
  serviceAccount:
    create: true
    name: ""
  autoscaling:
    enabled: false
    minReplicas: 1
    maxReplicas: 5
  pdb:
    enabled: false
  metrics:
    enabled: false
    serviceMonitor:
      enabled: false

controller:
  replicas: 1
  image:
    repository: ""
    tag: ""
  # ... same structure
```

### Template Organization

One directory per component or clear naming convention:

```
templates/
  server/
    deployment.yaml
    service.yaml
    ingress.yaml
  controller/
    deployment.yaml
    service.yaml
  _helpers.tpl
```

---

## Resource Presets

Bitnami pattern: t-shirt sizes instead of empty `resources: {}`.

### values.yaml

```yaml
# Use a preset OR custom resources (custom always wins)
resourcesPreset: "small"   # nano, micro, small, medium, large, xlarge, 2xlarge, none
resources: {}               # Overrides preset when set
```

### Preset Values

| Preset | CPU Req | Mem Req | CPU Limit | Mem Limit |
|--------|---------|---------|-----------|-----------|
| nano | 100m | 128Mi | 150m | 192Mi |
| micro | 250m | 256Mi | 375m | 384Mi |
| small | 500m | 512Mi | 750m | 768Mi |
| medium | 500m | 1024Mi | 750m | 1536Mi |
| large | 1.0 | 2048Mi | 1.5 | 3072Mi |
| xlarge | 1.0 | 3072Mi | 3.0 | 6144Mi |
| 2xlarge | 1.0 | 3072Mi | 6.0 | 12288Mi |

Presets are starting points. Custom resources recommended for production.

---

## Deployment Mode Switching

Pattern from Grafana Loki: a single value controls which templates render.

### values.yaml

```yaml
deploymentMode: SingleBinary   # SingleBinary | SimpleScalable | Distributed
```

### Template

```yaml
{{- if eq .Values.deploymentMode "SingleBinary" }}
apiVersion: apps/v1
kind: Deployment
...
{{- end }}

{{- if eq .Values.deploymentMode "Distributed" }}
# Render StatefulSets for each component (ingester, querier, etc.)
{{- end }}
```

Useful for applications with multiple deployment topologies.

---

## Upgrade Compatibility

Pattern from Cilium: store original install version to prevent disruptive changes
on upgrades.

### values.yaml

```yaml
upgradeCompatibility:
  enabled: true
```

### Template Logic

```yaml
{{- if and .Values.upgradeCompatibility.enabled .Release.IsUpgrade }}
{{- if semverCompare "<1.14.0" .Values.upgradeCompatibility.fromVersion }}
# Apply legacy behavior for upgrades from pre-1.14
{{- end }}
{{- end }}
```

Prevents new features from disrupting existing deployments while offering them
to fresh installs.

---

## Probe Patterns

### values.yaml

```yaml
livenessProbe:
  enabled: true
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 6
  successThreshold: 1

readinessProbe:
  enabled: true
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 6
  successThreshold: 1

startupProbe:
  enabled: false
  initialDelaySeconds: 0
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 30
  successThreshold: 1

customLivenessProbe: {}    # Override entire probe
customReadinessProbe: {}
customStartupProbe: {}
```

### Template

```yaml
{{- if .Values.customLivenessProbe }}
livenessProbe:
  {{- toYaml .Values.customLivenessProbe | nindent 12 }}
{{- else if .Values.livenessProbe.enabled }}
livenessProbe:
  httpGet:
    path: /healthz
    port: http
  initialDelaySeconds: {{ .Values.livenessProbe.initialDelaySeconds }}
  periodSeconds: {{ .Values.livenessProbe.periodSeconds }}
  timeoutSeconds: {{ .Values.livenessProbe.timeoutSeconds }}
  failureThreshold: {{ .Values.livenessProbe.failureThreshold }}
  successThreshold: {{ .Values.livenessProbe.successThreshold }}
{{- end }}
```

---

## Service Spec Control

### NodePort Suppression

By default, Kubernetes auto-assigns a NodePort (30000-32767) for NodePort and
LoadBalancer services. This is almost never wanted for LoadBalancer services
(cloud LBs route traffic directly) and wastes port range.

**Default `allocateLoadBalancerNodePorts` to `false`** — users who need NodePorts
on their LoadBalancer can opt in. The reverse (defaulting to `true`) silently
consumes scarce NodePort range on every install. Requires Kubernetes 1.24+.

### Spec Passthrough (extraSpec)

Kubernetes adds new Service spec fields over time (`externalTrafficPolicy`,
`internalTrafficPolicy`, `loadBalancerClass`, `ipFamilyPolicy`,
`loadBalancerSourceRanges`, etc.). Modeling each one explicitly means the chart
blocks admins until you add it. Instead, model the critical fields explicitly
and provide an `extraSpec` map that passes through anything else:

### values.yaml

```yaml
service:
  type: ClusterIP
  port: 80
  nodePort: ""                        # Pin a specific NodePort (NodePort/LoadBalancer only)
  allocateLoadBalancerNodePorts: false # Suppress auto-assigned NodePorts on LoadBalancer (K8s 1.24+)
  annotations: {}
  # Passthrough for any Service spec field not explicitly modeled above
  extraSpec: {}
    # externalTrafficPolicy: Local
    # internalTrafficPolicy: Local
    # loadBalancerSourceRanges:
    #   - 10.0.0.0/8
    # loadBalancerClass: internal
    # ipFamilyPolicy: PreferDualStack
```

### Template

```yaml
spec:
  type: {{ .Values.service.type }}
  {{- if and (eq .Values.service.type "LoadBalancer") (not .Values.service.allocateLoadBalancerNodePorts) }}
  allocateLoadBalancerNodePorts: false
  {{- end }}
  {{- with .Values.service.extraSpec }}
  {{- toYaml . | nindent 2 }}
  {{- end }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
      name: http
      {{- if and .Values.service.nodePort (or (eq .Values.service.type "NodePort") (eq .Values.service.type "LoadBalancer")) }}
      nodePort: {{ .Values.service.nodePort }}
      {{- end }}
```

The `extraSpec` pattern applies to any resource, not just Services. Use it
anywhere the Kubernetes API surface is large and evolving (Deployment pod spec,
Ingress spec, etc.). The `extra*` values convention (extraEnvVars, extraVolumes,
extraVolumeMounts, extraContainers) is the same idea applied to specific
sub-resources.

---

## NOTES.txt

Post-install instructions. Plain text processed as Go template.

```
Thank you for installing {{ .Chart.Name }}!

{{- if .Values.ingress.enabled }}
Access the application at:
{{- range .Values.ingress.hosts }}
  http{{ if $.Values.ingress.tls }}s{{ end }}://{{ .host }}{{ (first .paths).path }}
{{- end }}
{{- else if contains "NodePort" .Values.service.type }}
Get the application URL:
  export NODE_PORT=$(kubectl get --namespace {{ .Release.Namespace }} -o jsonpath="{.spec.ports[0].nodePort}" services {{ include "mychart.fullname" . }})
  export NODE_IP=$(kubectl get nodes --namespace {{ .Release.Namespace }} -o jsonpath="{.items[0].status.addresses[0].address}")
  echo http://$NODE_IP:$NODE_PORT
{{- else if contains "ClusterIP" .Values.service.type }}
Port-forward to access:
  kubectl --namespace {{ .Release.Namespace }} port-forward svc/{{ include "mychart.fullname" . }} {{ .Values.service.port }}:{{ .Values.service.port }}
{{- end }}
```

Keep brief. Point to README for details. Never print secrets — reference Secret
objects with retrieval commands.
