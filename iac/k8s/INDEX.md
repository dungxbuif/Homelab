---
type: Reference
title: "Code Index: k8s"
description: "Aggregated code index for k8s folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: k8s

> This index aggregates code files in the [[k8s/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [kube-vip-static.yaml](./kube-vip-static.yaml)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: kube-vip
  namespace: kube-system
spec:
  hostNetwork: true
  containers:
    - name: kube-vip
      image: ghcr.io/kube-vip/kube-vip:v0.8.7
      imagePullPolicy: IfNotPresent
      args:
        - manager
      env:
        - name: vip_arp
          value: "true"
        - name: address
          value: "10.10.0.30"
        - name: port
          value: "6443"
        - name: vip_interface
          value: "eth0"
        - name: cp_enable
          value: "true"
        - name: cp_namespace
          value: "kube-system"
        - name: svc_enable
          value: "true"
        - name: svc_le_namespace
          value: "kube-system"
        - name: vip_leaderelection
          value: "false"
        - name: server_address
          value: "127.0.0.1"
      securityContext:
        capabilities:
          add:
            - NET_ADMIN
            - NET_RAW
      volumeMounts:
        - mountPath: /etc/kubernetes/admin.conf
          name: kubeconfig
  volumes:
    - name: kubeconfig
      hostPath:
        path: /etc/kubernetes/admin.conf
        type: FileOrCreate

```

---
