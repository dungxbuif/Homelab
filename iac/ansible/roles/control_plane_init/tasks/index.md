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
- name: Check if first control-plane is already initialized
  ansible.builtin.stat:
    path: /etc/kubernetes/admin.conf
  register: kube_admin_conf

- name: Initialize first control-plane
  ansible.builtin.command: >
    kubeadm init
    --control-plane-endpoint {{ kube_control_plane_endpoint }}
    --upload-certs
    --pod-network-cidr {{ pod_cidr }}
    --service-cidr {{ service_cidr }}
  when: not kube_admin_conf.stat.exists

- name: Create kube config directory for ansible user
  ansible.builtin.file:
    path: "/home/{{ ansible_user }}/.kube"
    state: directory
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0755"

- name: Copy admin kubeconfig to ansible user
  ansible.builtin.copy:
    src: /etc/kubernetes/admin.conf
    dest: "/home/{{ ansible_user }}/.kube/config"
    remote_src: true
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0600"

- name: Generate control-plane join command
  ansible.builtin.shell: |
    set -e
    CERT_KEY="$(kubeadm init phase upload-certs --upload-certs 2>/dev/null | tail -n1)"
    kubeadm token create --print-join-command --certificate-key "$CERT_KEY"
  register: control_plane_join_command
  changed_when: false

- name: Share control-plane join command
  ansible.builtin.set_fact:
    kubeadm_control_plane_join_command: "{{ control_plane_join_command.stdout }}"
  delegate_facts: true
  delegate_to: "{{ item }}"
  loop: "{{ groups['k8s_join_control_plane'] | default([]) }}"

```

---
