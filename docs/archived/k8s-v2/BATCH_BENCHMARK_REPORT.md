# BÁO CÁO KIỂM THỬ HIỆU NĂNG BATCH API (POST /v1/batches)

**Thời gian thực hiện:** 16/08/2026 23:55 (GMT+7)  
**Đối tượng kiểm thử:** Ảnh gốc từ link Komu CDN (`https://cdn.komu.vn/1783755414765047808/2089023546947801088.jpg` - `439.5 KB` Base64)  
**Phương thức:** Đóng gói nhiều ảnh vào **1 Request duy nhất** gửi tới endpoint `POST /v1/batches` của Mac OCR Proxy.

---

## 1. BẢNG TỔNG HỢP KẾT QUẢ CÁC GÓI BATCH

| Quy mô Batch | Dung lượng 1 Request | Thời gian Ingest Payload & cấp Job ID | Thời gian xử lý xong cả mẻ | Throughput thực tế | Tỉ lệ thành công |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Gói 10 ảnh** | `4.29 MB` | **1.57 giây** | **5.47 giây** | **1.83 ảnh/giây** *(~110 ảnh/phút)* | **100% (10/10)** |
| **Gói 30 ảnh** | `12.88 MB` | **1.24 giây** | **11.71 giây** | **2.56 ảnh/giây** *(~154 ảnh/phút)* | **100% (30/30)** |
| **Gói 60 ảnh** | `25.75 MB` | **2.44 giây** | **23.42 giây** | **2.56 ảnh/giây** *(~154 ảnh/phút)* | **100% (60/60)** |

---

## 2. PHÂN BỐ ĐỘ TRỄ TỪNG ẢNH TRONG BATCH (PERCENTILES LATENCY)

> *Thời gian End-to-End được tính từ lúc bắt đầu đẩy toàn bộ gói JSON Batch qua mạng cho đến khi từng ảnh trong mẻ có kết quả OCR xong xuôi.*

| Gói Batch | Nhanh nhất (Min) | p50 (Median) | Trung bình (Avg) | p90 | p95 | p99 | Chậm nhất (Max) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Batch 10 ảnh** | **2.31s** | **4.29s** | **4.04s** | **5.46s** | **5.46s** | **5.46s** | **5.46s** |
| **Batch 30 ảnh** | **1.76s** | **7.01s** | **6.86s** | **11.12s** | **11.47s** | **11.71s** | **11.71s** |
| **Batch 60 ảnh** | **2.81s** | **6.85s** | **10.54s** | **21.05s** | **21.87s** | **23.42s** | **23.42s** |

---

## 3. ĐÁNH GIÁ KHI DÙNG BATCH API

1. **Tiết kiệm Request HTTP:** Thay vì phải mở 60 kết nối HTTP riêng lẻ, client chỉ cần gọi **1 request duy nhất** (`25.75 MB`) để ném 60 ảnh vào hệ thống.
2. **Thời gian Server Ingest:** Rất nhanh (**1.2s - 2.4s**) để K8s Proxy đọc, parse JSON Base64 và đẩy toàn bộ 60 jobs vào Redis Queue.
3. **Độ ổn định:** Toàn bộ 100/100 ảnh trong 3 đợt Batch đều hoàn thành trọn vẹn, không xảy ra nghẽn mạng hay tràn bộ nhớ.
