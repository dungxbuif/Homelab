# BÁO CÁO KIỂM THỬ HIỆU NĂNG & ĐỘ TRỄ HỆ THỐNG MAC OCR (BENCHMARK REPORT)

**Thời gian thực hiện:** 16/08/2026 23:51 (GMT+7)  
**Môi trường kiểm thử:** Production Kubernetes Cluster (K8s Proxy HPA 1-5 Pods) + Apple Silicon Native Worker  
**Đối tượng thử nghiệm:** Ảnh 2K khổ dọc (`946 x 2048 px`, dung lượng Base64 payload: `439.5 KB`, ~1,051 ký tự tiếng Việt/ảnh)  
**Giao thức kiểm thử:** Gửi HTTP POST JSON Base64 $\rightarrow$ Redis Queue $\rightarrow$ Apple Vision Native OCR Engine $\rightarrow$ Poll kết quả.

---

## 1. TỔNG QUAN KẾT QUẢ KIỂM THỬ

| Chỉ số tổng quan | Giá trị đo đạc thực tế |
| :--- | :--- |
| **Tổng số lượng ảnh kiểm thử** | **200 ảnh** |
| **Số lượng clients gửi đồng thời (Concurrency)** | **20 luồng độc lập** |
| **Tỉ lệ thành công (Success Rate)** | **100.0% (200/200)** |
| **Tỉ lệ lỗi (Error / Timeout Rate)** | **0.0% (0/200)** |
| **Tổng thời gian hoàn thành toàn bộ đợt tải** | **70.35 giây (~1.17 phút)** |
| **Throughput xử lý trung bình (RPS)** | **2.84 ảnh / giây** |
| **Công suất ước tính theo phút** | **~171 ảnh / phút** |
| **Công suất ước tính theo giờ** | **~10,235 ảnh / giờ** |

---

## 2. PHÂN BỐ ĐỘ TRỄ THỜI GIAN NHẬN KẾT QUẢ (LATENCY PERCENTILES)

> *Thời gian được tính trọn vẹn từ lúc Client bắt đầu gửi chuỗi Base64 440KB qua mạng, qua K8s Proxy ingest, xếp hàng Redis, Native Engine nhận dạng chữ và trả về Client hoàn tất.*

```
Min: 0.78s |━━━━━━━━
p50: 6.98s |━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
p90: 7.18s |━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
p95: 7.33s |━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
p99: 7.68s |━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Max: 7.77s |━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

| Mốc Percentile | Độ trễ (ms) | Độ trễ (giây) | Trải nghiệm & Phân loại |
| :--- | :---: | :---: | :--- |
| **Nhanh nhất (Min)** | `780 ms` | **0.78s** | Request đầu tiên khi hàng đợi rỗng, xử lý tức thì |
| **p50 (Median)** | `6,984 ms` | **6.98s** | 50% người dùng nhận kết quả trong vòng dưới 6.9 giây |
| **Trung bình (Avg)** | `6,721 ms` | **6.72s** | Thời gian chờ trung bình trong điều kiện 20 luồng ném liên tục |
| **p90** | `7,179 ms` | **7.18s** | 90% người dùng nhận kết quả trong vòng dưới 7.18 giây |
| **p95** | `7,331 ms` | **7.33s** | 95% người dùng nhận kết quả trong vòng dưới 7.33 giây |
| **p99** | `7,683 ms` | **7.68s** | 99% người dùng nhận kết quả trong vòng dưới 7.68 giây |
| **Chậm nhất (Max)** | `7,767 ms` | **7.77s** | Request cuối cùng nằm ở đuôi hàng đợi |

---

## 3. GIÁM SÁT TÀI NGUYÊN HỆ THỐNG TRONG QUÁ TRÌNH TẢI (K8S PODS MONITOR)

Trong suốt quá trình xả tải liên tục 200 ảnh dung lượng lớn, hệ thống giám sát K8s ghi nhận:

- **Cơ chế Auto-scaling (HPA):**
  - `macocr-proxy` tự động mở rộng từ 1 pod lên **5 pods** (`macocr-proxy-5fdd89567c-*`) để phân tán tải giải mã Base64 JSON và quản lý session Redis.
- **Mức độ tiêu thụ CPU / RAM của các Pods:**
  - **CPU:** Dao động ổn định từ **37m đến 128m CPU** / Pod (Tổng mức tiêu thụ toàn bộ 5 pod chưa tới 0.5 vCPU).
  - **RAM:** Cực kỳ nhẹ và ổn định ở mức **14Mi đến 22Mi RAM** / Pod.
  - **Memory Leak:** `0%` (RAM không tăng tích lũy sau khi hoàn thành đợt tải lớn).

---

## 4. KẾT LUẬN & ĐÁNH GIÁ CHUNG

1. **Độ ổn định:** Hệ thống hoạt động tin cậy tuyệt đối với 0% lỗi dưới áp lực 20 client liên tục.
2. **Khả năng chịu tải:** Với cấu hình 1 worker Native Apple Silicon hiện tại, hệ thống xử lý ổn định ở mức **~10,000 ảnh 2K/giờ**.
3. **Độ trễ:** p95 và p99 được kiểm soát chặt chẽ trong khoảng **7.3s - 7.6s** khi chạy full tải 20 luồng đồng thời.
