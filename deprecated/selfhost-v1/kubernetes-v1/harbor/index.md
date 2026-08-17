---
type: Reference
title: "Code Index: harbor"
description: "Aggregated code index for harbor folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: harbor

> This index aggregates code files in the [[harbor/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [values.yml](./values.yml)

```yaml
expose:
  type: ingress
  tls:
    enabled: false
  ingress:
    hosts:
      core: registry.dungxbuif.com
externalURL: https://registry.dungxbuif.com

persistence:
  enabled: true
  persistentVolumeClaim:
    registry:
      storageClass: "longhorn"
      accessMode: ReadWriteOnce
      size: 4Gi
    trivy:
      storageClass: "longhorn"
      accessMode: ReadWriteOnce
      size: 1Gi
    redis:
      storageClass: "longhorn"
      accessMode: ReadWriteOnce
      size: 250Mi
    jobservice:
      storageClass: "longhorn"
      accessMode: ReadWriteOnce
      size: 150Mi
    database:
      storageClass: "longhorn"
      accessMode: ReadWriteOnce
      size: 512Mi

harborAdminPassword: "<HARBOR_PASSWORD>"


```

---
