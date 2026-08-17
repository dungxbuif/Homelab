---
type: Reference
title: "MacOCR Deployment & Infrastructure Spec"
description: "Architecture, deployment guide, secrets, autoscaling and operational runbook for MacOCR Proxy on K8s"
timestamp: 2026-08-15T04:55:00Z
---

# 📑 MacOCR Platform Specification & Operational Runbook

## 1. 🏗️ Architecture Overview

MacOCR is a multi-tier OCR document processing service running on the hybrid homelab:
* **Proxy Server (K8s):** Go-based high-concurrency API server with embedded React Admin UI and Docusaurus documentation.
* **Native Worker (Pi 5 / Mac Mini):** Native OCR inference engine listening on `:8787` (`10.10.0.5:8787`).
* **Shared Redis (K8s Cluster):** Cache, rate-limiting, and queue broker in namespace `redis`.
* **PostgreSQL (Pi 5):** Central database instance (`postgres.dungxbuif.com:5432`), storing user accounts, API keys, and document processing logs under the database `macocr`.
* **RustFS Object Storage (Pi 5):** S3 backend (`storage.dungxbuif.com`) under bucket `mac-ocr`.

```
[ Internet / Clients ]
         │
         ▼ (HTTPS)
 [ VPS Traefik SNI ] ──(Rathole Tunnel)──► [ Pi 5 Caddy Edge ]
                                                    │
                                                    ▼
                                       [ K8s Traefik Ingress ]
                                                    │
                                        (ocr.dungxbuif.com)
                                                    ▼
                                      [ macocr-proxy Deployment ]
                                         ├──► [ Shared Redis (K8s:6379) ]
                                         ├──► [ PostgreSQL (Pi 5:5432) ]
                                         ├──► [ RustFS S3 (Pi 5:9000) ]
                                         └──► [ Native Worker (Pi 5:8787) ]
```

---

## 2. 🚀 Deployment Details

### Kubernetes Resources
* **Namespace:** `macocr`
* **Deployment:** `macocr-proxy` (Image: `registry.dungxbuif.com/macocr-proxy:v1.0.2`, Replicas: `1` fixed)
* **Service:** `macocr-service` (`ClusterIP:8080`)
* **Ingress:** `macocr-ingress` (Class: `traefik`, Host: `ocr.dungxbuif.com`)
* **Autoscaling / Scale Policy:**
  * Cố định **1 Replica** cho môi trường hiện tại để tối ưu tài nguyên và tránh lãng phí RAM/CPU khi chưa quá tải.
  * Hệ thống Session và Rate Limiter đã được tích hợp qua Redis trung tâm (`redis.svc.cluster.local:6379`), sẵn sàng bật lại HPA khi lưu lượng tải tăng cao mà không lo xung đột session.

---

## 3. 🛡️ Developer Portal, Admin Console & API Key Security

MacOCR Proxy cung cấp giao diện nhúng tại `/admin/` (Clean White Mode siêu thoáng, xây dựng bằng **React 18 + TypeScript + Lucide Icons**), hỗ trợ 2 phân quyền rõ ràng:

### 1. Developer Portal (User View):
* **Đăng nhập tự do:** Bất kỳ User nào được tạo đều có thể đăng nhập bằng email + mật khẩu của mình.
* **Tự quản trị API Keys của mình:** 
  * Tự tạo mới API Key (`sk_ocr_...`), đặt tên mô tả ứng dụng và tuỳ chỉnh Rate Limit riêng cho key đó.
  * Tự thu hồi (Revoke) secret key của chính mình khi không sử dụng.
  * Xem báo cáo hạn mức tài khoản cá nhân: RPM, Document Quota đã dùng / còn lại, S3 Storage utilized.

### 2. Admin Console (Admin View):
* **Quản trị người dùng & Phân bổ tài nguyên:**
  * Tạo tài khoản User mới, prefill mật khẩu ngẫu nhiên bảo mật cao và gửi cho người dùng.
  * Thiết lập hạn mức cấp tài khoản (**Account Quotas**): Rate Limit (RPM), Document Quota, S3 Storage Limit (GiB).
  * Khoá / Kích hoạt lại tài khoản (**Suspend / Reactivate**).
  * Đặt lại mật khẩu (**Reset Password**) cho User.
