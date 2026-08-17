---
type: Playbook
title: "Standardized K8s CI/CD Playbook (GitLab + ArgoCD)"
description: "Technical specifications of the Centralized Ops GitOps model, Custom Tagging Convention, LAN-Only Ingress, K8s Runner Stack, and Battle-Tested Onboarding Playbook"
timestamp: 2026-08-06T21:07:00Z
---

# 🚀 Standardized CI/CD Playbook (GitLab + ArgoCD GitOps)

Document này định nghĩa chi tiết toàn bộ kiến trúc **Centralized GitOps Model**, **Quy chuẩn Tagging Custom**, **Phân tách Database**, **Tham chiếu Biến Môi trường**, và **Quy trình 5 Bước Onboarding Ứng Dụng Mới chuẩn hóa**.

---

## 📐 Architecture & Security Overview (LAN-Only Ingress)

```text
 ┌──────────────────────────────────────┐       ┌──────────────────────────────────────┐
 │   1. App Source Repo (GitLab Pi 5)   │       │  2. Centralized Ops Repo (GitLab)    │
 │ (Code + Dockerfile + .gitlab-ci.yml) │       │   (`dungxbuif/homelab-ops`)          │
 └──────────────────┬───────────────────┘       └──────────────────▲───────────────────┘
                    │ Push Tag (prod-YYYY.MM.DD.index)             │ Update image.tag
                    v                                              │ (via OPS_REPO_TOKEN)
 ┌──────────────────────────────────────┐                          │
 │  GitLab CI (chạy trên K8s Runner)    ├──────────────────────────┘
 │  - DinD Sidecar (docker:24.0.5-dind) │
 └──────────────────┬───────────────────┘
                    │ Push Image (dungxbuif user)
                    v
 ┌──────────────────────────────────────┐       ┌──────────────────────────────────────┐
 │ Container Registry (Pi 5)            │       │      Kubernetes HA Cluster           │
 │ (registry.dungxbuif.com)             │       │                                      │
 └──────────────────▲───────────────────┘       │  [argocd Namespace]                  │
                    │                           │  - ArgoCD Controller (Polls Git)     │
                    │ Pull Image (regcred)      │               │ Auto-Sync            │
                    └───────────────────────────┤               v                      │
                                                │  [<app>-prod Namespace]              │
                                                └──────────────────────────────────────┘
```

### 🛡️ Invariants & Guideline Bảo Mật:
1. **LAN-Only Ingress (Zero Public Exposure)**:
   - **GitLab Server (`git.dungxbuif.com`)**: Đặt trên Raspberry Pi 5.
   - **ArgoCD UI (`argocd.dungxbuif.com`)**: Đặt trên K8s Cluster.
   - **Bảo mật**: Tuyệt đối **KHÔNG** khai báo Rathole Tunnel hay Nginx VPS Whitelist cho công cụ quản trị. Chỉ truy cập được qua WiFi Homelab hoặc **Tailscale VPN** (`100.64.0.0/10`).
2. **Docker-in-Docker (DinD) Builder Standard**:
   - Sử dụng service `docker:24.0.5-dind` với command `["--tls=false"]` và `DOCKER_HOST: tcp://localhost:2375`.
   - Không mount `hostPath` `/var/run/docker.sock` từ K8s node.
3. **No Direct Database Mutation**:
   - AI Agents & DevOps tuyệt đối không tự ý can thiệp CSDL dịch vụ ngầm (`gitlab-rails runner`, direct SQL queries) nếu không có sự đồng ý của Human User. Mọi thay đổi phải thông qua UI/API hoặc GitOps Manifests.

---

## 🔑 Required CI/CD Variables & Local Storage Reference

Dưới đây là danh sách tên biến môi trường (CI/CD Variables) khai báo trên GitLab UI, cùng vị trí lưu trữ giá trị bí mật thực tế trong `local_vars.json` (gitignored):

| Tên biến trên GitLab CI/CD | Mô tả vai trò | Khai báo trên GitLab UI | Vị trí lưu giá trị bí mật (`local_vars.json`) |
|---|---|---|---|
| **`OPS_REPO_TOKEN`** | Project Access Token của `homelab-ops` (Role: Maintainer, Scopes: `api`, `write_repository`, `read_repository`) | Masked, Unprotected | `LEGACY_SYSTEM_SECRETS.OPS_REPO_TOKEN` |
| **`REGISTRY_USER`** | Username đăng nhập private Docker Registry (`registry.dungxbuif.com`) $\rightarrow$ `dungxbuif` | Unmasked, Unprotected | `LEGACY_SYSTEM_SECRETS.REGISTRY_USER` |
| **`REGISTRY_PASSWORD`** | Mật khẩu mã hóa Bcrypt đăng nhập Docker Registry (`registry.dungxbuif.com`) | Masked, Unprotected | `LEGACY_SYSTEM_SECRETS.REGISTRY_PASSWORD` |

