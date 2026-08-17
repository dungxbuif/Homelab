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
- name: Install Calico CNI
  ansible.builtin.command: "kubectl --kubeconfig /etc/kubernetes/admin.conf apply -f {{ calico_manifest_url }}"
  when: cni_provider == "calico"
  changed_when: true

- name: Install Cilium CNI
  block:
    - name: Download Cilium CLI
      ansible.builtin.get_url:
        url: "https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz"
        dest: "/tmp/cilium-linux-amd64.tar.gz"
        mode: '0644'

    - name: Extract Cilium CLI
      ansible.builtin.unarchive:
        src: "/tmp/cilium-linux-amd64.tar.gz"
        dest: "/usr/local/bin"
        remote_src: yes
        mode: '0755'

    - name: Install Cilium into cluster
      ansible.builtin.command: "/usr/local/bin/cilium install --version v{{ cilium_version }}"
      environment:
        KUBECONFIG: /etc/kubernetes/admin.conf
      changed_when: true
  when: cni_provider == "cilium"

- name: Allow scheduling on control-plane nodes for demo
  ansible.builtin.command: kubectl --kubeconfig /etc/kubernetes/admin.conf taint nodes --all node-role.kubernetes.io/control-plane-
  when: allow_schedule_on_control_plane | bool
  register: taint_result
  changed_when: "'untainted' in taint_result.stdout"
  failed_when: false

```

---
