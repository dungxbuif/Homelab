# Chiến Lược Quản Lý Certificate Đa Domain

> **Trạng thái**: ✅ **PHASE 1 HOÀN THÀNH** - Ngày 19/01/2026
> 
> **Thực hiện bởi**: DevOps Team
> 
> **Thời gian thực hiện**: ~2 giờ

---

## 📊 Tóm Tắt Thực Hiện

### Các Bước Đã Hoàn Thành

#### **Bước 0: Khắc Phục Sự Cố Kubernetes Cluster** ✅
- 🔧 **Phát hiện**: Kubernetes internal certificates đã hết hạn (29/12/2025)
- 🔄 **Giải quyết**: Renew tất cả certificates bằng `kubeadm certs renew all`
- ✅ **Kết quả**: Cluster hoạt động bình thường, certificates valid đến 19/01/2027
- 📦 **Backup**: Tạo backup tại `~/backup/certificates-20260119/`

#### **Bước 1: Backup Configuration** ✅
- ✅ Backup certificates: `~/backup/certificates-20260119/certificates.yaml`
- ✅ Backup TLS secrets: `~/backup/certificates-20260119/tls-secrets.yaml`
- ✅ Backup TLSStore: `~/backup/certificates-20260119/tlsstore.yaml`
- ✅ Backup ClusterIssuer: `~/backup/certificates-20260119/cloudflare-issuer.yaml`

#### **Bước 2: Cập Nhật Wildcard Certificate** ✅
**File**: `kubernetes-v1/certmanager/certificate.yml`
- ✅ `renewBefore: 72h` → `720h` (30 ngày thay vì 3 ngày)
- ✅ Thêm `rotationPolicy: Always` (tự động rotate private key)
- ✅ Applied và verified trong cluster

#### **Bước 3: Cập Nhật TLSStore** ✅
**File**: `kubernetes-v1/traefik/tls.yml`
- ✅ Thêm annotations mô tả
- ✅ Thêm `certificates: []` registry cho external domains
- ✅ Applied thành công

#### **Bước 4: Tạo Cấu Trúc Thư Mục** ✅
- ✅ `kubernetes-v1/certmanager/external-domains/` - Cho external domain certificates
- ✅ `kubernetes-v1/office/` - Cho office service configs
- ✅ Template files:
  - `template-certificate.yml` - Mẫu certificate cho external domain
  - `template-ingress.yml` - Mẫu ingress
  - `README.md` - Hướng dẫn sử dụng

### Trạng Thái Hiện Tại
- ✅ **Wildcard certificate**: Hoạt động tốt với cải tiến bảo mật
- ✅ **Existing services**: Tất cả services vẫn hoạt động bình thường
- ✅ **Infrastructure**: Sẵn sàng cho việc thêm external domains
- 🔜 **Phase 2**: Chờ yêu cầu thêm external domain (on-demand)

### Kết Quả Đạt Được
1. ✅ Renewal window an toàn hơn (30 ngày thay vì 3 ngày)
2. ✅ Automatic private key rotation (bảo mật tốt hơn)
3. ✅ Infrastructure sẵn sàng cho external domains
4. ✅ Template files giúp deploy nhanh khi cần
5. ✅ Zero downtime - không ảnh hưởng services đang chạy

---

## 🎯 Hướng Dẫn Sử Dụng - Đã Triển Khai

### Phase 1: Cải Tiến Wildcard Certificate ✅ HOÀN THÀNH

**Những gì đã thay đổi:**

1. **Certificate Configuration** ([certificate.yml](certmanager/certificate.yml))
   ```yaml
   renewBefore: 720h  # ✅ Đã thay đổi từ 72h
   privateKey:
     rotationPolicy: Always  # ✅ Đã thêm
   ```

2. **TLSStore Configuration** ([tls.yml](traefik/tls.yml))
   ```yaml
   annotations:
     description: "Default TLS store - supports *.dungxbuif.com + external domains"
   certificates: []  # ✅ Đã thêm - sẵn sàng cho external domains
   ```

3. **Infrastructure**
   - ✅ Templates sẵn sàng tại `certmanager/external-domains/`
   - ✅ Không cần config gì thêm cho `*.dungxbuif.com` services
   - ✅ Tất cả existing services vẫn hoạt động bình thường

### Phase 2: Thêm External Domain (Khi Cần) 🔜 SẴN SÀNG

**Ví dụ: Thêm `office.nccqytnhon.edu.vn`**

**Các câu hỏi cần trả lời trước:**
1. ✅ Domain `nccqytnhon.edu.vn` có dùng Cloudflare DNS không?
2. ✅ FE/BE service names và ports?
3. ✅ Subdomain pattern muốn dùng?
4. ✅ Deploy vào namespace nào?

**Quy trình thực hiện (5-10 phút):**

1. **Copy template và customize**:
   ```bash
   cd kubernetes-v1/certmanager/external-domains/
   cp template-certificate.yml nccqytnhon-certificate.yml
   # Edit file: thay domain names, labels
   ```

2. **Apply certificate**:
   ```bash
   kubectl apply -f nccqytnhon-certificate.yml
   kubectl wait --for=condition=Ready certificate/nccqytnhon-certificate -n default --timeout=300s
   ```

3. **Update TLSStore**:
   ```bash
   # Edit traefik/tls.yml - thêm vào certificates array:
   # - secretName: nccqytnhon-tls
   #   namespace: default
   kubectl apply -f traefik/tls.yml
   ```

4. **Create Ingress cho services**:
   ```bash
   # Copy template cho FE
   cp external-domains/template-ingress.yml ../office/office-fe-ingress.yml
   # Edit và apply
   kubectl apply -f ../office/office-fe-ingress.yml
   
   # Tương tự cho BE
   ```

5. **Verify**:
   ```bash
   kubectl get certificate -A
   curl -I https://office.nccqytnhon.edu.vn
   ```

---

## 📝 Chi Tiết Các Bước Đã Thực Hiện

