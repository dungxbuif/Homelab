# RelayHub and OCR release

RelayHub source: `/Users/dungxbuif/workspace/RelayHub`, commit `eee9e7c`.
Build context on VM100: `/opt/apps/relayhub/releases/eee9e7c`.
Image: `homelab/relayhub:prod-eee9e7c`.
Rollback image: `homelab/relayhub:prod-20260920-152029`.

Use the existing prod compose and logging override plus `compose.release.yml`.
Update only API and worker, without recreating NATS/Redis or resetting data.
Verify container health, root docs, SDK download hashes and readiness afterward.
Keep release override in subsequent compose invocations to avoid image regression.

Changes: session/CSRF SDK admin auth; queue SDK lease-loss cancellation; refreshed
human/agent docs and SDK downloads. Backend race, PostgreSQL integration, SDK and
admin tests passed. Production OCR/native remains unchanged during RelayHub release.

OCR migration is proxy-only. Native Mac application, local listener and tunnel must
not be rebuilt or restarted. Implementation and acceptance gates are tracked in
mac-ocr/docs/RELAYHUB_INTEGRATION.md. Production tests use synthetic documents only.

Status: RelayHub deployed on VM100; API and worker healthy. Public readiness,
root docs and agent docs returned 200. Both SDK download hashes match the release.
OCR cutover and production smoke verification are complete; benchmark results and
the remaining burst-latency limitation are recorded below.

Follow-up: Pi SSH restored. Service spec privately snapshotted; PostgreSQL `macocr`
custom-format backup saved outside git (104643 bytes). Pre-migration inventory:
975 completed, 14 failed, no queued/processing documents; legacy batches absent.
Rollout will mount secret `ocr_relayhub_credentials_20260920` with target
`ocr_relayhub_credentials`, uid 100/gid 101/mode 0400 (verified image user).
Use the existing stop-first update policy to avoid concurrent direct/queue workers.

Rollout completed: `macocr-proxy` converged on VM100 with image `relay-31b3013`;
transport startup and public health/docs returned success. After operator memory
increase, synthetic PDF completed with exact text `OCR RELAY SMOKE 2026`, and image
completed; both used one native attempt and were ACKed by RelayHub afterward.

User-requested latency benchmark: current production image/config only, no tuning.
Use bounded smoke-account traffic: four sequential requests (two image, two PDF)
then eight concurrent submissions (four each). Report submit latency and observed
end-to-end completion, with server timestamps to separate queue and native time.
Polling adds observation overhead; small sample p95 is descriptive, not an SLA.
Temporarily raise only smoke account/key test limits; remove its data afterward.

Comparison plan: temporarily restore the pre-migration image
`homelab/macocr-proxy:vm100-20260910` and direct scheduler, run the same four
sequential plus eight concurrent workload with the same fixtures and 500 ms polling,
then restore `homelab/macocr-proxy:relay-31b3013`. Keep routing, networks, database,
Redis, native endpoint and resource limits unchanged. Record both samples; this is a
small operational comparison, not a statistically rigorous capacity benchmark.

Comparison result (same fixtures, 500 ms client polling, 4 sequential + burst 8):

| Transport/image | Sequential p50 / p95 | Burst-8 p50 / p95 / max | Success |
|---|---:|---:|---:|
| Direct `vm100-20260910` | 1.173s / 1.741s | 1.895s / 2.940s / 2.940s | 12/12 |
| RelayHub `relay-31b3013` | 2.208s / 2.889s | 8.142s / 16.514s / 16.514s | 12/12 |

Submit latency is similar (old burst p50/p95 209/302 ms; RelayHub 244/279 ms).
Native OCR remains fast after dispatch (RelayHub sample 217-461 ms). The RelayHub
tail is dominated by serialized queue consumption (`Concurrency: 1`) plus the
consumer's two-second terminal-state polling cadence: burst claims advanced by
roughly two seconds each. Correctness stayed intact: every sample completed in one
document attempt and one queue attempt, and PDF text matched exactly.

Conclusion: current RelayHub transport is durable but its initial conservative
consumer settings materially regress burst latency. Before treating it as the
preferred production path, make concurrency configurable and replace/coarsen the
terminal polling handoff (notification or shorter adaptive polling), then rerun a
larger warm benchmark.

