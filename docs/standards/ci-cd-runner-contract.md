---
type: Standard
title: CI/CD Runner Contract
description: "Chuẩn CI/CD dùng chung cho các workload chạy trong homelab"
status: stable
generated:
  by: codex
  at: "2026-11-01T00:00:00+07:00"
stale_after: "2027-01-29T00:00:00+07:00"
---

# CI/CD Runner Contract

Đây là chuẩn tối thiểu cho mọi repository có component `lab-runtime`. Mục tiêu là
chỉnh sửa ở máy điều khiển, còn validate, build image và deploy đều chạy trên
GitLab Runner của lab. Không chạy build/test/deploy nặng trên máy điều khiển.

## Phạm vi hiện tại

Runner CI áp dụng cho các app đang chạy trong lab:

`homepage`, `db-management`, `homelab-ops`, `relayhub`, `couchloom`, `devtool`,
`k8s-syntax`, `mac-ocr`, `mezonhook`, `my-family-tree` và
`homelab-automation`.

`mypocket` không thuộc đợt này vì đang phát triển dở. `flotsam`, `doino` và
các project không còn deploy không được đưa vào runner scope. Client ngoài lab
và source-only dùng [Component Delivery Scope](./component-delivery-scope.md).

## Hợp đồng runner

- Runner: VM100, rootless Docker, tag `homelab-rootless`.
- Runner project scope phải bị khóa vào đúng danh sách app đang chạy; không mở
  runner cho toàn GitLab và không đưa `mypocket` vào nhầm.
- `concurrent = 2`, `limit = 2`, `request_concurrency = 2`: tăng throughput vừa
  phải sau khi xác nhận VM100 còn khoảng 11GiB available. Không tăng tiếp nếu
  chưa có số liệu queue time và memory thực tế.
- Giới hạn mỗi job hiện tại: `memory = 2g`, `cpus = 1`; service sidecar tối đa
  `3g`. Nếu job vẫn OOM, đo memory trước khi tăng giới hạn.
- Không ghi runner token, password hay secret vào vault docs. Credential chỉ ở
  GitLab/1Password theo chuẩn secrets.

## Hợp đồng pipeline

Mỗi `lab-runtime` repository phải có `.gitlab-ci.yml` với các nguyên tắc sau:

1. Có stage validate và chạy lint/test/typecheck phù hợp với project.
2. Nếu dùng image native, chọn base image tương thích runtime; ưu tiên Debian/
   Bookworm khi dependency cung cấp binary glibc. Không mặc định dùng Alpine.
3. Chỉ dùng image nền đã được runner allow-list; không dùng wildcard để chữa
   lỗi nhanh. Image mới phải được thêm theo đúng version và ghi lý do.
4. Image ứng dụng phải build/push vào registry chung qua `LAB_REGISTRY_HOST` và
   credential `LAB_REGISTRY_PUSH_*`/`LAB_REGISTRY_PULL_*`; không dùng
   `CI_REGISTRY` cho registry vận hành của lab.
5. Release job phải kiểm tra tag có ancestry từ protected production branch
   trước khi push image, migrate hoặc deploy.
6. Deploy production luôn manual, protected và dùng image immutable (digest/tag
   đã xác định). Pipeline phải có health check sau deploy.
7. Agent không tự merge vào `main`/`master`/`prod` và không tự deploy production;
   merge/release là bước owner duyệt.

## Thêm một app mới

1. Xác nhận app là `lab-runtime`, có repo GitLab và project doc trong vault.
2. Thêm project vào runner scope; không mở rộng quyền runner chung.
3. Kiểm tra toàn bộ image trong pipeline với allow-list trên VM100. Nếu thiếu,
   thêm đúng image/version rồi restart runner có backup config.
4. Chạy pipeline trên branch riêng, sửa đến khi validate xanh.
5. Chỉ sau khi protected branch có commit hợp lệ mới tạo release tag, build/push
   registry chung, deploy manual và verify health.
6. Ghi receipt vào project doc: commit, pipeline/job, image digest, deploy,
   health check, rollback và backup/restore evidence nếu app có data.

## Bài học đã ghi nhận

| Hiện tượng | Nguyên nhân gốc | Chuẩn xử lý |
|---|---|---|
| Job pending dù runner online | Runner bị lock chỉ vào homepage và automation | Giữ runner locked nhưng gán đủ active project; kiểm tra scope trước khi debug code |
| `disallowed image` | Allow-list runner không có image job dùng | Thêm đúng image/version, không wildcard |
| Rollup native package lỗi trên Node Alpine | Binary glibc không chạy trên musl | Dùng `node:20-bookworm-slim` cho job đó |
| `git: not found` trong RelayHub | Script CI gọi `git diff` nhưng image thiếu git | Cài công cụ thật sự được script dùng trong image job |
| Next build bị `SIGKILL`, container `OOMKilled` | Job chỉ có 512MB | Chuẩn runner hiện tại là 2GB/job; vẫn phải đo trước khi tăng |
| Queue dài sau khi retry | Runner chỉ có một slot và job build lâu | Dùng tối đa 2 slot với giới hạn 2GB/job; chỉ tăng tiếp khi có số liệu chứng minh an toàn |
| `devtool` không build được `@collab/runtime` | Workspace `collab` build trước `packages/diagram-kit`, nhưng script của nó không build dependency này trước khi chạy `tsc` | Giữ pipeline đỏ; sửa dependency/build order ở app trước khi release, không nới gate để che lỗi |

## Receipt bắt buộc sau mỗi bài/pipeline

Sau mỗi lần học, sửa hoặc rollout CI phải note lại trong project doc hoặc
deployment receipt:

- repo, branch/tag, commit SHA và pipeline/job URL hoặc ID;
- trạng thái từng stage và kết quả cuối cùng;
- lỗi thật và root cause, không chỉ copy message bề mặt;
- thay đổi runner/image/resource đã thực hiện;
- bằng chứng verify: test, image push, deploy, health check hoặc rollback;
- việc còn lại, owner và điều kiện để release.

Không ghi “đã xong” khi chỉ pipeline cũ xanh; phải chỉ rõ pipeline của commit
đã sửa. Job fail cũ được giữ làm lịch sử và phải có root cause.

## Bằng chứng rollout 2026-11-01

- `k8s-syntax` pipeline #653: validate xanh.
- `couchloom` pipeline #655: validate xanh.
- `relayhub` job #2133: xanh sau khi bổ sung `git` cho image job.
- `my-family-tree` job cũ #2128 đã OOM; retry #2165 chạy sau khi nâng giới hạn
  runner lên 2GB và phải được kiểm tra riêng.
- `mezonhook` job cũ #2130 lỗi do Alpine/musl; commit sửa dùng Bookworm đã push
  và pipeline mới phải được xác nhận riêng.
- `devtool` job #2142 phát hiện lỗi workspace/build order: `@collab/runtime`
  không resolve được `@collab/diagram-kit`; đây là lỗi app đang chờ owner sửa,
  không phải lỗi runner.

Các mục pending không được coi là release evidence cho đến khi job mới xanh.