* **Bảo mật API Keys (Zero-Knowledge):**
  * **Admin KHÔNG xem và KHÔNG can thiệp vào API Keys của User.** API Keys là bí mật riêng tư của từng Developer, chỉ có chính Developer đó mới có quyền tạo và quản lý trong Developer Portal của họ.

A high-performance standalone Redis deployment was created for shared use across all Kubernetes workloads and local network applications.

* **Namespace:** `redis`
* **K8s Internal Endpoint:** `redis-service.redis.svc.cluster.local:6379`
* **LAN / Native App Endpoint (Pi 5 / Local):**
  * **Host:** `10.10.0.30` (K8s VIP) or `10.10.0.31` - `33`
  * **NodePort:** `30379`
  * **Password:** `SldPateMZwZm2QKpHnKT5kDEDkMcGBFH`
* **Performance Tuning:** `maxmemory 1gb`, `maxmemory-policy allkeys-lru`, `appendonly no`, `tcp-backlog 511`.

---

## 4. 🔑 Secrets & Credentials

All sensitive credentials for MacOCR are managed via Kubernetes Secret `macocr-secrets` in namespace `macocr` (referenced from `local_vars.json` -> `MACOCR_SECRETS`):

| Secret Key | Source / Reference in `local_vars.json` | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `MACOCR_SECRETS.MACOCR_DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | `MACOCR_SECRETS.MACOCR_REDIS_URL` | Redis connection URL |
| `S3_ENDPOINT` | `https://storage.dungxbuif.com` | Object storage endpoint |
| `S3_BUCKET` | `mac-ocr` | S3 bucket for uploads |
| `S3_ACCESS_KEY_ID` | `local_vars.json` (RustFS S3) | Storage Access Key |
| `S3_SECRET_ACCESS_KEY` | `local_vars.json` (RustFS S3) | Storage Secret Access Key |
| `NATIVE_BASE_URL` | `http://10.10.0.10:8787` (LAN) / `http://10.10.0.5:8787` | OCR Native Worker endpoint |
| `NOTIFICATION_ENCRYPTION_KEY` | `MACOCR_SECRETS.MACOCR_NOTIFICATION_ENCRYPTION_KEY` | 32-character AES webhook key |
| `NATIVE_AUTH_SECRET` | `MACOCR_SECRETS.MACOCR_NATIVE_AUTH_SECRET` | Secret HMAC for native worker auth |

---

## 5. ⚠️ Quan trọng: Lưu ý khi Build & Deploy

1. **Multi-Architecture Build Bắt Buộc:**
   * Môi trường phát triển cục bộ có thể là ARM64 (Apple Silicon / Pi 5), nhưng các node K8s Proxmox là kiến trúc **`linux/amd64`**.
   * Khi build image mới, **luôn dùng `docker buildx`** để xuất multi-arch image:
     ```bash
     docker buildx build --platform linux/amd64,linux/arm64 \
       -t registry.dungxbuif.com/macocr-proxy:<TAG> --push -f Dockerfile .
     ```
   * *Không build trực tiếp `docker build` đơn thuần trên Mac M-series vì sẽ gây lỗi `exec format error` trên cụm K8s.*

2. **Quản trị người dùng & Seed Admin:**
   * Để tạo hoặc reset tài khoản Admin:
     ```bash
     kubectl exec -it -n macocr deployment/macocr-proxy -- \
       macocr-admin seed --email <EMAIL> --password "<PASSWORD>"
     ```
   * Quản lý user và cấp API Key:
     ```bash
     kubectl exec -it -n macocr deployment/macocr-proxy -- macocr-admin list-users
     kubectl exec -it -n macocr deployment/macocr-proxy -- macocr-admin create-key --user-id 1 --name "prod-app"
     ```

3. **Luồng Ingress / Domain:**
   * Cấu hình Domain cần đi qua cả 3 lớp:
     1. **VPS Traefik:** Cần có `HostSNI('ocr.dungxbuif.com')` trong `/root/gateway/dynamic.yml`.
     2. **Pi 5 Caddy:** Block `@ocr host ocr.dungxbuif.com` trỏ về `10.10.0.30:80`.
     3. **K8s Ingress:** Ingress resource `macocr-ingress` trong namespace `macocr`.