## Final disposition

OCR production is finalized on direct scheduling with image
`homelab/macocr-proxy:direct-admin-6a4924a`. This image is built from OCR `master`
commit `6a4924a`: the pre-RelayHub direct scheduler plus the restored administrator
“My API Keys” navigation. Public health and Admin assets return 200; the deployed
bundle contains API-key create/manage controls. `OCR_TRANSPORT`, the RelayHub
credential-file variable and the Swarm secret attachment are absent.

Experimental RelayHub OCR code remains on branch
`codex/ocr-relayhub-transport` at `65d0910`; it is not on OCR `master` and is not
active in production. The additive outbox table is retained for a future controlled
trial. Benchmark data was removed from PostgreSQL, Redis and object storage.

RelayHub itself remains a production service and is independent from this OCR
transport decision. Its first production release is documented as `v1.0.0` in
RelayHub commit `c1c51ca`; deployed API/worker image remains
`homelab/relayhub:prod-eee9e7c`.

## OCR candidate

Commit `31b3013` in `/Users/dungxbuif/workspace/mac-ocr` contains the reviewed proxy-only
integration. Image build on VM100: `homelab/macocr-proxy:relay-31b3013`, context
`/opt/apps/macocr-proxy/releases/31b3013`, exported from the commit, not the dirty
working tree. Native and unrelated scan/admin changes are not included.

Candidate image build completed successfully on VM100. Image manifest list digest:
`sha256:342c51e64c4388c3b120e4999c4d3e689a599cad9a1e013cd462749f25442b68`.
It has not replaced the running OCR service. The earlier `relay-3b45756` candidate
is superseded and must not be deployed.

Full proxy race tests passed against the exact staged release source, including
new PostgreSQL outbox and 16-way targeted-claim tests on a disposable local DB.
Tests cover terminal-only ACK, existing attempts, wrong publishers and native
offline/busy. Human docs and agent processing contract build successfully.

Review fixes: transactional claim/read, delayed retry for PDFs that cannot fit,
startup event-filter validation. Independent re-review found no remaining blocker.
Test-only follow-up `65d0910` checks the actual expired owner, repeated five times
against PostgreSQL with race detection. Full heartbeat-loss/redelivery/late-callback
production acceptance is still pending; component tests are not a substitute.

Read-only production checks passed: existing OCR container can reach RelayHub
readiness; signed consumer authentication succeeds; `ocr-jobs` is enabled, not
paused or draining, max visibility 300 seconds and max batch size one.

Build dependency warning: Docusaurus npm audit reports 30 findings (5 high,
24 moderate, 1 low). These are build-stage dependencies, not shipped Node runtime;
triage remains separate work. No automatic breaking dependency upgrade was applied.

The running Swarm service is `macocr-proxy`, old image
`homelab/macocr-proxy:vm100-20260910`. VM100 is a worker, not a manager.
The Pi manager's 1Password SSH signing currently fails. Do not bypass Swarm by
starting a standalone replacement or changing node membership.

Pending rollout gates:

1. Restore Pi SSH signing; inspect and privately snapshot the service spec.
2. Back up OCR DB before startup migration (new outbox table/index only).
3. Create a versioned Docker secret from the protected local credential JSON;
   mount at `/run/secrets/ocr_relayhub_credentials`, readable by the service user.
4. Update the existing service image plus `OCR_TRANSPORT=relayhub` and
   `RELAYHUB_CREDENTIALS_FILE=/run/secrets/ocr_relayhub_credentials`. Keep placement,
   networks, labels, limits, native URL and all other credentials unchanged.
5. Verify readiness and transport startup, then submit synthetic image/PDF through
   the public API. Verify native callback, durable completion and queue ACK.
6. Remove only recorded smoke data. Rollback to previous image and direct transport
   if verification fails. Do not remove real apps, users, documents or queue data.

Native is reachable through the existing tunnel but currently reports
`effectiveLimit=0`, `state=busy`, `resourceReason=memory-safety-reserve`.
Full OCR acceptance requires capacity recovery. No native process or LLM has been
restarted, rebuilt or reconfigured as part of this proxy rollout.