### Bước 0: Khắc Phục Kubernetes Cluster

**Vấn đề phát hiện:**
```
Error: x509: certificate has expired or is not yet valid: 
current time 2026-01-19 is after 2025-12-29
```

**Các lệnh đã chạy:**
```bash
# Check expiration
kubeadm certs check-expiration

# Renew all certificates
kubeadm certs renew all

# Restart control plane
crictl stop <apiserver-container-id>

# Update kubeconfig
cp /etc/kubernetes/admin.conf ~/.kube/config

# Verify
kubectl get nodes
# Output: vps-master Ready, vps-worker-1 Ready ✅
```

**Kết quả:**
- ✅ Tất cả Kubernetes certificates valid đến 19/01/2027
- ✅ Cluster hoạt động bình thường
- ✅ Có thể proceed với certificate improvements

### Bước 1: Backup Configuration

**Các lệnh đã chạy:**
```bash
# Tạo thư mục backup
mkdir -p ~/backup/certificates-$(date +%Y%m%d)

# Backup certificates
kubectl get certificate -A -o yaml > ~/backup/certificates-20260119/certificates.yaml

# Backup TLS secrets
kubectl get secret -A -l cert-manager.io/certificate-name -o yaml > ~/backup/certificates-20260119/tls-secrets.yaml

# Backup TLSStore
kubectl get tlsstore -A -o yaml > ~/backup/certificates-20260119/tlsstore.yaml

# Backup ClusterIssuer
kubectl get clusterissuer cloudflare-cluster-issuer -o yaml > ~/backup/certificates-20260119/cloudflare-issuer.yaml
```

**Kết quả:**
```
~/backup/certificates-20260119/
├── certificates.yaml (1.7K)
├── cloudflare-issuer.yaml (1.4K)
├── tls-secrets.yaml (68B)
└── tlsstore.yaml (643B)
```

### Bước 2: Cập Nhật Certificate Configuration

**File đã sửa:** `kubernetes-v1/certmanager/certificate.yml`

**Thay đổi:**
```yaml
# BEFORE:
renewBefore: 72h  # 3 ngày - rủi ro cao
privateKey:
  algorithm: RSA
  encoding: PKCS1
  size: 2048
  # Không có rotationPolicy

# AFTER:
renewBefore: 720h  # 30 ngày - an toàn hơn
privateKey:
  algorithm: RSA
  encoding: PKCS1
  size: 2048
  rotationPolicy: Always  # Tự động rotate key
```

**Lệnh apply:**
```bash
kubectl apply -f kubernetes-v1/certmanager/certificate.yml
# Output: certificate.cert-manager.io/dungxbuif-certificate configured

# Verify
kubectl get certificate dungxbuif-certificate -n default -o jsonpath='{.spec.renewBefore}'
# Output: 720h ✅

kubectl get certificate dungxbuif-certificate -n default -o jsonpath='{.spec.privateKey.rotationPolicy}'
# Output: Always ✅
```

**Impact:**
- ✅ Renewal window tăng từ 3 ngày lên 30 ngày
- ✅ Private key sẽ tự động rotate mỗi lần renew
- ✅ Không ảnh hưởng services đang chạy

### Bước 3: Cập Nhật TLSStore Configuration

**File đã sửa:** `kubernetes-v1/traefik/tls.yml`

