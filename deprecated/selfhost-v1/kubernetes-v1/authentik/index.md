---
type: Reference
title: "Code Index: authentik"
description: "Aggregated code index for authentik folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: authentik

> This index aggregates code files in the [[authentik/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [values.yaml](./values.yaml)

```yaml
authentik:
    secret_key: "vmtlT+jTyV2v19rx2raeTt1vDHWpOiYqoGuV6Trsy7RdpFucOdGBOIBJFEmtgl6VDMsLs9h9a8fecc5W"
    error_reporting:
        enabled: true
    postgresql:
        password: "63nUqDh1gu2hkIECaBtIYEPhaet4tcZB465HRhM87FtUKsLPiKBTDwX9NZtisb6ZoCLY0YjqA2E7BUNr"
    replicaCount: 1

server:
    service:
        type: ClusterIP
        port: 80
        targetPort: 9000
        protocol: TCP
    ingress:
        # Specify kubernetes ingress controller class name
        ingressClassName: traefik
        enabled: true
        annotations:
            traefik.ingress.kubernetes.io/router.tls: "true"
            traefik.ingress.kubernetes.io/router.entrypoints: "websecure"
        # Modified ingress host configuration
        hosts:
          - authentik.dungxbuif.com
    replicaCount: 1

worker:
    replicaCount: 1

postgresql:
    enabled: true
    image:
        repository: docker.io/bitnami/postgresql
        tag: "17.5.0-debian-12-r3"
        pullPolicy: IfNotPresent
    auth:
        password: "63nUqDh1gu2hkIECaBtIYEPhaet4tcZB465HRhM87FtUKsLPiKBTDwX9NZtisb6ZoCLY0YjqA2E7BUNr"
    primary:
        persistence:
            size: 1Gi

redis:
    enabled: true
    master:
        persistence:
            size: 512Mi

```

---
