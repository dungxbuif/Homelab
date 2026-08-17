---
type: Reference
title: "Code Index: traefik"
description: "Aggregated code index for traefik folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: traefik

> This index aggregates code files in the [[traefik/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [auth.middleware.yml](./auth.middleware.yml)

```yaml
apiVersion: v1
kind: Secret
metadata:
   name: traefik-dashboard-auth-secret
   namespace: traefik
type: kubernetes.io/basic-auth
stringData:
   username: admin
   password: <TRAEFIK_PASSWORD>
---
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
   name: traefik-dashboard-auth
   namespace: traefik
spec:
   basicAuth:
      secret: traefik-dashboard-auth-secret
---
apiVersion: v1
kind: Secret
metadata:
   name: longhorn-dashboard-auth-secret
   namespace: longhorn-system
type: kubernetes.io/basic-auth
stringData:
   username: admin
   password: <TRAEFIK_PASSWORD>
---
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
  namespace: traefik
spec:
  forwardAuth:
    address: http://traefik-proxy-outpost.authentik.svc.cluster.local:9000/outpost.goauthentik.io/auth/traefik
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

## [tls.yml](./tls.yml)

```yaml
apiVersion: traefik.io/v1alpha1
kind: TLSStore
metadata:
  name: default
  namespace: default
  annotations:
    description: "Default TLS store - supports *.dungxbuif.com + external domains"

spec:
  defaultCertificate:
    secretName: dungxbuif-tls  # Default cert for *.dungxbuif.com
  
  # TLS certificates registry for SNI-based routing
  # Traefik will automatically use the right cert based on SNI
  certificates: []  # Will populate when adding external domains
```

---

## [values.yml](./values.yml)

```yaml
ports:
   web:
      port: 80
      exposedPort: 80
      redirections:
         entryPoint:
            to: websecure
            scheme: https
            permanent: true
   websecure:
      port: 443
      exposedPort: 443

service:
   externalIPs:
      - <MASTER_VPS_PUBLIC_IP>

ingressRoute:
   dashboard:
      enabled: true
      matchRule: Host(`traefik.dungxbuif.com`)
      entryPoints: ['websecure']
      middlewares:
         # - name: authentik-forward-auth  # Removed Authentik middleware
         - name: traefik-dashboard-auth  # Enabled basic auth middleware

securityContext:
   capabilities:
      drop: [ALL]
      add: [NET_BIND_SERVICE]
   readOnlyRootFilesystem: true
   runAsGroup: 0
   runAsNonRoot: false
   runAsUser: 0

```

---