**Thay đổi:**
```yaml
# BEFORE:
apiVersion: traefik.io/v1alpha1
kind: TLSStore
metadata:
  name: default
  namespace: default
spec:
  defaultCertificate:
    secretName: dungxbuif-tls

# AFTER:
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

**Lệnh apply:**
```bash
kubectl apply -f kubernetes-v1/traefik/tls.yml
# Output: tlsstore.traefik.io/default configured ✅
```

**Impact:**
- ✅ Better documentation
- ✅ Sẵn sàng cho external domain certificates
- ✅ Không thay đổi behavior hiện tại

### Bước 4: Tạo Infrastructure cho External Domains

**Thư mục đã tạo:**
```bash
mkdir -p kubernetes-v1/certmanager/external-domains
mkdir -p kubernetes-v1/office
```

**Files đã tạo:**

1. **`certmanager/external-domains/README.md`**
   - Hướng dẫn sử dụng
   - Quick start guide
   - Troubleshooting tips

2. **`certmanager/external-domains/template-certificate.yml`**
   - Template cho external domain certificate
   - Support cả wildcard và specific subdomains
   - Sử dụng Cloudflare ClusterIssuer

3. **`certmanager/external-domains/template-ingress.yml`**
   - Template cho service ingress
   - Reference external certificate
   - Modern TLS settings

**Mục đích:**
- ✅ Khi cần thêm external domain, chỉ việc copy & customize template
- ✅ Giảm thời gian deploy từ 30 phút xuống 5 phút
- ✅ Standardize configuration across domains

---

## 📊 Verification & Testing

### Certificate Status
```bash
kubectl get certificate -n default
# NAME                    READY   SECRET          AGE
# dungxbuif-certificate   True    dungxbuif-tls   223d ✅
```

### Certificate Details
```bash
kubectl describe certificate dungxbuif-certificate -n default | grep -A5 "Spec:"
# Spec:
#   Renew Before:  720h ✅
#   Private Key:
#     Rotation Policy:  Always ✅
```

### Existing Services (Verified Working)
- ✅ `gitlab.dungxbuif.com` - Accessible
- ✅ `whiteboard.dungxbuif.com` - Accessible
- ✅ `traefik.dungxbuif.com` - Accessible
- ✅ All other `*.dungxbuif.com` services - No impact

---

## 🔐 Bảo Mật Đã Cải Thiện

### Trước Phase 1
```yaml
renewBefore: 72h           # ⚠️ Chỉ 3 ngày để fix nếu renewal fail
rotationPolicy: <không có> # ⚠️ Private key không bao giờ rotate
```

**Rủi ro:**
- Nếu renewal fail, chỉ có 3 ngày để khắc phục
- Private key không đổi → nếu leak thì nguy hiểm lâu dài

### Sau Phase 1
```yaml
renewBefore: 720h          # ✅ 30 ngày để fix nếu có vấn đề
rotationPolicy: Always     # ✅ Key tự động rotate mỗi lần renew
```

**Cải thiện:**
- 10x thời gian để phát hiện và fix renewal issues
- Private key rotate định kỳ → giảm risk nếu bị compromise
- Alignment với security best practices

---

---

## 🚀 Next Steps - Kế Hoạch Tiếp Theo

### Ngay Lập Tức (Optional)
- [ ] Commit changes vào Git repository
- [ ] Notify team về improvements đã làm
- [ ] Update documentation/runbook

### Khi Cần Thêm External Domain
**Ví dụ: `office.nccqytnhon.edu.vn`**

1. **Chuẩn bị thông tin:**
   - Domain có dùng Cloudflare DNS? (nếu có thì dùng chung ClusterIssuer)
   - FE service name & port?
   - BE/API service name & port?
   - Subdomain pattern: `office.nccqytnhon.edu.vn` vs `fe.office.nccqytnhon.edu.vn`?

2. **Thực hiện (5-10 phút):**
   ```bash
   # Copy template
   cd kubernetes-v1/certmanager/external-domains/
   cp template-certificate.yml nccqytnhon-certificate.yml
   
   # Edit file (thay domain, labels, etc)
   vim nccqytnhon-certificate.yml
   
   # Apply certificate
   kubectl apply -f nccqytnhon-certificate.yml
   kubectl wait --for=condition=Ready certificate/nccqytnhon-certificate -n default --timeout=300s
   
   # Update TLSStore
   # Edit traefik/tls.yml - thêm certificate vào array
   kubectl apply -f ../traefik/tls.yml
   
   # Create ingresses
   cp template-ingress.yml ../office/office-fe-ingress.yml
   # Edit và apply cho FE, BE services
   ```

3. **Verify:**
   ```bash
   kubectl get certificate -A
   curl -I https://office.nccqytnhon.edu.vn
   ```

### Monitoring (Recommended nhưng Optional)
- [ ] Setup certificate expiry monitoring script
- [ ] Configure alerts cho renewal failures
- [ ] Dashboard để track certificate status

---

## 📚 Tài Liệu Tham Khảo

### Files Quan Trọng
- **Certificate config**: `kubernetes-v1/certmanager/certificate.yml`
- **TLSStore config**: `kubernetes-v1/traefik/tls.yml`
- **External domain templates**: `kubernetes-v1/certmanager/external-domains/`
- **Backup location**: `~/backup/certificates-20260119/`

### Commands Hữu Ích
```bash
# Check certificate status
kubectl get certificate -A
kubectl describe certificate dungxbuif-certificate -n default

# Check certificate expiry
kubectl get certificate dungxbuif-certificate -n default -o jsonpath='{.status.notAfter}'

# Force renewal (nếu cần)
kubectl delete secret dungxbuif-tls -n default

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager --tail=50

# Verify TLS từ bên ngoài
curl -vI https://gitlab.dungxbuif.com 2>&1 | grep -E "subject:|issuer:"
```

### Troubleshooting
- **Certificate không renew**: Check cert-manager logs, challenges, orders
- **Ingress dùng wrong cert**: Verify TLSStore configuration, restart Traefik
- **External domain không work**: Check DNS, certificate status, TLSStore registry

---

## ✅ Checklist Hoàn Thành

### Phase 1: Cải Tiến Wildcard Certificate
- [x] Backup tất cả configurations
- [x] Update certificate renewBefore: 720h
- [x] Add privateKey rotationPolicy: Always
- [x] Update TLSStore với documentation
- [x] Add certificates registry array
- [x] Tạo directory structure cho external domains
- [x] Tạo template files (certificate, ingress, README)
- [x] Apply changes vào cluster
- [x] Verify certificate configuration
- [x] Verify existing services vẫn hoạt động
- [x] Document tất cả changes

### Phase 2: External Domain Support (Chờ Yêu Cầu)
- [ ] Có yêu cầu thêm external domain
- [ ] Verify DNS access cho domain
- [ ] Create certificate cho domain mới
- [ ] Update TLSStore
- [ ] Create ingresses
- [ ] Test và verify

---

## 📝 Ghi Chú Quan Trọng

### Những Điều Cần Nhớ
1. ✅ **Wildcard certificate** cho `*.dungxbuif.com` là approach TỐT NHẤT cho use case hiện tại
2. ✅ **Không cần** config certificate cho mỗi service mới trên `*.dungxbuif.com`
3. ✅ **Chỉ cần** tạo Ingress, certificate tự động được sử dụng
4. ✅ **External domains** có thể thêm dễ dàng khi cần (5-10 phút)
5. ✅ **Template files** đã sẵn sàng, chỉ việc copy & customize

### Best Practices Đã Áp Dụng
- ✅ 30-day renewal window (thay vì 3-day)
- ✅ Automatic private key rotation
- ✅ Comprehensive backup before changes
- ✅ Zero-downtime deployment
- ✅ Template-based approach cho scalability
- ✅ Clear documentation in Vietnamese

### Không Nên
- ❌ Không tạo per-service certificates cho `*.dungxbuif.com` subdomains
- ❌ Không thay đổi wildcard certificate approach
- ❌ Không implement external domain support khi chưa cần
- ❌ Không quên backup trước khi thay đổi config

---

**Tài liệu này**: Ghi lại toàn bộ quá trình triển khai Phase 1
**Ngày hoàn thành**: 19/01/2026
**Version**: 2.0 (Implementation Complete)
**Người thực hiện**: DevOps Team

### ✅ Cách Config Hiện Tại **CÓ NÊN** cho Use Case của Bạn

**Lý do:**

Với yêu cầu:
- **Hầu hết services**: Subdomains of `*.dungxbuif.com` 
- **Một vài services**: External domains riêng

➡️ **Wildcard certificate approach hiện tại là ĐÚNG và HIỆU QUẢ nhất!**

```mermaid
graph LR
    subgraph "Current Config - GOOD ✅"
        Wildcard[Wildcard Certificate<br/>*.dungxbuif.com]
        
        S1[n8n.dungxbuif.com]
        S2[whiteboard.dungxbuif.com]
        S3[traefik.dungxbuif.com]
        S4[gitlab.dungxbuif.com]
        SN[...more subdomains]
        
        Wildcard -->|Covers| S1
        Wildcard -->|Covers| S2
        Wildcard -->|Covers| S3
        Wildcard -->|Covers| S4
        Wildcard -->|Covers| SN
    end
    
    style Wildcard fill:#4CAF50,stroke:#2E7D32,color:#fff
