---
type: Reference
title: "Code Index: traefik"
description: "Aggregated code index for traefik folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: traefik

> This index aggregates code files in the [[traefik/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [ingressroute-dashboard.yaml](./ingressroute-dashboard.yaml)

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  annotations:
    kubectl.kubernetes.io/last-applied-configuration: |
      {"apiVersion":"traefik.io/v1alpha1","kind":"IngressRoute","metadata":{"annotations":{},"name":"traefik-dashboard","namespace":"traefik"},"spec":{"entryPoints":["web"],"routes":[{"kind":"Rule","match":"Host(`traefik.dungxbuif.com`) \u0026\u0026 (PathPrefix(`/dashboard`) || PathPrefix(`/api`))","services":[{"kind":"TraefikService","name":"api@internal"}]}]}}
    meta.helm.sh/release-name: traefik
    meta.helm.sh/release-namespace: traefik
  creationTimestamp: "2026-06-03T04:29:47Z"
  generation: 2
  labels:
    app.kubernetes.io/instance: traefik-traefik
    app.kubernetes.io/managed-by: Helm
    app.kubernetes.io/name: traefik
    helm.sh/chart: traefik-40.2.0
  name: traefik-dashboard
  namespace: traefik
  resourceVersion: "23493"
  uid: 8a247c82-b5d2-4aa7-ab6e-bafd720c3f31
spec:
  entryPoints:
  - web
  routes:
  - kind: Rule
    match: Host(`traefik.dungxbuif.com`) && (PathPrefix(`/dashboard`) || PathPrefix(`/api`))
    services:
    - kind: TraefikService
      name: api@internal

```

---

## [values.yaml](./values.yaml)

```yaml
# Traefik configuration without TLS (handled by Caddy)
# Exposed via Kube-vip IP (10.10.0.30)
deployment:
  kind: DaemonSet

service:
  type: LoadBalancer
  annotations: {}

ports:
  web:
    port: 8000
    expose:
      default: true
    exposedPort: 80
    protocol: TCP
  websecure:
    port: 8443
    expose:
      default: false
    exposedPort: 443
    protocol: TCP

global:
  checkNewVersion: false
  sendAnonymousUsage: false

additionalArguments:
  - "--providers.kubernetesingress=true"
  - "--entrypoints.web.address=:8000"

ingressRoute:
  dashboard:
    enabled: true
    matchRule: Host(`traefik.dungxbuif.com`)
    entryPoints: ["web"]

```

---
