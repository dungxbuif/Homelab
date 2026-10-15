# MyPocket AI provider configuration sync (2026-09-24)

After OCR authentication and model-provider failures, the MyPocket production
AI configuration was aligned with the working local development configuration.
The source values are in
`/Users/dungxbuif/workspace/MyPocket/backend/.env.local`; the homelab operational
copy is `local_vars.json` under `MYPOCKET_SECRETS` (gitignored). Keep both in
sync when rotating credentials. Never copy secret values into this document,
version control, or shell output.

Synced variables:

- `AI_BASE_URL`
- `AI_API_KEY`
- `AI_MODEL` (`DeepSeek-V4-Flash`)
- `OCR_API_URL`
- `OCR_API_KEY`

The API Swarm service was updated in place and converged on
`homelab/mypocket-api:4591b98a-tzdata-20260924`. The web service remains on
`homelab/mypocket-web:4591b98a-20260924`. The API task reported healthy, and
`https://money.dungxbuif.com/` and `/api/v1/health` returned HTTP 200 after the
update. No receipt/model request was issued as a deployment smoke test; owner
UAT is still needed to verify a real AI-entry workflow.

Operational note: the OCR key was previously rejected with HTTP 401. After
syncing the local OCR key, an authenticated read against a deliberately
nonexistent document no longer returned 401 (provider returned 400). The prior
LLM model returned HTTP 502; this update changes the configured provider/model,
but successful inference has not yet been verified.
