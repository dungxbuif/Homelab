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
- name: Create Kubernetes apt keyring directory
  ansible.builtin.file:
    path: /etc/apt/keyrings
    state: directory
    mode: "0755"

- name: Install Kubernetes apt key
  ansible.builtin.shell: |
    curl -fsSL "https://pkgs.k8s.io/core:/stable:/v{{ kubernetes_version }}/deb/Release.key" |
      gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
  args:
    creates: /etc/apt/keyrings/kubernetes-apt-keyring.gpg

- name: Configure Kubernetes apt repository
  ansible.builtin.copy:
    dest: /etc/apt/sources.list.d/kubernetes.list
    mode: "0644"
    content: |
      deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v{{ kubernetes_version }}/deb/ /

- name: Install Kubernetes packages
  ansible.builtin.apt:
    name:
      - "kubelet={{ kubernetes_apt_version }}"
      - "kubeadm={{ kubernetes_apt_version }}"
      - "kubectl={{ kubernetes_apt_version }}"
    update_cache: true
    state: present

- name: Hold Kubernetes packages
  ansible.builtin.dpkg_selections:
    name: "{{ item }}"
    selection: hold
  loop:
    - kubelet
    - kubeadm
    - kubectl

- name: Enable kubelet
  ansible.builtin.systemd:
    name: kubelet
    enabled: true

```

---
