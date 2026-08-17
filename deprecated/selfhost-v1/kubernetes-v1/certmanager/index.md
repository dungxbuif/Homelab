---
type: Reference
title: "Code Index: certmanager"
description: "Aggregated code index for certmanager folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: certmanager

> This index aggregates code files in the [[certmanager/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [certificate.yml](./certificate.yml)

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: dungxbuif-certificate
  namespace: default
spec:
  secretName: dungxbuif-tls
  duration: 2160h 
  renewBefore: 720h 
    organizations:
      - dungxbuif
  commonName: dungxbuif.com
  isCA: false
  privateKey:
    algorithm: RSA
    encoding: PKCS1
    size: 2048
    rotationPolicy: Always  # Auto rotate private key on renewal
  usages:
    - server auth
    - client auth
  issuerRef:
    name: cloudflare-cluster-issuer
    kind: ClusterIssuer
  dnsNames:
    - 'dungxbuif.com'
    - '*.dungxbuif.com'

```

---

## [cluster-issuer.yml](./cluster-issuer.yml)

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: cloudflare-cluster-issuer
spec:
  acme:
    email: dungbui.dungbui.00@gmail.com
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: cloudflare-cluster-issuer-account-key
    solvers:
    - dns01:
        cloudflare:
          apiTokenSecretRef:
            name: cloudflare-api-key
            key: api-token
  
```

---

## [issuer.secret.yml](./issuer.secret.yml)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: cloudflare-api-key
  namespace: cert-manager
type: Opaque
data:
  api-token: "X19HSG56Q1VWQk1SN1Y4T0xWWXpxU1h0ZE1wS21DOWh2Y19zdmpaTQ=="
```

---

## [values.yml](./values.yml)

```yaml
installCRDs: true
extraArgs: 
  - --dns01-recursive-nameservers=1.1.1.1:53,1.0.0.1:53
```

---
