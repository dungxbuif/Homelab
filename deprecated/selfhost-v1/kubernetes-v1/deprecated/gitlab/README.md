# GitLab Self-Hosted Kubernetes Deployment

This directory contains configuration files for deploying GitLab Community Edition on your Kubernetes cluster using Helm, with an existing external MinIO instance and Traefik ingress controller.

## Configuration Overview

- **Edition:** Community Edition (CE)
- **Ingress:** Traefik (handles TLS termination)
- **Object Storage:** External MinIO (provided separately)
- **Persistent Storage:** Longhorn (for Gitaly, PostgreSQL, Redis if bundled)
- **Resource Profile:** Reduced resource requests for homelab environment.

## Prerequisites

1.  **Kubernetes Cluster:** A running Kubernetes cluster.
2.  **Helm:** Helm v3 installed.
3.  **Traefik:** Traefik installed as an ingress controller, configured with TLS for your domain.
4.  **Longhorn:** Longhorn installed and configured as a StorageClass named `longhorn`.
5.  **MinIO:** An external MinIO instance running and accessible *within* the cluster (e.g., via a ClusterIP or NodePort service). The service used in `values.yml` is `minio-service.minio-system.svc:9000`.
6.  **DNS:** DNS records pointing `gitlab.dungxbuif.com` and `gitlab-registry.dungxbuif.com` to your Traefik ingress.

## Automated Installation

For a quick installation, you can use the automated deployment script below. Save it as `deploy-gitlab.sh`, make it executable with `chmod +x deploy-gitlab.sh`, and run it:

## Manual Setup Steps

If you prefer to set up manually, follow these steps:

### 1. Prepare MinIO

Ensure your external MinIO instance is running. Create the following buckets for GitLab using the MinIO UI or `mc` client:

- `git-lfs`
- `gitlab-artifacts`
- `gitlab-uploads`
- `gitlab-packages`
- `gitlab-backups`
- `registry`

### 2. Create Namespace

Create the Kubernetes namespace for GitLab:

```bash
kubectl create namespace gitlab
```

### 3. Create MinIO Credentials Secret

Create the Kubernetes secret containing the access and secret keys for your MinIO instance. Replace placeholders if your credentials differ from the ones below.

**MinIO Credentials:**
- Access Key: `gitlab`
- Secret Key: `rdh-FRN3qjh4pwv_ztp`

```bash
kubectl apply -f /root/selfhost/kubernetes-v1/gitlab/gitlab-minio-creds.yaml -n gitlab
```

*(Note: The `values.yml` file has been configured to use this secret.)*

### 4. Add GitLab Helm Repository

```bash
helm repo add gitlab https://charts.gitlab.io/
helm repo update
```

### 5. Deploy GitLab

Install the GitLab chart using the customized `values.yml` file in this directory. This command will install GitLab in the `gitlab` namespace.

```bash
helm install gitlab gitlab/gitlab -f /root/selfhost/kubernetes-v1/gitlab/values.yml --create-namespace -n gitlab
helm upgrade gitlab gitlab/gitlab -f /root/selfhost/kubernetes-v1/gitlab/values.yml --create-namespace -n gitlab
```

*(The deployment might take several minutes.)*

### 6. Get Initial Root Password

Once the deployment is complete, retrieve the initial password for the `root` user:

```bash
kubectl get secret -n gitlab gitlab-gitlab-initial-root-password -o jsonpath='{.data.password}' | base64 --decode ; echo
```

### 7. Access GitLab

Open your browser and navigate to `https://gitlab.dungxbuif.com`. Log in using the username `root` and the password obtained in the previous step.

## Default Values Reference

The default `values.yaml` for the chart can be found here:
[https://gitlab.com/gitlab-org/charts/gitlab/-/blob/master/values.yaml?ref_type=heads](https://gitlab.com/gitlab-org/charts/gitlab/-/blob/master/values.yaml?ref_type=heads)