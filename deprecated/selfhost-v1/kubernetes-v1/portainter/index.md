---
type: Reference
title: "Code Index: portainter"
description: "Aggregated code index for portainter folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: portainter

> This index aggregates code files in the [[portainter/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [values.yml](./values.yml)

```yaml
service:
  type: ClusterIP
ingress:
  enabled: true
  hosts:
    - host: portainer.dungxbuif.com
      paths:
        - path: /
          port: 9000
persistence:
  size: 1Gi
  storageClass: longhorn
```

---
