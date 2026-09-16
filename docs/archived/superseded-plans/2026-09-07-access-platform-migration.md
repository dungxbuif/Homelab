# Homelab Access Platform Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Network mutations, production database operations and cutovers are sequential, never delegated concurrently against the same environment.

**Goal:** Thay Rathole/public ingress bằng Pangolin (ngoại lệ BDS dùng Cloudflare Tunnel), chuyển BDS về local, đưa RustDesk/Headscale vào trạng thái đã kiểm chứng, và cài/verify MikroTik Back to Home khi phần cứng cho phép.

**Architecture:** Dựng đường mới cạnh đường cũ, đổi từng hostname, giữ đường quản trị độc lập. VPS chạy Pangolin/Gerbil/Traefik cùng Headscale/DERP và RustDesk; Newt ở nhà truy cập được các backend. BDS app dự kiến chạy Mac mini, database local là nhánh riêng cần xác nhận; Cloudflare Tunnel đi TCP HTTP/2. Caddy/AdGuard tiếp tục phục vụ LAN.

**Tech Stack:** Docker Compose/Swarm, Traefik, Pangolin/Newt/Gerbil, Headscale/Tailscale/DERP, RustDesk hbbs/hbbr, cloudflared, PostgreSQL, MikroTik RouterOS.

**Spec:** Quyết định người dùng ngày 2026-09-07 trong task này: (1) thay Rathole và public bằng Pangolin; (2) move BDS local dùng Cloudflare Tunnel; (3) BTH và verify; (4) RustDesk và Headscale. Đây là runbook lập kế hoạch, chưa có quyền triển khai được suy ra từ yêu cầu viết plan.

## Global Constraints

- Chỉ plan trong lượt này; chưa SSH thay đổi host, chưa deploy, đổi DNS, restart service hoặc migrate DB.
- Không hứa zero downtime: ingress có thể ngắt connection đang mở; chuyển DB bằng dump/restore cần cửa sổ dừng ghi đo từ rehearsal.
- Không xóa database/volume/cert/key, không `docker compose down -v`, không prune toàn host. Không reset hoặc upgrade router trong đợt ingress.
- Giữ image digest và bản config cũ; pin bộ phiên bản Pangolin/Gerbil/Newt/Traefik/Badger tương thích sau kiểm tra release tại thời điểm triển khai. Không dùng `latest` cho cutover.
- Không ghi secrets, token, SQL dump, router binary backup vào Git hoặc đầu ra task. Backup nhạy cảm phải mã hóa và có bản ngoài VPS.
- Preserve các thay đổi có sẵn ở `docs/MAIN.md`, `docs/LOG.md`, `edge-registrar/`; không stage/commit chúng như sản phẩm của migration.
- Chỉ public các service hiện public; không biến toàn bộ LAN, database, admin API thành public. BDS là ngoại lệ Cloudflare Tunnel có chủ ý.
- Không cài Headscale/RustDesk trùng hoặc khởi tạo database/identity mới nếu đã có bản chạy. BTH không được coi là thành công bằng cách thay bằng WireGuard thường.
- Pangolin P2P là tối ưu có kiểm chứng, không phải điều kiện để hứa service sẽ nhanh. Gerbil relay vẫn UDP; Rathole TCP giữ rollback tới cuối.

## 1. Bằng chứng và điều kiện chưa xác minh live

| Hạng mục | Bằng chứng repo | Hệ quả cho plan |
|---|---|---|
| VPS | `docs/MAIN.md`: Ubuntu 24.04, 4 vCPU, 8 GB RAM, 38 GB SSD | Đủ cơ sở thiết kế personal stack, chưa biết tải, disk trống, quota hay listener live |
| Public edge | `docs/LOG.md` v3.2: `gateway-traefik`, `/root/gateway/dynamic.yml` | Không sửa legacy nginx.conf; không dừng gateway để chạy installer Pangolin |
| Home edge | Docs v3.1 nói Orange Pi 10.10.0.2; v3.2 ghi Caddyfile ở Pi5 | Phải xác định container/task đang chạy, bind mount và máy sở hữu config thật trước deploy |
| BDS | `/root/batdongsan`, `bds-app`, `bds-prod-db`, PostgreSQL 16, host port 5434 | Có production data; app source/domain/uploads/jobs chưa inventory |
| Local | Mac 10.10.0.10 ARM64, `/Users/dungxbuif/production`; Pi5 10.10.0.5 | Build/test ARM64, không copy thẳng PGDATA từ VPS x86 sang Pi5 |
| Headscale/RustDesk | Đã ghi có `/root/headscale`, `/root/rustdesk` | Verify và sửa scoped thay vì mặc định cài mới |
| Router | `docs/MIKROTIK.md`: RB760iGS/MMIPS; snapshot `diagnostics/mikrotik-rest-snapshot.json`: hEX/MMIPS | Model giữa nguồn chưa đồng nhất nhưng cùng MMIPS, không đáp ứng BTH ARM/ARM64/TILE |
| UDP | Runbook ghi WireGuard từng ~5 Mbps | Dùng latency/error/reconnect thực tế làm gate cho Pangolin; chưa khẳng định mọi tuyến P2P đều bị bóp |
| Existing automation | `edge-registrar/` có sẵn và chưa tracked | Kiểm tra writer/cron trước cutover để tránh tự ghi đè SNI/Caddy |