---

## 🏷️ Quy chuẩn Tag Custom: `prod-YYYY.MM.DD.index` (Single Production Flow)

| Tiền tố Tag | Ví dụ Tag chuẩn | Môi trường Target | Hành động GitLab CI & ArgoCD |
|---|---|---|---|
| `prod-` | `prod-2026.08.06.0` | K8s Namespace `<app>-prod` | Build Docker Image $\rightarrow$ Push Registry $\rightarrow$ Commit Ops Repo $\rightarrow$ Auto-Deploy Production. |

---

## 📋 Quy trình 5 Bước Onboarding Dự Án Mới (Standardized Playbook)

Khi cần phát triển và triển khai một dự án/dịch vụ mới lên hệ thống, thực hiện theo đúng 5 bước chuẩn hóa sau:

### 1️⃣ Bước 1: Khai báo 3 Biến CI/CD trên App Repo (GitLab UI)
Vào App Repo $\rightarrow$ **Settings** $\rightarrow$ **CI/CD** $\rightarrow$ **Variables**:
- `OPS_REPO_TOKEN`: Dán Project Access Token của `homelab-ops` *(Masked)*
- `REGISTRY_USER`: `dungxbuif` *(Unmasked)*
- `REGISTRY_PASSWORD`: Dán mật khẩu Registry trong `local_vars.json` *(Masked)*

### 2️⃣ Bước 2: Khai báo Manifests trong `homelab-ops`
Tạo thư mục `k8s/apps/<app-name>/prod/`:
- `kustomization.yaml` (Trỏ tới `../base` + `ingress.yaml` + `newTag: prod-YYYY.MM.DD.0`)
- `ingress.yaml` (Khai báo host `<app-domain>.dungxbuif.com`)

### 3️⃣ Bước 3: Khai báo ArgoCD Application & Secret `regcred`
1. Khai báo file `argocd-apps/<app-name>.yaml` (sử dụng `project: homelab` hoặc `default`, namespace `<app-name>-prod`).
2. Khởi tạo Secret `regcred` cho Namespace mới để K8s pull được private image:
   ```bash
   kubectl create secret docker-registry regcred \
     --docker-server=registry.dungxbuif.com \
     --docker-username=dungxbuif \
     --docker-password=<REGISTRY_PASSWORD> \
     -n <app-name>-prod --dry-run=client -o yaml | kubectl apply -f -
   ```

### 4️⃣ Bước 4: Thêm `.gitlab-ci.yml` chuẩn vào App Repo
Sử dụng mẫu template chuẩn DinD duy nhất cho luồng Production:
```yaml
image: docker:24.0.5

services:
  - name: docker:24.0.5-dind
    command: ["--tls=false"]

stages:
  - build

variables:
  DOCKER_HOST: tcp://localhost:2375
  DOCKER_TLS_CERTDIR: ""
  REGISTRY_HOST: "registry.dungxbuif.com"
  IMAGE_NAME: "$REGISTRY_HOST/<app-name>"
  OPS_REPO_URL: "https://oauth2:${OPS_REPO_TOKEN}@gitlab.dungxbuif.com/dungxbuif/homelab-ops.git"

deploy_prod:
  stage: build
  rules:
    - if: '$CI_COMMIT_TAG =~ /^prod-[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$/'
  before_script:
    - 'apk add --no-cache git'
  script:
    - 'echo "🚀 Building PRODUCTION Image: ${IMAGE_NAME}:${CI_COMMIT_TAG}"'
    - 'echo "${REGISTRY_PASSWORD}" | docker login ${REGISTRY_HOST} -u "${REGISTRY_USER}" --password-stdin'
    - 'docker build -t ${IMAGE_NAME}:${CI_COMMIT_TAG} .'
    - 'docker push ${IMAGE_NAME}:${CI_COMMIT_TAG}'
    - 'git config --global user.email "ci-bot@dungxbuif.com"'
    - 'git config --global user.name "GitLab CI Bot"'
    - 'git clone ${OPS_REPO_URL} homelab-ops'
    - 'cd homelab-ops/k8s/apps/<app-name>/prod'
    - 'sed -i "s|newTag:.*|newTag: ${CI_COMMIT_TAG}|g" kustomization.yaml'
    - 'git add kustomization.yaml'
    - 'git commit -m "chore(prod): release <app-name> image ${CI_COMMIT_TAG}"'
    - 'git push origin main'
```

### 5️⃣ Bước 5: Push Tag để kích hoạt Deploy tự động!
```bash
git tag prod-YYYY.MM.DD.0
git push origin prod-YYYY.MM.DD.0
```
👉 Toàn bộ ứng dụng sẽ tự động được build, push registry, sync ArgoCD và live tại domain tương ứng sau 30 giây!