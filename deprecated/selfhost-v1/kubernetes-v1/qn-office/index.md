---
type: Reference
title: "Code Index: qn-office"
description: "Aggregated code index for qn-office folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: qn-office

> This index aggregates code files in the [[qn-office/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [application.yml](./application.yml)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: qn-office
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/dungxbuif-ncc/QnOffice.git # Use HTTPS for public repo or configure SSH secret
    targetRevision: main
    path: kubernetes/base
  destination:
    server: https://kubernetes.default.svc
    namespace: qn-office
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true

```

---
