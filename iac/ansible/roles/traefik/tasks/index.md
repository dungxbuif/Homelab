---
type: Reference
title: "Code Index: tasks"
description: "Aggregated code index for tasks folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: tasks

> This index aggregates code files in the [[tasks/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [main.yml](./main.yml)

```yaml
---
- name: Add Traefik Helm repository
  kubernetes.core.helm_repository:
    name: traefik
    repo_url: "https://traefik.github.io/charts"

- name: Create Traefik values file
  template:
    src: values.yaml.j2
    dest: /tmp/traefik-values.yaml

- name: Deploy Traefik via Helm
  kubernetes.core.helm:
    name: traefik
    chart_ref: traefik/traefik
    release_namespace: traefik
    create_namespace: true
    values_files:
      - /tmp/traefik-values.yaml
    kubeconfig: /etc/kubernetes/admin.conf
    wait: true

- name: Clean up temporary values file
  file:
    path: /tmp/traefik-values.yaml
    state: absent

```

---
