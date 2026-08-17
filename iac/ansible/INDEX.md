---
type: Reference
title: "Code Index: ansible"
description: "Aggregated code index for ansible folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: ansible

> This index aggregates code files in the [[ansible/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [deploy_longhorn.yml](./deploy_longhorn.yml)

```yaml
- name: Deploy Longhorn Storage
  hosts: k8s_first_control_plane
  become: true
  roles:
    - longhorn

```

---

## [deploy_traefik.yml](./deploy_traefik.yml)

```yaml
- name: Deploy Traefik Ingress
  hosts: k8s_first_control_plane
  become: true
  roles:
    - traefik

```

---

## [longhorn_prep.yml](./longhorn_prep.yml)

```yaml
- name: Prepare nodes for Longhorn
  hosts: k8s_cluster
  become: true
  tasks:
    - name: Install Longhorn prerequisites
      apt:
        name:
          - open-iscsi
          - nfs-common
          - util-linux
          - bash
          - curl
        state: present
        update_cache: yes

    - name: Ensure open-iscsi service is started and enabled
      systemd:
        name: iscsid
        state: started
        enabled: yes

    - name: Load iscsi_tcp module
      modprobe:
        name: iscsi_tcp
        state: present

    - name: Ensure iscsi_tcp module is loaded on boot
      lineinfile:
        path: /etc/modules
        line: iscsi_tcp
        create: yes

```

---

## [site.yml](./site.yml)

```yaml
- name: Prepare all Kubernetes nodes
  hosts: k8s_cluster
  become: true
  roles:
    - common
    - containerd
    - kubernetes

- name: Bootstrap first control-plane node
  hosts: k8s_first_control_plane
  become: true
  roles:
    - kube_vip
    - control_plane_init

- name: Join remaining control-plane nodes
  hosts: k8s_join_control_plane
  become: true
  roles:
    - kube_vip
    - control_plane_join

- name: Install CNI and verify cluster
  hosts: k8s_first_control_plane
  become: true
  roles:
    - cni
    - verify

```

---