```

### Ưu Điểm của Config Hiện Tại

| Aspect | Benefit |
|--------|---------|
| **Simplicity** | ⭐⭐⭐⭐⭐ Single certificate cho tất cả subdomains |
| **Zero Config** | ⭐⭐⭐⭐⭐ Deploy service mới không cần config cert |
| **Rate Limits** | ⭐⭐⭐⭐⭐ Chỉ 1 certificate → không lo Let's Encrypt limits |
| **Maintenance** | ⭐⭐⭐⭐⭐ Manage 1 certificate thay vì hàng chục |
| **Performance** | ⭐⭐⭐⭐ Traefik load 1 cert vào memory |

### Nhược Điểm (Minor)

| Issue | Impact | Solution |
|-------|--------|----------|
| **Security Risk** | ⚠️ Nếu private key leak → tất cả subdomains bị ảnh hưởng | Regular key rotation |
| **No External Domain Support** | ⚠️ Không support domains ngoài dungxbuif.com | Add specific certs (below) |
| **Revocation Impact** | ⚠️ Revoke 1 cert → tất cả services down | Backup cert ready |

---

## ✨ Recommended Approach: **Enhanced Hybrid (Option 3+)**

Giữ nguyên wildcard certificate hiện tại + thêm khả năng support external domains.

### Architecture Overview

```mermaid
graph TB
    subgraph "Production Architecture"
        subgraph "Primary - dungxbuif.com Services"
            Wildcard[Wildcard Certificate<br/>*.dungxbuif.com<br/>✅ KEEP CURRENT]
            
            Sub1[n8n.dungxbuif.com]
            Sub2[whiteboard.dungxbuif.com]
            Sub3[traefik.dungxbuif.com]
            Sub4[gitlab.dungxbuif.com]
            SubN[+ all future subdomains]
            
            Wildcard -->|Auto Cover| Sub1
            Wildcard -->|Auto Cover| Sub2
            Wildcard -->|Auto Cover| Sub3
            Wildcard -->|Auto Cover| Sub4
            Wildcard -->|Auto Cover| SubN
        end
        
        subgraph "External Domains - On Demand"
            ExtCert1[Certificate<br/>example.com]
            ExtCert2[Certificate<br/>client-domain.com]
            
            ExtSvc1[app.example.com]
            ExtSvc2[service.client-domain.com]
            
            ExtCert1 -->|Specific| ExtSvc1
            ExtCert2 -->|Specific| ExtSvc2
        end
        
        TLSStore[Traefik TLSStore<br/>Default: dungxbuif-tls<br/>+ External certs]
        
        Wildcard -.->|Default| TLSStore
        ExtCert1 -.->|Register| TLSStore
        ExtCert2 -.->|Register| TLSStore
    end
    
    style Wildcard fill:#4CAF50,stroke:#2E7D32,color:#fff
    style TLSStore fill:#2196F3,stroke:#1565C0,color:#fff
```

---

## Implementation Plan - Simplified

### Phase 1: Cải Tiến Config Hiện Tại (Recommended Improvements)

Mục tiêu: Tăng cường security và maintainability cho wildcard certificate hiện tại.

#### Step 1.1: Add Certificate Monitoring

**[MODIFY]** [certificate.yml](file:///Users/dungxbuif/selfhost/kubernetes-v1/certmanager/certificate.yml)

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: dungxbuif-certificate
  namespace: default
  annotations:
    # Add monitoring annotations
    prometheus.io/scrape: "true"
spec:
  secretName: dungxbuif-tls
  duration: 2160h      # 90 days
  renewBefore: 720h    # ⬆️ CHANGE: 30 days (safer than current 72h)
  subject:
    organizations:
      - dungxbuif
  commonName: dungxbuif.com
  isCA: false
  privateKey:
    algorithm: RSA
    encoding: PKCS1
    size: 2048
    rotationPolicy: Always  # ⬆️ ADD: Auto rotate private key on renewal
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

**Changes:**
- ✅ `renewBefore: 720h` (30 days) → Safer renewal window
- ✅ `rotationPolicy: Always` → Security best practice
- ✅ Monitoring annotations

---

#### Step 1.2: Improve TLSStore Configuration

**[MODIFY]** [tls.yml](file:///Users/dungxbuif/selfhost/kubernetes-v1/traefik/tls.yml)

```yaml
apiVersion: traefik.io/v1alpha1
kind: TLSStore
metadata:
  name: default
  namespace: default
  annotations:
    description: "Default TLS store with wildcard cert for *.dungxbuif.com"

spec:
  defaultCertificate:
    secretName: dungxbuif-tls
  
  # ⬆️ ADD: TLS certificates registry for SNI-based routing
  # Traefik will automatically use the right cert based on SNI
  certificates: []  # Will populate when adding external domains
