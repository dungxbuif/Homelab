---
type: Reference
title: "Code Index: bitwaden"
description: "Aggregated code index for bitwaden folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: bitwaden

> This index aggregates code files in the [[bitwaden/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [bitwarden.secret.yml](./bitwarden.secret.yml)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: bitwarden-secret
  namespace: bitwarden
type: Opaque
data:
  globalSettings__installation__id: ODZmOTZmYmItMzE3Ny00ZjNiLWIzZjUtYjI0ZjAxMDFlYjlh
  globalSettings__installation__key: ektFd3ZuY2tzeFVkMjlDMHR4Rkk=
  adminSettings__admins: ZHVuZ2J1aS5kdW5nYnVpLjAwQGdtYWlsLmNvbQ==
```

---

## [values.yml](./values.yml)

```yaml

general:
  domain: "bitwarden.dungxbuif.com"
  admins: "dungbui.dungbui.00@gmail.com"
  email:
    replyToEmail: "no-reply@bitwarden.localhost"
    smtpHost: "smtp.gmail.com"
    smtpPort: "587"
    smtpSsl: "false"
    smtpTrustServer: "false"
    smtpSslOverride: "false"
    smtpStartTls: "false"
sharedStorageClassName: "longhorn"
secrets:
  secretName: bitwarden-secret

supportComponents:
  dbMigrator:
    image:
      name: bitwarden/mssqlmigratorutility
  certGenerator:
    image:
      name: docker.io/nginx
      tag: 1.25.3
  kubectl:
    image:
      name: bitnami/kubectl
      tag: 1.21
# Data volume sizes for shared PVCs
volume:
  dataprotection:
    size: "1Gi"
    labels: {}
  attachments:
    size: 1Gi
    labels: {}
  licenses:
    size: 1Gi
    labels: {}
  logs:
    enabled: false
    size: 1Gi
    labels: {}

serviceAccount:
  name: service-account
  deployRolesOnly: false

database:
  enabled: true
  image:
    name: mcr.microsoft.com/mssql/server
    tag: latest

  resources:
  requests:
    memory: "2G"
    cpu: "100m"
  limits:
    memory: "2G"
    cpu: "500m"
  volume:
    backups:
      storageClass: "longhorn"
      size: 1Gi
    data:
      storageClass: "longhorn"
      size: 3Gi
      labels: {}
    log:
      storageClass: "longhorn"
      size: 1Gi
      
```

---
