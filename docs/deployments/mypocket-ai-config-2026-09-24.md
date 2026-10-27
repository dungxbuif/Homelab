# MyPocket AI provider configuration sync (2026-09-24)

After OCR authentication and model-provider failures, the MyPocket production
AI configuration was aligned with the working local development configuration.
The source values are in
`/home/dungxbuif/workspace/projects/MyPocket/backend/.env.local`; the homelab operational
copy is `local_vars.json` under `MYPOCKET_SECRETS` (gitignored). Keep both in
sync when rotating credentials. Never copy secret values into this document,
version control, or shell output.

Synced variables:

- `AI_BASE_URL`
- `AI_API_KEY`
- `AI_MODEL` (`DeepSeek-V4.1-Flash`)
- `OCR_API_URL`
- `OCR_API_KEY`

The API Swarm service was updated in place and currently runs
`AI_MODEL=DeepSeek-V4.1-Flash`; the provider model catalog includes that exact
ID. The API task is healthy, and `https://money.dungxbuif.com/api/v1/health`
returns HTTP 200 after the rolling update. The web service remains stopped by
the API-only deployment decision. A real receipt/model request is still an
owner-UAT gate; the rollout proves configuration and provider availability,
not business-quality inference.

Operational note: the OCR key was previously rejected with HTTP 401. After
syncing the local OCR key, an authenticated read against a deliberately
nonexistent document no longer returned 401 (provider returned 400). The prior
The previous LLM model returned HTTP 502 during the earlier deployment. The
current production model has been changed to `DeepSeek-V4.1-Flash`; successful
business inference remains an explicit UAT check.
