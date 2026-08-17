---
type: Reference
title: "Code Index: longhorn"
description: "Aggregated code index for longhorn folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: longhorn

> This index aggregates code files in the [[longhorn/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [auth.middleware.yml](./auth.middleware.yml)

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: basic-auth
  namespace: longhorn-system
spec:
  basicAuth:
    secret: longhorn-dashboard-auth-secret
```

---

## [authentik-forward-auth.yml](./authentik-forward-auth.yml)

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: authentik-forward-auth
  namespace: longhorn-system
spec:
  forwardAuth:
    address: http://longhorn-outpost.authentik.svc.cluster.local:9000/outpost.goauthentik.io/auth/traefik
    trustForwardHeader: true
    authResponseHeaders:
      - X-authentik-username
      - X-authentik-groups
      - X-authentik-entitlements
      - X-authentik-email
      - X-authentik-name
      - X-authentik-uid
      - X-authentik-jwt
      - X-authentik-meta-jwks
      - X-authentik-meta-outpost
      - X-authentik-meta-provider
      - X-authentik-meta-app
      - X-authentik-meta-version
```

---

## [uninstall.yml](./uninstall.yml)

```yaml
#apiVersion: policy/v1beta1
#kind: PodSecurityPolicy
#metadata:
#  name: longhorn-uninstall-psp
#spec:
#  privileged: true
#  allowPrivilegeEscalation: true
#  requiredDropCapabilities:
#  - NET_RAW
#  allowedCapabilities:
#  - SYS_ADMIN
#  hostNetwork: false
#  hostIPC: false
#  hostPID: true
#  runAsUser:
#    rule: RunAsAny
#  seLinux:
#    rule: RunAsAny
#  fsGroup:
#    rule: RunAsAny
#  supplementalGroups:
#    rule: RunAsAny
#  volumes:
#  - configMap
#  - downwardAPI
#  - emptyDir
#  - secret
#  - projected
#  - hostPath
#---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: longhorn-uninstall-service-account
  namespace: longhorn
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: longhorn-uninstall-role
rules:
  - apiGroups:
      - apiextensions.k8s.io
    resources:
      - customresourcedefinitions
    verbs:
      - "*"
  - apiGroups: [""]
    resources: ["pods", "persistentvolumes", "persistentvolumeclaims", "nodes", "configmaps", "secrets", "services", "endpoints"]
    verbs: ["*"]
  - apiGroups: ["apps"]
    resources: ["daemonsets", "statefulsets", "deployments"]
    verbs: ["*"]
  - apiGroups: ["batch"]
    resources: ["jobs", "cronjobs"]
    verbs: ["*"]
  - apiGroups: ["policy"]
    resources: ["poddisruptionbudgets"]
    verbs: ["*"]
  - apiGroups: ["scheduling.k8s.io"]
    resources: ["priorityclasses"]
    verbs: ["watch", "list"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["csidrivers", "storageclasses", "volumeattachments"]
    verbs: ["*"]
  - apiGroups: ["longhorn.io"]
    resources: ["volumes", "engines", "replicas", "settings", "engineimages", "nodes", "instancemanagers", "sharemanagers",
                "backingimages", "backingimagemanagers", "backingimagedatasources", "backuptargets", "backupvolumes", "backups",
                "recurringjobs", "orphans", "snapshots", "supportbundles", "systembackups", "systemrestores", "volumeattachments", "backupbackingimages"]
    verbs: ["*"]
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    verbs: ["*"]
  #  - apiGroups: ["policy"]
  #    resources: ["podsecuritypolicies"]
  #    verbs: ["use"]
  #    resourceNames: ["longhorn-uninstall-psp"]
  - apiGroups: ["admissionregistration.k8s.io"]
    resources: ["mutatingwebhookconfigurations", "validatingwebhookconfigurations"]
    verbs: ["get", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: longhorn-uninstall-bind
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: longhorn-uninstall-role
subjects:
  - kind: ServiceAccount
    name: longhorn-uninstall-service-account
    namespace: longhorn
---
apiVersion: batch/v1
kind: Job
metadata:
  name: longhorn-uninstall
  namespace: longhorn
spec:
  activeDeadlineSeconds: 900
  backoffLimit: 1
  template:
    metadata:
      name: longhorn-uninstall
    spec:
      containers:
        - name: longhorn-uninstall
          image: longhornio/longhorn-manager:v1.7.2
          imagePullPolicy: IfNotPresent
          command:
            - longhorn-manager
            - uninstall
            - --force
          env:
            - name: LONGHORN_NAMESPACE
              value: longhorn
      restartPolicy: Never
      serviceAccountName: longhorn-uninstall-service-account
#      imagePullSecrets:
#      - name: ""
#      priorityClassName:
#      tolerations:
#        - key: "key"
#          operator: "Equal"
#          value: "value"
#          effect: "NoSchedule"
#      nodeSelector:
#        label-key1: "label-value1"
#        label-key2: "label-value2"
```

---

## [values.yml](./values.yml)

```yaml
longhornUI:
  replicas: 1
#   nodeSelector:
#     storage: longhorn
#   tolerations:
#     - key: "node-role.kubernetes.io/worker"
#       operator: "Exists"
#       effect: "NoSchedule"

# longhornManager:
#   nodeSelector:
#     storage: longhorn
#   tolerations:
#     - key: "node-role.kubernetes.io/worker"
#       operator: "Exists"
#       effect: "NoSchedule"

# longhornDriver:
#   nodeSelector:
#     storage: longhorn
#   tolerations:
#     - key: "node-role.kubernetes.io/worker"
#       operator: "Exists"
#       effect: "NoSchedule"
#   extraArgs:
#     - --kubelet-root-dir=/var/lib/kubelet  # Replace with the actual root-dir you found

ingress:
  enabled: true
  host: 'longhorn.dungxbuif.com'
  path: '/'
  annotations: 
    traefik.ingress.kubernetes.io/router.entrypoints: "websecure"
    traefik.ingress.kubernetes.io/router.middlewares: "longhorn-system-basic-auth@kubernetescrd"  # Enabled basic auth middleware
    traefik.ingress.kubernetes.io/router.tls: "true"

defaultSettings:
  defaultDataPath: '/data/longhorn/'
  defaultReplicaCount: 2
  snapshotMaxCount: 10
  autoCleanupSystemGeneratedSnapshot: true
  autoCleanupRecurringJobBackupSnapshot: true
  autoCleanupSnapshotAfterOnDemandBackupCompleted: true
  orphanResourceAutoDeletion: true
  orphanResourceAutoDeletionGracePeriod: 60
  # systemManagedComponentsNodeSelector: "storage:longhorn"
```

---