BTH chỉ được triển khai khi đọc live `/system/resource/print` và `/system/routerboard/print` xác nhận thiết bị hỗ trợ. Nếu vẫn MMIPS, đánh dấu **blocked-hardware**, hoàn thành các nhánh khác; user chọn thiết bị ARM/ARM64 phù hợp hoặc đổi yêu cầu dự phòng. Không tự mua/thay router. Không đặt BTH là dependency bắt buộc của mọi nhánh; console VPS + SSH và Headscale/RustDesk đã verify thay thế điều kiện an toàn truy cập, không thay thế deliverable BTH.

BDS: mặc định đề xuất app Mac, DB Pi5 theo topology hiện có. Vì câu “move app” chưa xác định DB, chỉ nhánh chuyển app là chắc chắn thuộc yêu cầu; việc cutover DB phải chờ lựa chọn người dùng. Nếu DB ở lại VPS, dùng đường mã hóa có giới hạn truy cập và đánh giá latency, không mở rộng port 5434 public.

## 2. Thứ tự và cấu trúc file

Thứ tự: **inventory/backup → quản trị + RustDesk/Headscale → BTH nếu hỗ trợ → BDS local/Cloudflare → Pangolin canary → từng public resource → soak → retire Rathole**.

BDS và Pangolin có thể chuẩn bị artifact độc lập, nhưng không cutover trong cùng cửa sổ. BTH nếu cần đổi phần cứng phải là đợt khác, ở LAN.

Các file triển khai được tạo ở đợt execution, không phải cấu hình có sẵn:

| Đường dẫn trong repo | Trách nhiệm |
|---|---|
| `migration/access-platform/inventory.md` | Phiên bản/digest, port owner, network, host/config owner; không secrets |
| `migration/access-platform/routes.tsv` | Từng hostname/protocol/backend/auth/old-route/new-route và test cụ thể |
| `migration/access-platform/versions.lock` | Bộ phiên bản đã staging thành công |
| `migration/access-platform/pangolin/compose.yaml` | Compose riêng; port coexist và persistent volumes |
| `migration/access-platform/pangolin/config.yml` | Endpoint, domain, registration; secret lấy ngoài Git |
| `migration/access-platform/pangolin/traefik/` | Static/dynamic configuration theo release đã pin, TLS và trusted proxy |
| `migration/access-platform/newt/compose.yaml` | Connector trên network backend đúng, không publish app port mới |
| `migration/access-platform/bds/compose.yaml` | App local cô lập, image pin, network/volume, health check theo app thật |
| `migration/access-platform/bds/cloudflared.yaml` | Named tunnel và mapping domain; credentials ngoài Git; HTTP/2 |
| `migration/access-platform/bds/data-migration.md` | DB/storage/jobs manifest, freeze, restore verification, rollback sau ghi |
| `migration/access-platform/management.md` | Headscale/DERP/RustDesk IDs, endpoints, test và rollback không secrets |
| `migration/access-platform/bth.md` | Hardware gate, RouterOS changes tối thiểu, test ngoài LAN |
| `migration/access-platform/evidence.md` | Checkpoints, timestamp, test outcome và thời điểm dữ liệu đổi chủ |
| `migration/access-platform/rollback.md` | Patch đảo đúng từng cutover và địa chỉ/port old path đã thử |

Chỉ sửa `docs/MAIN.md`, `docs/LOG.md`, `docs/MAC.md`, `docs/MIKROTIK.md` ở cuối để ghi sự thật đã verify, không ghi kế hoạch như trạng thái live.

## 3. Task 0 — Inventory live và phục hồi được

