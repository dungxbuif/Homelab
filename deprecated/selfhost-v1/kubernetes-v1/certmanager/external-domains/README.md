# External Domain Certificates

This directory contains certificate configurations for external domains (non-`*.dungxbuif.com` domains).

## Quick Start

To add a new external domain certificate:

1. **Copy the template**:
   ```bash
   cp template-certificate.yml your-domain-certificate.yml
   ```

2. **Edit the file** and replace:
   - Certificate name
   - Secret name
   - DNS names
   - Labels

3. **Apply the certificate**:
   ```bash
   kubectl apply -f your-domain-certificate.yml
   ```

4. **Wait for certificate to be ready**:
   ```bash
   kubectl wait --for=condition=Ready certificate/your-cert-name -n default --timeout=300s
   ```

5. **Update TLSStore** in `traefik/tls.yml`:
   ```yaml
   certificates:
     - secretName: your-domain-tls
       namespace: default
   ```

6. **Apply TLSStore**:
   ```bash
   kubectl apply -f kubernetes-v1/traefik/tls.yml
   ```

7. **Create Ingress** for your service referencing the certificate

## Prerequisites

- Domain must be managed by Cloudflare (or create separate ClusterIssuer)
- DNS A record pointing to Traefik IP: `<MASTER_VPS_PUBLIC_IP>`
- Cloudflare API access configured

## Troubleshooting

Check certificate status:
```bash
kubectl describe certificate <cert-name> -n default
kubectl get certificate -A
```

Check cert-manager logs:
```bash
kubectl logs -n cert-manager -l app=cert-manager --tail=50
```

Check challenges:
```bash
kubectl get challenges -A
kubectl describe challenge <challenge-name> -n default
```
