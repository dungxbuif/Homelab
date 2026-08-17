---
type: Reference
title: "Code Index: coturn"
description: "Aggregated code index for coturn folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: coturn

> This index aggregates code files in the [[coturn/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [coturn.yml](./coturn.yml)

```yaml
# Traefik CRDs
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: ingressroutetcps.traefik.containo.us
spec:
  group: traefik.containo.us
  names:
    kind: IngressRouteTCP
    listKind: IngressRouteTCPList
    plural: ingressroutetcps
    singular: ingressroutetcp
  scope: Namespaced
  versions:
    - name: v1alpha1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                entryPoints:
                  type: array
                  items:
                    type: string
                routes:
                  type: array
                  items:
                    type: object
                    properties:
                      match:
                        type: string
                      services:
                        type: array
                        items:
                          type: object
                          properties:
                            name:
                              type: string
                            port:
                              type: integer
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: ingressrouteudps.traefik.containo.us
spec:
  group: traefik.containo.us
  names:
    kind: IngressRouteUDP
    listKind: IngressRouteUDPList
    plural: ingressrouteudps
    singular: ingressrouteudp
  scope: Namespaced
  versions:
    - name: v1alpha1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                entryPoints:
                  type: array
                  items:
                    type: string
                routes:
                  type: array
                  items:
                    type: object
                    properties:
                      match:
                        type: string
                      services:
                        type: array
                        items:
                          type: object
                          properties:
                            name:
                              type: string
                            port:
                              type: integer
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: middlewares.traefik.containo.us
spec:
  group: traefik.containo.us
  names:
    kind: Middleware
    listKind: MiddlewareList
    plural: middlewares
    singular: middleware
  scope: Namespaced
  versions:
    - name: v1alpha1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                hostSNI:
                  type: array
                  items:
                    type: string
---
# Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: coturn
---
# ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: coturn-config
  namespace: coturn
data:
  turnserver.conf: |
    listening-port=3478
    tls-listening-port=5349
    min-port=49152
    max-port=65535
    fingerprint
    user=whiteboard:.Bcu9~W)gTP'#Xso
---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coturn
  namespace: coturn
spec:
  replicas: 1
  selector:
    matchLabels:
      app: coturn
  template:
    metadata:
      labels:
        app: coturn
    spec:
      containers:
      - name: coturn
        image: coturn/coturn:latest
        ports:
        - containerPort: 3478
          protocol: TCP
        - containerPort: 3478
          protocol: UDP
        - containerPort: 5349
          protocol: TCP
        - containerPort: 5349
          protocol: UDP
        resources:
          requests:
            cpu: 0.5
            memory: 512Mi
          limits:
            cpu: 1
            memory: 1Gi
        volumeMounts:
        - name: config
          mountPath: /etc/coturn/turnserver.conf
          subPath: turnserver.conf
      volumes:
      - name: config
        configMap:
          name: coturn-config
---
# Service
apiVersion: v1
kind: Service
metadata:
  name: coturn
  namespace: coturn
spec:
  type: NodePort
  selector:
    app: coturn
  ports:
  - name: turn-udp
    port: 3478
    protocol: UDP
    targetPort: 3478
  - name: turn-tcp
    port: 3478
    protocol: TCP
    targetPort: 3478
  - name: turns-udp
    port: 5349
    protocol: UDP
    targetPort: 5349
  - name: turns-tcp
    port: 5349
    protocol: TCP
    targetPort: 5349
---
# IngressRouteTCP
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRouteTCP
metadata:
  name: coturn-tcp
  namespace: coturn
spec:
  entryPoints:
    - turnserver
    - turnservers
  routes:
    - match: HostSNI(`ice.dungxbuif.com`)
      services:
        - name: coturn
          port: 3478
---
# IngressRouteUDP
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRouteUDP
metadata:
  name: coturn-udp
  namespace: coturn
spec:
  entryPoints:
    - turnserver
  routes:
    - match: HostSNI(`ice.dungxbuif.com`)
      services:
        - name: coturn
          port: 3478
---
# Horizontal Pod Autoscaler
# apiVersion: autoscaling/v2beta2
# kind: HorizontalPodAutoscaler
# metadata:
#   name: coturn-hpa
#   namespace: coturn
# spec:
#   scaleTargetRef:
#     apiVersion: apps/v1
#     kind: Deployment
#     name: coturn
#   minReplicas: 1
#   maxReplicas: 5
#   metrics:
#   - type: Resource
#     resource:
#       name: cpu
#       target:
#         type: Utilization
#         averageUtilization: 80
#   - type: Resource
#     resource:
#       name: memory
#       target:
#         type: Utilization
#         averageUtilization: 80

```

---