**Files:** Create inventory.md, routes.tsv, versions.lock, evidence.md, rollback.md.
**Consumes:** Repo, SSH alias/config đã xác định và console nhà cung cấp.
**Produces:** G0: bảng service/port/domain đầy đủ và backup có thể khôi phục.

- [ ] Truy cập console VPS từ nhà cung cấp, mở SSH thứ hai từ một máy ngoài LAN; xác minh cả hai không đi qua Pangolin sẽ dựng.
- [ ] Read-only VPS: `uptime`, `free -h`, `df -h`, `df -i`, `ss -lntup`, `docker ps`, `docker stats --no-stream`. Qua shell local luôn dùng `rtk` hoặc `rtk proxy`; không dump toàn `docker inspect`/env vào transcript.
- [ ] Lấy riêng image/digest, mount source/destination, published ports, restart policy, container networks, Compose project và health. Chỉ đọc env keys; giá trị nhạy cảm chuyển trực tiếp vào secret storage.
- [ ] Xác định gateway network namespace; gateway trong container không thể gọi host loopback bằng `127.0.0.1`. Ghi địa chỉ reachable giữa gateway và future Gerbil/Traefik.
- [ ] Xác định Swarm service/task Caddy/Rathole, đường config thật và network reachability tới Pi5 portless/Mac. Không suy ra vị trí runtime từ tên file ở manager.
- [ ] Liệt kê DNS exact A/AAAA/CNAME, wildcard, proxied flag, TTL, root domain và AdGuard rewrites. routes.tsv chứa mỗi public route thực tế, bao gồm Headscale, PairDrop, BDS, API/webhook, storage/registry và TCP/UDP nếu có.
- [ ] Kiểm tra scheduler/CI/edge-registrar đang sửa route. Ghi cách tạm khóa đúng writer trong cửa sổ cutover và phục hồi; không dừng cron toàn máy.
- [ ] BDS: xác định repo/commit/image, domain, DATABASE_URL destination (redacted), schema/extensions, tổng data, upload directory/S3 buckets, worker/cron, auth callbacks, email/webhook integrations và migration-on-start.
- [ ] Backup gateway/Caddy/Rathole, Headscale DB+config+keys, RustDesk keys/config, BDS logical DB+roles cần thiết+uploads. Dùng snapshot nhất quán: SQLite backup API hoặc stop ngắn riêng dịch vụ; PostgreSQL logical dump/snapshot phù hợp, không copy DB đang ghi tùy tiện.
- [ ] Copy encrypted backup ra ngoài VPS, kiểm tra checksum và thử restore DB vào database cô lập. Không chạy restore lên production.
- [ ] Chụp baseline ngoài LAN: HTTP status/body marker/TLS, login, WebSocket/SSE, upload/download, SSH/Tailnet. Ghi thời gian phản hồi làm mốc.

**Gate G0:** Không có hostname/DB/job chưa xác định trong phạm vi chuyển; backups được mở/restore thử; console và SSH độc lập dùng được. Nếu thiếu, tiếp tục inventory, không deploy prod.

## 4. Task 1 — Headscale/DERP và RustDesk trước ingress

**Files:** management.md, evidence.md; sửa đúng Compose/config live đã map ở G0.
**Consumes:** Existing identities/keys, port ownership và backup G0.
**Produces:** G1: đường điều khiển ngoài LAN đã thử và không phụ thuộc home Caddy.

- [ ] Verify Headscale hiện hữu: version, users/nodes/routes, ACL/policy, UI đã có và cách bảo vệ. Giữ DB, server_url, keys để không cần enroll lại mọi máy.
- [ ] Giữ endpoint Headscale đi trực tiếp VPS qua route riêng. Không đặt toàn control API/DERP sau màn hình login Pangolin hoặc Basic Auth; chỉ bảo vệ UI quản trị ở hostname/path tách biệt đã test.
- [ ] Kiểm tra embedded DERP thực sự hoạt động, không chỉ enabled trong YAML; giữ DERP map dự phòng và xác minh client theo khả năng release.
- [ ] Rà `3478/udp` Headscale STUN vs Coturn: chỉ một owner trên mỗi IP:port. Nếu xung đột, chọn STUN port trống khác, cấu hình đúng DERP map và test client; không chiếm port của Coturn đang dùng.
- [ ] Trên Tailscale client ngoài LAN: `tailscale status`, `tailscale netcheck`, `tailscale ping` tới Pi5; kiểm tra SSH và một resource LAN. Với phiên bản hỗ trợ, `tailscale debug derp headscale` kiểm tra DERP. Dùng rule outbound UDP tạm trên máy test duy nhất để thử relay, có rollback tự động; không chặn UDP toàn nhà/VPS.
- [ ] Verify hbbs/hbbr tồn tại và key nhất quán; chỉ cài mới nếu thực sự chưa có. Giữ image hiện tại khi nó hoạt động, tách nâng cấp khỏi ingress.
- [ ] Cài/cấu hình client trên máy remote và máy ở nhà; ID server/key đúng. Mac cấp Screen Recording/Accessibility bằng UI người dùng; unattended access dùng mật khẩu mạnh.
- [ ] Thử RustDesk force-relay theo client/release, kiểm tra TCP hbbr và phiên 20–30 phút từ mạng ngoài; keyboard/mouse, reconnect, lock screen. Không suy ra forced relay từ việc thấy desktop.
- [ ] Chỉ expose port RustDesk cần dùng, không mở API Pro khi chạy OSS. WebSocket ports chỉ dùng nếu cần web client và được proxy/firewall phù hợp.