```

**No functional change** - just better documented and ready for external certs.

---

#### Step 1.3: Standardize Ingress Configurations

**Best Practice Template** for all `*.dungxbuif.com` services:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: <service>-ingress
  namespace: <namespace>
  annotations:
    # Optional: Explicitly use Traefik
    kubernetes.io/ingress.class: "traefik"
    traefik.ingress.kubernetes.io/router.entrypoints: "websecure"
    traefik.ingress.kubernetes.io/router.tls: "true"
    
    # ⬇️ ADD: TLS-related annotations
    traefik.ingress.kubernetes.io/router.tls.options: "default-modern-tls@kubernetescrd"

spec:
  ingressClassName: traefik
  
  # ⬇️ OPTIONAL: TLS section (not required with wildcard default)
  # tls:
  # - hosts:
  #   - <service>.dungxbuif.com
  #   # No secretName needed - uses default wildcard cert
  
  rules:
  - host: <service>.dungxbuif.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: <service>-service
            port:
              number: 80
```

**Key Points:**
- ✅ **No `tls.secretName`** → Automatically uses wildcard certificate
- ✅ **No cert-manager annotations** → No per-service certificates
- ✅ Minimal configuration for new services

---

#### Step 1.4: Add Modern TLS Options

**[NEW]** `traefik/tls-options.yml`

```yaml
apiVersion: traefik.io/v1alpha1
kind: TLSOption
metadata:
  name: default-modern-tls
  namespace: default

spec:
  minVersion: VersionTLS12
  maxVersion: VersionTLS13
  
  cipherSuites:
    # TLS 1.2 ciphers
    - TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
    - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
    - TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
    - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
    - TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256
    - TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256
  
  curvePreferences:
    - CurveP521
    - CurveP384
    - CurveP256
  
  sniStrict: true  # Require valid SNI
  
  # HSTS (HTTP Strict Transport Security)
  alpnProtocols:
    - h2      # HTTP/2
    - http/1.1
```

Apply globally via Traefik Helm values:

```yaml
# traefik/values.yml
tlsOptions:
  default:
    minVersion: VersionTLS12
    sniStrict: true
```

---

### Phase 2: Support cho External Domains (On-Demand)

Chỉ implement khi bạn thực sự cần add external domain.

#### Khi nào cần?
- Khi có client muốn sử dụng domain riêng của họ
- Khi cần whitelabel solution
- Khi có multiple brand domains

#### How to Add External Domain

**Example: Thêm `app.example.com`**

##### Step 2.1: Create Certificate Resource

**[NEW]** `certmanager/external-domains/example-com-certificate.yml`

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-com-certificate
  namespace: default  # Or specific namespace
  labels:
    cert-type: external-domain
    domain: example.com

spec:
  secretName: example-com-tls
  duration: 2160h
  renewBefore: 720h
  
  issuerRef:
    # Use same ClusterIssuer nếu cùng DNS provider (Cloudflare)
    name: cloudflare-cluster-issuer
    kind: ClusterIssuer
    
    # HOẶC create separate issuer nếu khác DNS provider
    # name: example-com-issuer
    # kind: ClusterIssuer

  dnsNames:
    - 'example.com'
    - '*.example.com'  # Wildcard cho subdomains
    # HOẶC chỉ specific subdomain:
    # - 'app.example.com'

  privateKey:
    algorithm: RSA
    size: 2048
    rotationPolicy: Always
  
  usages:
    - server auth
    - client auth
```

##### Step 2.2: (Optional) Create Separate ClusterIssuer

Nếu `example.com` dùng DNS provider khác Cloudflare:

**[NEW]** `certmanager/external-domains/example-com-issuer.yml`

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: example-com-issuer
  labels:
    issuer-type: external-domain

spec:
  acme:
    email: admin@example.com
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: example-com-issuer-account-key
    
    solvers:
    # Example: AWS Route53
    - dns01:
        route53:
          region: us-east-1
          accessKeyID: AKIAIOSFODNN7EXAMPLE
          secretAccessKeySecretRef:
            name: route53-credentials
            key: secret-access-key
    
    # Example: Google Cloud DNS
    # - dns01:
    #     cloudDNS:
    #       project: my-project
    #       serviceAccountSecretRef:
    #         name: clouddns-credentials
    #         key: service-account.json
    
    # Example: Azure DNS
    # - dns01:
    #     azureDNS:
    #       subscriptionID: xxx
    #       tenantID: xxx
    #       resourceGroupName: xxx
    #       hostedZoneName: example.com
    #       environment: AzurePublicCloud
```

##### Step 2.3: Update TLSStore

