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
- name: Create Kubernetes manifests directory
  ansible.builtin.file:
    path: /etc/kubernetes/manifests
    state: directory
    mode: "0755"

- name: Install kube-vip static pod manifest
  ansible.builtin.template:
    src: kube-vip.yaml.j2
    dest: /etc/kubernetes/manifests/kube-vip.yaml
    mode: "0644"

```

---