**Gate G1:** SSH/console độc lập, Tailnet và RustDesk usable từ ngoài LAN. Nếu remote desktop lỗi permission máy đích, sửa ở máy đích trước, không đổi gateway để chữa.
**Rollback:** Khôi phục riêng config đã thay; giữ danh tính và keys; không rollback DB Headscale qua image cũ sau schema upgrade không tương thích.

## 5. Task 2 — MikroTik BTH, gate phần cứng

**Files:** bth.md, evidence.md.
**Consumes:** Router live inventory; người dùng ở LAN để xác nhận/app setup khi cần.
**Produces:** G2-pass hoặc G2-blocked-hardware có bằng chứng, không “pass giả”.

- [ ] Chạy read-only `/system/resource/print` và `/system/routerboard/print`; ghi model, architecture, RouterOS.
- [ ] Nếu MMIPS như snapshot: dừng riêng nhánh BTH. Không factory reset, upgrade để thử, hoặc chạy BTH trên VPS rồi gọi là đường router dự phòng. User chọn hardware hỗ trợ trong đợt riêng.
- [ ] Nếu hardware hỗ trợ và RouterOS đáp ứng tài liệu: backup/export nhạy cảm ra nơi riêng; dùng Safe Mode cho sửa routing/firewall thủ công; có phiên WinBox LAN.
- [ ] Cấu hình BTH bằng app ở mạng nhà, cấp peer riêng cho máy test; chỉ quyền LAN cần thiết. Không đổi PPPoE, default route, DHCP/DNS hay firewall nền như một phần BTH.
- [ ] Tắt Wi-Fi máy test, dùng 4G/5G; verify tới router và một host LAN thực, rồi reconnect. Ghi direct/relay thực tế và tốc độ sử dụng được, không mặc định BTH chống UDP throttling.
- [ ] Từ client test ngắt đường VPS/Headscale (không shutdown VPS production); chứng minh BTH vẫn truy cập được. Thử ngắt BTH và xác nhận Internet LAN không bị ảnh hưởng.

**Rollback:** Thu hồi đúng peer/BTH config vừa thêm; kiểm tra route/firewall diff trước-sau. Không import toàn router backup từ xa làm rollback thường lệ.
**Giới hạn:** BTH là đường logic khác; cùng ISP/mất điện nhà vẫn là điểm lỗi chung. Không có WAN/UPS dự phòng được đưa thêm vào phạm vi này.

## 6. Task 3 — BDS local + Cloudflare Tunnel, rehearsal

**Files:** bds/compose.yaml, bds/cloudflared.yaml, bds/data-migration.md, evidence.md.
**Consumes:** BDS manifest G0 và lựa chọn phạm vi database.
**Produces:** G3: ứng dụng local chạy đúng trên bản dữ liệu test, tunnel TCP hoạt động.

