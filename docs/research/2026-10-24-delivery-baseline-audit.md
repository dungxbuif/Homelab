# Delivery baseline audit — 2026-10-24

## Quyết định hiện tại

Ưu tiên db-management deploy và CI/CD hoàn chỉnh trước; tiếp theo chuẩn hóa
từng app đang running. Không thêm stack vào critical path. Kestra là phase
operations sau baseline; Semaphore chỉ retire sau khi job consumers đã chuyển.

Canonical implementation plan nằm tại [homelab-ops plan](../../../../homelab-ops-task1/docs/superpowers/plans/2026-10-24-db-management-minimum-delivery.md),
thiết kế tại [minimum delivery spec](../../../../homelab-ops-task1/docs/superpowers/specs/2026-10-24-db-management-minimum-delivery.md).
Hai link đã kiểm tra theo checkout layout hiện tại; bản canonical repo-relative là
`homelab-ops:docs/superpowers/plans/2026-10-24-db-management-minimum-delivery.md`.

## Evidence fresh, read-only

- Swarm: Pi5/rpivn leader Ready, VM100 Ready, VM110/db-ops Ready; orangepizero3 Down.
- VM110: 5 db-management services 1/1; web/API/CloudBeaver/Databasus healthy;
  worker Up nhưng chưa có application heartbeat evidence.
- [Pipeline 472](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/pipelines/472):
  quality, ops-contract, build-images, container-scan, release-manifest success;
  [deploy job 1433](https://gitlab.dungxbuif.com/dungxbuif/db-management/-/jobs/1433)
  manual. Chưa chứng minh end-to-end CD.
- Project runner2 `db-management-local-ci` online; project runner API không trả
  runner deploy LAN chuyên biệt khác.
- Wi-Fi active resolver: 8.8.8.8/8.8.4.4; domain db-management trả VPS
  103.82.21.202; HTTPS thông thường lỗi self-signed certificate.
- Probe cùng hostname trực tiếp Pi5 10.10.0.5: HTTP200, TLS verify0. Không cần
  thay certificate Pi5 để chữa lỗi DNS client này. `--resolve` chỉ là diagnostic,
  không phải acceptance workaround.
- CI YAML vẫn bắt buộc 1Password agent socket; deploy không needs manifest;
  manifest chỉ tags/opsRef; deploy playbook cuối chỉ list service names.
- Bun CI 1.3.14 khác API/worker images 1.4.4; active runtime policy chưa có VM110;
  docs/lock còn thông tin stale.

## Những gì chưa được chứng minh

DHCP MikroTik toàn LAN, browser secure-DNS, roaming DNS, public reachability
restriction thực tế, runner isolation đầy đủ, credential scopes/rotation,
backup schedules/last-good hiện tại, restore drill, worker job health và rollback.
Không gọi audit này là kiểm toán đầy đủ mọi app. Full inventory là T1 trong plan.

Backup transition record ngày 2026-10-23 ghi coverage paused; không được suy ra
coverage đã phục hồi từ dashboard hoặc containers healthy. Không thay schedules,
production data, DNS, credentials hay deployment trong lần audit/lập plan này.

## Ownership

App code/CI ở `db-management`; infrastructure/release code ở `homelab-ops`;
vault này giữ evidence/runbook. Plan chưa được thực thi; các checkbox pending.
