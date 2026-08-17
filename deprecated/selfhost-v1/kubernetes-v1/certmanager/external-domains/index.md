---
type: Reference
title: "Code Index: external-domains"
description: "Aggregated code index for external-domains folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: external-domains

> This index aggregates code files in the [[external-domains/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [template-certificate.yml](./template-certificate.yml)

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-com-certificate  # CHANGE: Use your domain name
  namespace: default  # Or specific namespace
  labels:
    cert-type: external-domain
    domain: example.com  # CHANGE: Your domain

spec:
  secretName: example-com-tls  # CHANGE: Secret name for this certificate
  duration: 2160h      # 90 days
  renewBefore: 720h    # 30 days - safe renewal window
  
  issuerRef:
    # Use same ClusterIssuer if domain uses Cloudflare DNS
    name: cloudflare-cluster-issuer
    kind: ClusterIssuer
    
    # OR create separate issuer if different DNS provider
    # name: example-com-issuer
    # kind: ClusterIssuer

  # DNS names to include in certificate
  dnsNames:
    - 'example.com'              # CHANGE: Base domain
    - '*.example.com'            # CHANGE: Wildcard for subdomains
    
    # OR specific subdomains only:
    # - 'app.example.com'
    # - 'api.example.com'

  privateKey:
    algorithm: RSA
    size: 2048
    rotationPolicy: Always  # Auto rotate private key on renewal
  
  usages:
    - server auth
    - client auth

```

---

## [template-ingress.yml](./template-ingress.yml)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-app-ingress  # CHANGE: Your service name
  namespace: default  # CHANGE: Your namespace
  annotations:
    kubernetes.io/ingress.class: "traefik"
    traefik.ingress.kubernetes.io/router.entrypoints: "websecure"
    traefik.ingress.kubernetes.io/router.tls: "true"
    
    # Optional: Add authentication middleware
    # traefik.ingress.kubernetes.io/router.middlewares: "default-basic-auth@kubernetescrd"

spec:
  ingressClassName: traefik
  
  tls:
  - hosts:
    - app.example.com  # CHANGE: Your domain
    secretName: example-com-tls  # CHANGE: Match certificate secretName
  
  rules:
  - host: app.example.com  # CHANGE: Your domain
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service  # CHANGE: Your service name
            port:
              number: 80  # CHANGE: Your service port

```

---