- [ ] Đề xuất app project riêng `/Users/dungxbuif/production/bds/`; cloudflared cùng Docker network với app, target bằng service name. Không đổi Compose chính đang chạy ứng dụng khác.
- [ ] Build từ đúng commit cho ARM64 và test dependency native; chỉ dùng amd64 emulation nếu rehearsal đạt. Không dùng `network_mode: host` để giả định khả năng truy cập macOS native.
- [ ] Nếu DB local được chọn: tạo project/volume/database BDS riêng trên Pi5, giữ major PostgreSQL 16 trong đợt này, cài extension cần thiết. Không restore đè shared production database và không đổi PgBouncer của các app khác.
- [ ] Restore một logical dump vào target cô lập; kiểm tra schema, row counts bảng nghiệp vụ, sequences, grants, extension, timezone/collation và truy vấn tiêu biểu. Không copy PGDATA x86 sang ARM.
- [ ] Mirror uploads/media, đo thời gian dump/transfer/restore và final file sync. Disable jobs, scheduler, email, webhook outbound ở môi trường test; không để rehearsal phát side effect production.
- [ ] Tạo named Cloudflare Tunnel riêng cho BDS; ép `http2` do lịch sử UDP. Allow outbound TCP 7844 tới endpoint Cloudflare cần thiết; đây không phải giả định tunnel TCP 443.
- [ ] Tạo hostname canary riêng dưới zone đã kiểm soát, được kiểm tra không trùng DNS hiện có. Bảo vệ canary; không đặt Access login mới lên public app production nếu không được yêu cầu.
- [ ] Verify trang list/detail/search, đăng nhập/logout/session, upload/render image, một transaction create-update-delete trên dữ liệu test; test callback và các URL absolute theo public host production.
- [ ] Test app restart và cloudflared restart từng cái; xác nhận Mac không sleep và container runtime có cách khởi động sau reboot phù hợp FileVault/user login. Nếu không tự phục hồi, ghi điều kiện vận hành trước cutover.
- [ ] Với nhánh DB giữ VPS: xác minh private encrypted DB path và reconnect sau tunnel restart. Không dùng canary ghi vào production DB chỉ để test; dùng DB test riêng.

**Gate G3:** Canary qua HTTP/2, nghiệp vụ đạt, restore drill đạt nếu chuyển DB. Ước lượng downtime = freeze + final dump/sync + transfer + restore/verify + mở ghi; lấy số đo rehearsal cộng 50% dự phòng, không tự hứa 5 phút.

## 7. Task 4 — BDS production cutover, một nguồn ghi

**Files:** bds/data-migration.md, rollback.md, evidence.md; DNS chỉ đúng record BDS.
**Consumes:** G3, cửa sổ bảo trì thống nhất khi execution.
**Produces:** G4: BDS local qua Cloudflare, một DB authoritative.

- [ ] Ghi record DNS cũ đầy đủ A/AAAA/CNAME/proxy/TTL; giảm TTL trước cửa sổ nếu loại record cho phép. Không thay wildcard cả zone.
- [ ] Đóng mutation trên app cũ và mới; dừng toàn bộ writer đã inventory: worker/cron/webhook consumer/external DB writer. Request đang chạy phải drain xong; kiểm tra session/transaction ghi còn lại trước snapshot cuối.
- [ ] Nếu DB chuyển local: final dump và final upload sync, checksum, restore vào target mới; chạy verify giống rehearsal. App cũ không còn quyền ghi vào DB cũ; giữ bản nguồn read-only làm recovery.
- [ ] Nếu chỉ chuyển app: giữ DB authoritative cũ, không dump/restore cutover; chỉ một bộ worker/scheduler active và cùng schema tương thích.
- [ ] Bật app local với cấu hình production nhưng giữ maintenance cho người dùng; chạy smoke đọc bằng hostname thật/đường test kiểm soát. Không chạy automatic schema migration ngoài kế hoạch.
- [ ] Trỏ DNS exact BDS tới Cloudflare named tunnel; kiểm tra từ resolver ngoài và LAN. Sửa riêng AdGuard rewrite BDS nếu wildcard LAN đang đưa domain về Caddy cũ: exact DNS/route exception phải có rollback riêng.
- [ ] Old HTTP ingress BDS phải trả maintenance hoặc forward có kiểm soát về cùng app/DB mới trong thời gian cache DNS còn tồn tại. Tuyệt đối không mở lại app cũ dùng DB cũ cho traffic tồn đọng.
- [ ] Mở ghi trên target duy nhất; bật một bộ worker, xử lý backlog với idempotency. Ghi timestamp first production write ở target, kiểm tra một transaction nghiệp vụ và upload.
- [ ] Quan sát tối thiểu 24 giờ trước cutover public gateway khác; giữ old app image/config/source DB và backup tối thiểu 7 ngày, theo dung lượng thực tế. Không giữ dump lớn chỉ trên SSD 38 GB.

**Rollback trước first-write:** Đóng target, đưa DNS/route cũ về, mở writer cũ sau xác nhận source vẫn authoritative.
**Rollback sau first-write nếu DB đã chuyển:** Không đổi DNS về DB cũ. Ưu tiên sửa/rollback app image dùng cùng DB mới; nếu bắt buộc trả DB về VPS: maintenance, dừng target writers, lấy snapshot/dump mới từ local + đồng bộ uploads ngược, restore vào DB mới riêng trên VPS, verify rồi chuyển writers. RPO mục tiêu 0; cần thêm downtime. Nếu mất truy cập hoàn toàn data mới, không hứa rollback RPO 0 từ backup cũ.
**Rollback app-only:** Chuyển app về image cũ dùng cùng DB authoritative, sau kiểm tra tương thích schema; chỉ một bộ workers.

