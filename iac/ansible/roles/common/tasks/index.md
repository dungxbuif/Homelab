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
- name: Set hostname from inventory name
  ansible.builtin.hostname:
    name: "{{ inventory_hostname }}"

- name: Install base packages
  ansible.builtin.apt:
    name:
      - apt-transport-https
      - ca-certificates
      - curl
      - gnupg
      - lsb-release
      - software-properties-common
      - qemu-guest-agent
    update_cache: true
    state: present

- name: Enable qemu guest agent
  ansible.builtin.systemd:
    name: qemu-guest-agent
    enabled: true
    state: started

- name: Disable swap immediately
  ansible.builtin.command: swapoff -a
  changed_when: false

- name: Remove swap entries from fstab
  ansible.builtin.replace:
    path: /etc/fstab
    regexp: '^([^#].*\sswap\s.*)$'
    replace: '# \1'

- name: Add kubernetes to /etc/hosts for local API resolution
  ansible.builtin.lineinfile:
    path: /etc/hosts
    line: "127.0.0.1 kubernetes"
    state: present

- name: Load Kubernetes kernel modules
  ansible.builtin.copy:
    dest: /etc/modules-load.d/k8s.conf
    mode: "0644"
    content: |
      overlay
      br_netfilter

- name: modprobe overlay
  community.general.modprobe:
    name: overlay
    state: present

- name: modprobe br_netfilter
  community.general.modprobe:
    name: br_netfilter
    state: present

- name: Configure Kubernetes sysctl
  ansible.builtin.copy:
    dest: /etc/sysctl.d/99-kubernetes.conf
    mode: "0644"
    content: |
      net.bridge.bridge-nf-call-iptables = 1
      net.bridge.bridge-nf-call-ip6tables = 1
      net.ipv4.ip_forward = 1

- name: Apply sysctl
  ansible.builtin.command: sysctl --system
  changed_when: false

```

---
