---
type: Reference
title: "Code Index: longhorn"
description: "Aggregated code index for longhorn folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: longhorn

> This index aggregates code files in the [[longhorn/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [ingress-applied.yaml](./ingress-applied.yaml)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    kubectl.kubernetes.io/last-applied-configuration: |
      {"apiVersion":"networking.k8s.io/v1","kind":"Ingress","metadata":{"annotations":{},"name":"longhorn-ingress","namespace":"longhorn-system"},"spec":{"rules":[{"host":"longhorn.dungxbuif.com","http":{"paths":[{"backend":{"service":{"name":"longhorn-frontend","port":{"number":80}}},"path":"/","pathType":"Prefix"}]}}]}}
  creationTimestamp: "2026-06-03T04:19:42Z"
  generation: 1
  name: longhorn-ingress
  namespace: longhorn-system
  resourceVersion: "23459"
  uid: 41c322e1-1141-49c4-9980-63d56e1ecded
spec:
  rules:
  - host: longhorn.dungxbuif.com
    http:
      paths:
      - backend:
          service:
            name: longhorn-frontend
            port:
              number: 80
        path: /
        pathType: Prefix
status:
  loadBalancer: {}

```

---

## [ingress-longhorn.yml](./ingress-longhorn.yml)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: longhorn-ingress
  namespace: longhorn-system
spec:
  rules:
  - host: longhorn.dungxbuif.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: longhorn-frontend
            port:
              number: 80
---
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: traefik-dashboard
  namespace: traefik
spec:
  entryPoints:
    - web
  routes:
    - match: Host(`traefik.dungxbuif.com`) && (PathPrefix(`/dashboard`) || PathPrefix(`/api`))
      kind: Rule
      services:
        - name: api@internal
          kind: TraefikService

```

---

## [values.yaml](./values.yaml)

```yaml
# Optimized values for 3-node HA cluster with limited disk (80GB OS disk)
global:
  priorityClass: system-cluster-critical

networkPolicies:
  enabled: true

defaultSettings:
  defaultDataPath: /var/lib/longhorn
  defaultNumberOfReplicas: 2
  storageOverProvisioningPercentage: 150
  storageMinimalAvailablePercentage: 15
  guaranteedEngineManagerCPU: 10
  guaranteedReplicaManagerCPU: 10
  allowNodeFailureWithLastReplica: true
  replicaSoftAntiAffinity: true
  upgradeChecker: false
  defaultLonghornStaticStorageClass: longhorn-static
  backupTarget: 
  backupTargetCredentialSecret: 

# Ensure Longhorn UI is accessible via NodePort or we will handle Ingress later
service:
  ui:
    type: ClusterIP

```

---