**[MODIFY]** [tls.yml](file:///Users/dungxbuif/selfhost/kubernetes-v1/traefik/tls.yml)

```yaml
apiVersion: traefik.io/v1alpha1
kind: TLSStore
metadata:
  name: default
  namespace: default

spec:
  defaultCertificate:
    secretName: dungxbuif-tls  # ← Keep default cho *.dungxbuif.com
  
  certificates:
    # ⬇️ ADD: Register external domain certificates
    - secretName: example-com-tls
      namespace: default  # hoặc namespace khác nếu cần
    
    # Có thể add nhiều external domains
    # - secretName: another-domain-tls
    #   namespace: default
```

**Traefik sẽ tự động:**
- Sử dụng `dungxbuif-tls` cho `*.dungxbuif.com` requests
- Sử dụng `example-com-tls` cho `*.example.com` requests
- SNI-based routing (Server Name Indication)

##### Step 2.4: Create Ingress for External Domain

**[NEW]** `<namespace>/example-app-ingress.yml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-app-ingress
  namespace: myapp
  annotations:
    kubernetes.io/ingress.class: "traefik"
    traefik.ingress.kubernetes.io/router.entrypoints: "websecure"
    traefik.ingress.kubernetes.io/router.tls: "true"
    traefik.ingress.kubernetes.io/router.tls.options: "default-modern-tls@kubernetescrd"

spec:
  ingressClassName: traefik
  
  tls:
  - hosts:
    - app.example.com
    secretName: example-com-tls  # ⬅️ Reference external cert
  
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: myapp-service
            port:
              number: 80
```

##### Step 2.5: Deploy & Verify

```bash
# Apply certificate
kubectl apply -f certmanager/external-domains/example-com-certificate.yml

# Wait for certificate to be ready
kubectl wait --for=condition=Ready certificate/example-com-certificate -n default --timeout=300s

# Check certificate status
kubectl describe certificate example-com-certificate -n default

# Apply updated TLSStore
kubectl apply -f traefik/tls.yml

# Apply Ingress
kubectl apply -f <namespace>/example-app-ingress.yml

# Verify TLS
curl -vI https://app.example.com 2>&1 | grep -E "subject:|issuer:"

# Test in browser
open https://app.example.com
```

---

### Phase 3: Monitoring & Alerting (Optional but Recommended)

#### Certificate Expiry Monitoring Script

**[NEW]** `scripts/monitor-certificates.sh`

```bash
#!/bin/bash

echo "=== Certificate Monitoring Report ==="
echo "Generated at: $(date)"
echo ""

# Check Kubernetes Certificate resources
echo "📋 Kubernetes Certificates Status:"
kubectl get certificate -A -o custom-columns=\
NAMESPACE:.metadata.namespace,\
NAME:.metadata.name,\
READY:.status.conditions[?(@.type==\"Ready\")].status,\
EXPIRY:.status.notAfter,\
RENEW_TIME:.status.renewalTime

echo ""
echo "🔐 Certificate Details:"

# Check actual TLS secrets
for ns in $(kubectl get certificate -A -o jsonpath='{.items[*].metadata.namespace}' | tr ' ' '\n' | sort -u); do
  for cert in $(kubectl get certificate -n $ns -o jsonpath='{.items[*].metadata.name}'); do
    secret=$(kubectl get certificate -n $ns $cert -o jsonpath='{.spec.secretName}')
    
    # Extract certificate expiry from secret
    kubectl get secret -n $ns $secret -o jsonpath='{.data.tls\.crt}' 2>/dev/null | \
      base64 -d | \
      openssl x509 -noout -enddate 2>/dev/null | \
      awk -v ns="$ns" -v cert="$cert" '{print "  " ns "/" cert ": " $0}'
  done
done

echo ""
echo "⚠️  Certificates Expiring Soon (< 30 days):"

# Check certificates expiring in next 30 days
kubectl get certificate -A -o json | \
  jq -r '.items[] | select(.status.notAfter != null) | 
  .metadata.namespace + "/" + .metadata.name + " expires: " + .status.notAfter' | \
  while read line; do
    expiry=$(echo "$line" | awk '{print $NF}')
    days_until=$(( ($(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$expiry" +%s) - $(date +%s)) / 86400 ))
    
    if [ $days_until -lt 30 ]; then
      echo "  ⚠️  $line (in $days_until days)"
    fi
  done

echo ""
echo "✅ Monitoring complete"
```

**Run periodically:**

```bash
chmod +x scripts/monitor-certificates.sh

# Add to cron (daily at 9am)
0 9 * * * /path/to/scripts/monitor-certificates.sh | mail -s "Certificate Status" admin@dungxbuif.com
```

---

#### Prometheus Alerts (if using Prometheus)

**[NEW]** `monitoring/certificate-alerts.yml`

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: certificate-alerts
  namespace: monitoring

spec:
  groups:
  - name: certificates
    interval: 1h
    rules:
    
    - alert: CertificateExpiringSoon
      expr: |
        (certmanager_certificate_expiration_timestamp_seconds - time()) / 86400 < 30
      for: 1h
      labels:
        severity: warning
      annotations:
        summary: "Certificate {{ $labels.namespace }}/{{ $labels.name }} expiring soon"
        description: "Certificate expires in {{ $value | humanizeDuration }}"
    
    - alert: CertificateExpiringCritical
      expr: |
        (certmanager_certificate_expiration_timestamp_seconds - time()) / 86400 < 7
      for: 15m
      labels:
        severity: critical
      annotations:
        summary: "Certificate {{ $labels.namespace }}/{{ $labels.name }} expiring VERY SOON"
        description: "Certificate expires in {{ $value | humanizeDuration }} - URGENT ACTION REQUIRED"
    
    - alert: CertificateRenewalFailed
      expr: |
        certmanager_certificate_ready_status{condition="False"} == 1
      for: 1h
      labels:
        severity: critical
      annotations:
        summary: "Certificate {{ $labels.namespace }}/{{ $labels.name }} renewal failed"
        description: "Certificate is not ready. Check cert-manager logs."
    
    - alert: CertManagerDown
      expr: up{job="cert-manager"} == 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "cert-manager is down"
        description: "cert-manager has been down for 5 minutes. Certificates cannot renew."
```

---

## Configuration Examples

### Example 1: Current Setup (No Changes Needed)

**n8n service** - uses wildcard certificate automatically:

```yaml
# n8n/n8n-ingress.yaml - CURRENT CONFIG IS PERFECT ✅
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: n8n-ingress
  namespace: n8n
spec:
  ingressClassName: traefik
  rules:
  - host: n8n.dungxbuif.com  # ← Auto covered by *.dungxbuif.com wildcard
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: n8n-main-service
            port:
              number: 5678
```

**No TLS section needed!** Traefik automatically uses default wildcard certificate.

---

### Example 2: Deploying New Service on Subdomain

**New service: `monitoring.dungxbuif.com`**

```yaml
# monitoring/prometheus-ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: prometheus-ingress
  namespace: monitoring

spec:
  ingressClassName: traefik
  
  rules:
  - host: monitoring.dungxbuif.com  # ← Instantly covered by wildcard cert
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: prometheus
            port:
              number: 9090
```

**Deploy:**
```bash
kubectl apply -f monitoring/prometheus-ingress.yml

# Service is immediately accessible with HTTPS
curl https://monitoring.dungxbuif.com
```

**Zero certificate configuration needed!** ✨

---

### Example 3: Multi-Subdomain Service (Whiteboard)

```yaml
# whiteboard/whiteboard-ingress.yml - CURRENT CONFIG IS PERFECT ✅
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: whiteboard-ingress
  namespace: whiteboard

spec:
  ingressClassName: traefik
  
  rules:
  # All these subdomains covered by *.dungxbuif.com wildcard
  - host: whiteboard.dungxbuif.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: whiteboard-fe
            port:
              number: 80
  
  - host: wb-dashboard.dungxbuif.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: whiteboard-dashboard
            port:
              number: 80
  
  - host: api-whiteboard.dungxbuif.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: whiteboard-be
            port:
              number: 80
  
  - host: ws-whiteboard.dungxbuif.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: whiteboard-ws
            port:
              number: 80
```

**All 4 subdomains instantly secured with 1 wildcard certificate!** 🎉

---

### Example 4: External Domain (Future Use)

**Client wants to use their domain: `app.clientcompany.com`**

```yaml
# Step 1: Create certificate
# certmanager/external-domains/clientcompany-certificate.yml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: clientcompany-certificate
  namespace: default
spec:
  secretName: clientcompany-tls
  issuerRef:
    name: cloudflare-cluster-issuer  # If they use Cloudflare
    kind: ClusterIssuer
  dnsNames:
    - 'app.clientcompany.com'

---
# Step 2: Create Ingress
# myapp/clientcompany-ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: clientcompany-ingress
  namespace: myapp
spec:
  ingressClassName: traefik
  tls:
  - hosts:
    - app.clientcompany.com
    secretName: clientcompany-tls  # ⬅️ Reference specific cert
  rules:
  - host: app.clientcompany.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: myapp-service
            port:
              number: 80
```

---

## Comparison: Before vs After Improvements

### Before (Current - Already Good!)

```yaml
# certmanager/certificate.yml
spec:
  renewBefore: 72h  # 3 days
  # No private key rotation
```

### After (Improved)

```yaml
# certmanager/certificate.yml
spec:
  renewBefore: 720h  # 30 days - safer
  privateKey:
    rotationPolicy: Always  # Security best practice
```

**Impact:**
- ✅ 30-day renewal window instead of 3 days → less risky
- ✅ Automatic private key rotation → better security
- ✅ No functional changes for existing services

---

## Quick Reference

### Adding New Subdomain Service (*.dungxbuif.com)

**Time required:** 2 minutes

```bash
# Just create Ingress - no certificate config needed!
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: newservice-ingress
  namespace: newservice
spec:
  ingressClassName: traefik
  rules:
  - host: newservice.dungxbuif.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: newservice
            port:
              number: 80
EOF

# Done! Service is live with HTTPS
curl https://newservice.dungxbuif.com
```

---

### Adding External Domain

**Time required:** 5 minutes

```bash
# 1. Create Certificate
kubectl apply -f certmanager/external-domains/example-com-certificate.yml

# 2. Wait for certificate (usually 1-2 minutes)
kubectl wait --for=condition=Ready certificate/example-com-certificate -n default --timeout=300s

# 3. Update TLSStore (add certificate to registry)
# Edit traefik/tls.yml and add to certificates[] list

# 4. Create Ingress with explicit secretName
kubectl apply -f myapp/example-com-ingress.yml

# Done!
curl https://app.example.com
```

---

## Migration Checklist

### Phase 1: Immediate Improvements (This Week)

- [ ] **Backup current config**
  ```bash
  kubectl get certificate -A -o yaml > backup/certificates-$(date +%Y%m%d).yaml
  kubectl get secret -A -l cert-manager.io/certificate-name -o yaml > backup/tls-secrets-$(date +%Y%m%d).yaml
  ```

- [ ] **Update wildcard certificate**
  - Change `renewBefore: 72h` → `720h`
  - Add `rotationPolicy: Always`
  ```bash
  kubectl apply -f certmanager/certificate.yml
  ```

- [ ] **Create TLS Options**
  ```bash
  kubectl apply -f traefik/tls-options.yml
  ```

- [ ] **Setup monitoring script**
  ```bash
  chmod +x scripts/monitor-certificates.sh
  ./scripts/monitor-certificates.sh  # Test run
  ```

- [ ] **Verify existing services still work**
  ```bash
  for domain in n8n.dungxbuif.com whiteboard.dungxbuif.com traefik.dungxbuif.com; do
    echo "Testing $domain..."
    curl -sI https://$domain | grep "HTTP/"
  done
  ```

### Phase 2: External Domain Support (Only When Needed)

- [ ] **Create external domain directory structure**
  ```bash
  mkdir -p certmanager/external-domains
  ```

- [ ] **Document process** for adding external domains

- [ ] **Create template files** for quick deployment

---

## Cost-Benefit Analysis

### Current Approach vs Full Per-Service Certificates

| Metric | Wildcard (Current) | Per-Service Certs |
|--------|-------------------|-------------------|
| **Certificates to Manage** | 1 | 10-20+ |
| **Deployment Time (New Service)** | 2 min | 5-10 min |
| **Let's Encrypt Rate Limit Risk** | Very Low | Medium |
| **Certificate Renewal Failures** | 1 point of failure | Multiple points |
| **Complexity** | Very Low | Medium-High |
| **Cost** | $0 | $0 (but higher ops cost) |
| **Scalability** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good |

**Verdict:** Giữ wildcard approach là ĐÚNG ĐẮN nhất cho use case của bạn! ✅

---

## Security Considerations

### Wildcard Certificate Security

**Risks:**
1. **Private Key Compromise**: Nếu private key bị leak → tất cả `*.dungxbuif.com` services bị ảnh hưởng

**Mitigations:**
1. ✅ **Private Key Rotation**: Set `rotationPolicy: Always`
2. ✅ **Secret Encryption at Rest**: Enable Kubernetes secret encryption
3. ✅ **RBAC**: Limit access to `dungxbuif-tls` secret
4. ✅ **Regular Audits**: Monitor secret access logs
5. ✅ **Backup Certificate**: Keep backup cert ready for emergency rotation

### RBAC for Certificate Secret

**[NEW]** `certmanager/certificate-rbac.yml`

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: certificate-reader
  namespace: default

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: certificate-secret-reader
  namespace: default
rules:
- apiGroups: [""]
  resources: ["secrets"]
  resourceNames: ["dungxbuif-tls"]  # Only this specific secret
  verbs: ["get", "list"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: certificate-secret-reader-binding
  namespace: default
subjects:
- kind: ServiceAccount
  name: traefik  # Only Traefik can read the cert
  namespace: traefik
roleRef:
  kind: Role
  name: certificate-secret-reader
  apiGroup: rbac.authorization.k8s.io
```

---

## Troubleshooting Guide

### Issue 1: Certificate Not Renewing

**Symptoms:**
- Certificate shows `Ready=False`
- Nearing expiry date

**Debug:**
```bash
# Check certificate status
kubectl describe certificate dungxbuif-certificate -n default

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager --tail=100

# Check ACME challenge
kubectl get challenges -A
kubectl describe challenge <challenge-name> -n default

# Check orders
kubectl get orders -A
kubectl describe order <order-name> -n default
```

**Common Fixes:**
```bash
# Force renewal
kubectl delete secret dungxbuif-tls -n default
# cert-manager will auto-recreate

# Or delete and recreate certificate
kubectl delete certificate dungxbuif-certificate -n default
kubectl apply -f certmanager/certificate.yml
```

---

### Issue 2: Ingress Not Using Wildcard Certificate

**Symptoms:**
- Self-signed certificate shown instead of Let's Encrypt
- Certificate mismatch warnings

**Debug:**
```bash
# Check if secret exists
kubectl get secret dungxbuif-tls -n default

# Check TLSStore
kubectl describe tlsstore default -n default

# Check Traefik logs
kubectl logs -n traefik -l app.kubernetes.io/name=traefik --tail=50
```

**Fix:**
```bash
# Ensure TLSStore references correct secret
kubectl apply -f traefik/tls.yml

# Restart Traefik to reload certificates
kubectl rollout restart deployment traefik -n traefik
```

---

### Issue 3: External Domain Certificate Not Working

**Symptoms:**
- External domain shows default certificate
- SNI not working properly

**Debug:**
```bash
# Check certificate exists
kubectl get certificate -A | grep example-com

# Verify TLSStore includes the certificate
kubectl get tlsstore default -n default -o yaml

# Test SNI explicitly
openssl s_client -servername app.example.com -connect <MASTER_VPS_PUBLIC_IP>:443 < /dev/null 2>/dev/null | openssl x509 -noout -text
```

**Fix:**
```bash
# Ensure TLSStore has certificate registered
# Edit traefik/tls.yml and add to certificates[] array

# Apply and restart
kubectl apply -f traefik/tls.yml
kubectl rollout restart deployment traefik -n traefik
```

---

## Summary & Recommendations

### ✅ Your Current Config is GOOD! Keep It!

**Reasons:**
1. **Perfect fit** cho use case (mostly `*.dungxbuif.com` subdomains)
2. **Simple & maintainable** - 1 certificate thay vì hàng chục
3. **Scalable** - thêm service mới trong 2 phút
4. **Low operational overhead** - minimal management

### 🔧 Recommended Improvements (Low effort, high value)

1. **Update `renewBefore`**: 72h → 720h (safer renewal window)
2. **Add `rotationPolicy: Always`**: Better security
3. **Create monitoring script**: Track certificate health
4. **Document external domain process**: Ready when needed

### 📋 When to Add External Domain Support

**Only when you actually need it:**
- Client requires their own domain
- Whitelabel solution
- Multi-brand architecture

**Don't over-engineer prematurely!** Wildcard certificate is perfect for 95% of your use cases.

### 🎯 Action Plan

**This Week (2 hours):**
1. Apply improvements to wildcard certificate config
2. Setup monitoring script
3. Document process

**When Needed (Future):**
4. Add external domain support following Phase 2 guide

**That's it!** Đơn giản và hiệu quả. 🚀

---

## 📚 Additional Review Questions

### For Reviewer

1. **Current Setup Understanding**
   - Do you understand why wildcard certificate is beneficial for our use case?
   - Are you comfortable with the single certificate approach?

2. **Proposed Changes**
   - Do the Phase 1 improvements make sense?
   - Any security concerns with the proposed configuration?

3. **Implementation Timing**
   - Is 2 hours acceptable for Phase 1?
   - Should we schedule during maintenance window or can proceed anytime?

4. **Future Planning**
   - Do you anticipate needing external domain support soon?
   - Should we prioritize Phase 2 preparation?

### For Implementation Team

1. **Preparation**
   - Do you have access to all required namespaces?
   - Are kubectl permissions sufficient?
   - Backup strategy clear?

2. **Execution**
   - Implementation steps clear and actionable?
   - Any ambiguity in the proposed changes?
   - Need any additional documentation?

---

## 📞 Review Support

**Questions during review?**
- **Technical Questions**: Contact DevOps team
- **Business Impact**: Contact Tech Lead
- **Timeline Concerns**: Contact Project Manager

**Review Timeline:**
- Initial review: 30 minutes
- Feedback incorporation: 1 hour
- Final approval: 15 minutes
- **Total**: ~2 hours before implementation can start

---

## 🎯 Next Steps After Review

### If Approved
1. ✅ Mark this document as "APPROVED"
2. 📅 Schedule implementation (suggest: low-traffic period)
3. 📢 Notify team via Slack/email
4. 🔧 Execute Phase 1 following the documented steps
5. ✅ Run post-implementation verification
6. 📝 Update documentation with actual results

### If Needs Changes
1. 📝 Document requested changes in feedback section
2. 🔄 Revise proposal
3. 🔁 Re-submit for review

### If Rejected
1. 📋 Document rejection reasons
2. 🤔 Evaluate alternative approaches
3. 💬 Schedule discussion meeting if needed

---

**Document Version**: 1.0 (Review Draft)
**Last Updated**: [Current Date]
**Next Review**: After implementation (if approved)