## 8. Task 5 — Pangolin coexist, chưa đổi public service

**Files:** pangolin/, newt/, versions.lock, routes.tsv, rollback.md.
**Consumes:** G0/G1, BDS ổn định G4; G2 có trạng thái rõ.
**Produces:** G5: Pangolin auth/canary/Newt hoạt động cạnh Rathole.

- [ ] Dùng manual Compose theo release đã pin; không chạy quick installer chiếm 80/443 trên VPS live. Backup trước mọi schema migration.
- [ ] Giữ `gateway-traefik` sở hữu public TCP 80/443. Pangolin Traefik/Gerbil chạy project riêng, listener nội bộ 80/443 trên namespace của nó, không publish trùng host. Gateway tới Gerbil bằng network Docker chung cô lập hoặc host mapping giới hạn reachable từ gateway đã test; không dùng loopback sai namespace.
- [ ] Chọn hostname dashboard canary `pangolin.dungxbuif.com` chỉ sau kiểm tra chưa được dùng. Gateway thêm exact SNI TLS passthrough tới Pangolin cho hostname này; redirect/callback vẫn dùng external HTTPS 443. Không catch-all lấy mất Headscale/BDS/legacy routes.
- [ ] TLS: DNS-01 bằng Cloudflare token zone-scoped ngoài Git để tránh xung đột ACME HTTP-01 trong coexist. Verify cert, chain, renewal config, redirect không lộ port nội bộ. Không copy insecure upstream verification mặc định sang production nếu có thể verify đúng CA/SNI.
- [ ] Public UDP 51820 và 21820 cho Gerbil chỉ sau kiểm tra listener. Nếu bị chiếm, chọn port được release hỗ trợ và cấu hình thống nhất; không tự tắt VPN khác. Kiểm tra subnet Pangolin không đụng LAN/Swarm/Docker/Tailnet 100.64.0.0/10.
- [ ] Bootstrap admin qua đường có giới hạn truy cập trước khi public dashboard; tắt signup không mời; bật MFA và lưu recovery ngoài VPS. Không đưa secret/key trong repo.
- [ ] Deploy Newt trên host/network có thể tới backend. Ưu tiên network overlay hiện hữu cho portless Pi5 và LAN tới Mac; xác minh Docker DNS/reachability ngay trong connector namespace. Đánh giá LAN discovery nếu Newt trong container, không hứa tự thấy host IP.
- [ ] Canary web read-only riêng có auth; canary private SSH/DB test với grant hẹp. Guest chưa login bị chặn, đúng user truy cập, user không quyền bị chặn, revoke có hiệu lực theo semantics release đã kiểm tra.
- [ ] Xác minh Newt control WebSocket, site tunnel, reconnect sau restart một connector. Test qua 4G và Wi-Fi ngoài; ghi direct/relay, latency, error và transfer đủ đại diện nhu cầu hiện tại.
- [ ] Kiểm tra PROXY protocol/X-Forwarded headers: gateway hiện có có thể gửi PROXY tới Caddy. Không gửi PROXY vào listener không hỗ trợ. Chỉ tin header từ proxy xác định; xác nhận IP/log và HTTP Host/TLS SNI trước dùng ACL IP.

**Gate G5:** 30 phút canary không có lỗi transport chưa giải thích; login/private grant/reconnect đạt; không route cũ nào hồi quy. Ngưỡng đề xuất: 0 lỗi trong 20 request nhẹ liên tiếp, latency p95 không quá 2x baseline hoặc mức người dùng chấp nhận, SSH usable. Throughput không bắt buộc bằng Rathole nhưng phải ghi số đo. Không dùng public DNS test nhầm đường LAN.
**Rollback:** Xóa đúng route canary mới, dừng project Pangolin/Newt mới; gateway/Rathole/Headscale cũ không đổi. Giữ artifact/key để điều tra.

## 9. Task 6 — Migrate từng public resource sang Pangolin

**Files:** routes.tsv, evidence.md, rollback.md; gateway dynamic config và Pangolin resource declarations.
**Consumes:** G5, baseline G0, danh sách đầy đủ service.
**Produces:** G6: mọi public resource trong phạm vi qua Pangolin, BDS qua Cloudflare.

