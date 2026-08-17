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
- name: Install containerd
  ansible.builtin.apt:
    name: containerd
    update_cache: true
    state: present

- name: Create containerd config directory
  ansible.builtin.file:
    path: /etc/containerd
    state: directory
    mode: "0755"

- name: Generate default containerd config if missing
  ansible.builtin.shell: containerd config default > /etc/containerd/config.toml
  args:
    creates: /etc/containerd/config.toml

- name: Use systemd cgroup driver
  ansible.builtin.replace:
    path: /etc/containerd/config.toml
    regexp: 'SystemdCgroup = false'
    replace: 'SystemdCgroup = true'

- name: Enable and restart containerd
  ansible.builtin.systemd:
    name: containerd
    enabled: true
    state: restarted

```

---
