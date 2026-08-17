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
- name: Show nodes
  ansible.builtin.command: kubectl --kubeconfig /etc/kubernetes/admin.conf get nodes -o wide
  changed_when: false

- name: Show system pods
  ansible.builtin.command: kubectl --kubeconfig /etc/kubernetes/admin.conf get pods -A
  changed_when: false

- name: Check API readiness
  ansible.builtin.command: kubectl --kubeconfig /etc/kubernetes/admin.conf get --raw=/readyz
  changed_when: false

```

---