- [ ] Phân loại route: web admin cần Pangolin auth; web public giữ public; API/webhook/Registry/S3/CouchDB giữ auth ứng dụng và machine compatibility. Không bật login redirect đại trà lên endpoint SDK.
- [ ] Target direct service từ Newt nếu reachable; nếu giữ Caddy trung gian phải khai báo Host/SNI và HTTPS verification đúng, tránh HTTP→HTTPS redirect loop, giữ rewrite/CORS/upload semantics hiện có.
- [ ] Mỗi hostname tạo resource và test trước bằng canary/override DNS kiểm soát. Dùng production hostname với TLS đúng khi thử callback/cookie; không suy kết quả từ canary hostname cho toàn auth flow.
- [ ] Chuẩn bị patch đảo exact SNI/router config của hostname. Cutover bằng gateway watched dynamic config: exact SNI sang Pangolin, ưu tiên rõ hơn legacy router, bỏ hostname tương ứng khỏi Rathole whitelist trong cùng config file update atomic.
- [ ] Không restart gateway cho cập nhật file provider. Vì hai control systems không transaction chung, tạo backend/resource sẵn trước, rồi mới đổi gateway; rollback gateway trước khi gỡ resource.
- [ ] Test ngoài LAN ngay: unauth/authorized/denied, status+body, TLS, application login và action nghiệp vụ. Nếu lỗi critical, rollback hostname đó trong mục tiêu 5 phút, không chuyển hostname kế.
- [ ] Thứ tự: dashboard/tool ít rủi ro → web thông thường → WebSocket/SSE/OCR → API/webhook → CouchDB/Registry/S3 cuối. Headscale control/DERP và RustDesk transport là ngoại lệ hạ tầng, không bọc thêm web auth.
- [ ] Tests riêng: Registry login/push/pull image nhỏ; S3 signed PUT/GET và multipart nhỏ; CouchDB replication hai chiều trên DB test; webhook signature+delivery không duplicate; WebSocket/SSE duy trì và reconnect; PairDrop browser connectivity/transfer nếu thuộc public routes.
- [ ] Test LAN với AdGuard split DNS: local bypass Pangolin phải được ghi rõ và giữ auth ứng dụng; không tuyên bố Pangolin auth bảo vệ cả LAN khi Caddy vẫn direct. Service bắt buộc auth cả LAN phải có route/policy riêng đã test.
- [ ] Chuyển từng route có soak 15–30 phút; nhóm storage/integration qua một chu kỳ sử dụng thật trước nhóm tiếp theo. Chỉ expose raw TCP/UDP đã có yêu cầu; DB tương lai dùng private resource.

**Gate G6:** routes.tsv không còn service public thuộc phạm vi chưa chuyển; tests không chỉ HTTP 200; old endpoints đã đóng bypass auth public. Gateway chỉ là L4 front door, Pangolin chịu resource/auth/TLS public đã chuyển.

## 10. Task 7 — Soak, retire Rathole và handoff

**Files:** evidence.md, rollback.md; cập nhật docs hiện hữu bằng patch nhỏ preserve edits.
**Consumes:** G4/G6 ổn định.
**Produces:** G7: vận hành chính trên platform mới, rollback còn dùng được.

- [ ] Quan sát 48–72 giờ gồm giờ cao điểm; theo dõi endpoint lỗi, reconnect Newt, session auth, CPU/RAM/disk/log, public service latency. Đây là kế hoạch quan sát, không tự tạo automation khi chưa được yêu cầu.
- [ ] Verify lại RustDesk relay và Headscale/DERP qua cùng public 443/ports sau toàn bộ route changes. Verify BTH nếu G2-pass; nếu blocked giữ trạng thái chưa hoàn thành, không ghi “done toàn bộ”.
- [ ] Restart tuần tự Newt, Pangolin components theo phụ thuộc trong cửa sổ bảo trì; xác minh recovery và identities. Reboot host không bắt buộc cùng ngày, lên lịch riêng nếu cần người ở LAN unlock Mac.
- [ ] Kiểm tra không còn session/service phụ thuộc Rathole, đặc biệt route hiếm, SSH/DB mapping và automation. Disable restart/stop đúng Rathole client/server; không remove volumes hoặc token ngay.
- [ ] Đóng public TCP 7000 sau stop và kiểm tra lại các đường mới. Giữ config/images/keys tối thiểu 7 ngày; rollback documented gồm mở lại firewall trước start tunnel và restore exact gateway rules.
- [ ] Không gỡ Caddy/AdGuard/Swarm chỉ vì public đã chuyển: LAN và backend reachability còn phụ thuộc. Không gỡ gateway-traefik chỉ để bớt một container: nó giữ Headscale route và L4 coexist. Nếu muốn Pangolin Traefik sở hữu trực tiếp 80/443, đó là đợt cutover cổng riêng, staging đủ Headscale/DERP/routes rồi mới chuyển.
- [ ] Sau retention và xác nhận dữ liệu BDS local ổn, đề xuất riêng việc xóa old deployment/DB. Dừng service không đồng nghĩa cho phép xóa production volume.
- [ ] Cập nhật topology, route owner, secret storage location (không secret), backup/restore và trạng thái BTH đúng sự thật; commit chỉ file của migration.

