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
- name: Check if node is already joined
  ansible.builtin.stat:
    path: /etc/kubernetes/kubelet.conf
  register: kubelet_conf

- name: Join node as control-plane
  ansible.builtin.command: "{{ kubeadm_control_plane_join_command }} --control-plane"
  when: not kubelet_conf.stat.exists

```

---
