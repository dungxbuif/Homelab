---
type: Reference
title: "Code Index: group_vars"
description: "Aggregated code index for group_vars folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: group_vars

> This index aggregates code files in the [[group_vars/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [all.yml](./all.yml)

```yaml
ansible_python_interpreter: /usr/bin/python3

```

---

## [k8s_cluster.yml](./k8s_cluster.yml)

```yaml
kubernetes_version: "1.30"
kubernetes_apt_version: "1.30.*"

pod_cidr: "<K8S_POD_SUBNET>"
service_cidr: "<K8S_SERVICE_CIDR>"

kube_vip_address: "<K8S_VIP>"
kube_vip_interface: "eth0"
kube_vip_image: "ghcr.io/kube-vip/kube-vip:v0.8.7"

cni_provider: "cilium"
cilium_version: "1.15.5"
calico_manifest_url: "https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico.yaml"

allow_schedule_on_control_plane: true

```

---