## 11. Ma trận dừng và rollback

| Sự cố | Dừng ở đâu | Hành động |
|---|---|---|
| Console/SSH độc lập không dùng được | Trước mọi thay đổi edge | Khôi phục đường quản trị, chưa cutover |
| BTH không hỗ trợ MMIPS | Riêng Task 2 | blocked-hardware, không sửa router; không tự đổi sang VPN khác |
| BDS restore drill lỗi hoặc thiếu upload/job | Task 3 | Giữ app/DB cũ authoritative |
| BDS lỗi trước ghi target | Task 4 | Old route + source writer duy nhất |
| BDS lỗi sau ghi target | Task 4 | Maintenance; giữ DB mới hoặc reverse-migrate có kiểm chứng |
| Pangolin UDP không ổn cho app nhẹ | Task 5 | Giữ Rathole; không áp dụng “P2P sau này” làm lý do vượt gate |
| Login loop, SDK bị redirect, sai SNI/IP | Từng hostname Task 6 | Đảo gateway route; không đổi DNS wildcard |
| Headscale/RustDesk mất truy cập khi đổi route | Task 6/7 | Dùng console/SSH, khôi phục route hạ tầng độc lập |
| Disk VPS không đủ giữ source và backup | G0/Task 4 | Đưa encrypted backup ra offsite; không xóa source để nhường chỗ |

## 12. Tiêu chí nghiệm thu cuối

- [ ] BDS domain đúng app local qua Cloudflare HTTP/2; một DB authoritative; job/upload/auth hoạt động; restore/rollback có bằng chứng.
- [ ] Public resource ngoài BDS qua Pangolin, chính sách auth đúng loại client; không còn public bypass qua old Rathole.
- [ ] Headscale giữ node identity/UI auth; DERP và private LAN verified từ ngoài nhà.
- [ ] RustDesk remote được và relay TCP đã chứng minh, không chỉ cài container.
- [ ] BTH verified ngoài LAN trên hardware hỗ trợ **hoặc ghi blocked-hardware rõ, task này chưa complete**.
- [ ] Rathole retired sau soak, có rollback; không mất LAN DNS/TLS; không mất dữ liệu production.

## 13. Nguồn và self-review

- Local: `docs/MAIN.md`, `docs/LOG.md`, `docs/MAC.md`, `docs/MIKROTIK.md`, trường hardware trong `diagnostics/mikrotik-rest-snapshot.json`.
- Pangolin manual layout/ports: https://docs.pangolin.net/self-host/manual/docker-compose
- Pangolin NAT/P2P/relay: https://docs.pangolin.net/manage/clients/nat-traversal
- Pangolin auth/resource types: https://docs.pangolin.net/manage/resources/understanding-resources
- Cloudflare HTTP/2/port 7844: https://developers.cloudflare.com/tunnel/advanced/run-parameters/ và https://developers.cloudflare.com/tunnel/configuration/
- Headscale DERP/UI: https://headscale.net/stable/ref/derp/ và https://headscale.net/stable/ref/integration/web-ui/
- RustDesk: https://rustdesk.com/docs/en/self-host/rustdesk-server-oss/install/
- BTH hardware: https://manual.mikrotik.com/docs/network-management/cloud/back-to-home/

Self-review: bốn yêu cầu đều có task/gate; BTH không được bỏ qua âm thầm; app-only/DB-move rollback phân biệt trước/sau ghi; 80/443 coexist và proxy namespace được kiểm tra; Headscale không bị auth loop; Cloudflare TCP đúng port; dirty worktree preserved. Đường dẫn deployment mới là đề xuất, đường live chưa biết phải được G0 xác định trước render configuration. Không đưa lệnh mutation có giá trị suy đoán vào runbook để tránh copy-paste nhầm production.
