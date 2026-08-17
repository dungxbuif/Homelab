---
type: Reference
title: "OmniScan Mezon Bot Deployment & Specification"
description: "Architecture, production environment variables, database schema, and operational runbook for OmniScan Bot on K8s"
timestamp: 2026-08-15T04:23:00Z
---

# 🤖 OmniScan Mezon Bot Specification & Operational Runbook

## 1. 🏗️ Architecture Overview

OmniScan is an intelligent document scanning & conversational QA bot on the Mezon platform:
* **Bot Runtime (K8s):** Go daemon connecting via WebSocket to `gw.mezon.ai:443`, listening for channel messages and attachments.
* **Database (PostgreSQL Pi 5):** Central DB instance (`10.10.0.5:5432`), storing user daily scan quotas, OCR counts, and user configuration under the database `omniscan`.
* **Shared Redis (K8s Cluster):** Used for message deduplication and quota cache in namespace `redis` (`redis-service.redis.svc.cluster.local:6379`).
* **LLM Engine:** Multi-modal conversational reasoning via `https://llm.dungxbuif.com/v1` (Model: `qwen/qwen3.6-35b-a3b`).
* **OCR Service:** High-speed Apple Vision OCR Proxy via `https://ocr.dungxbuif.com/v1`.

```
[ Mezon Cloud Gateway ]
         │ (WebSocket WSS)
         ▼
[ omniscan-bot Deployment (1 Pod) ]
         ├──► [ PostgreSQL Pi 5: 10.10.0.5:5432/omniscan ]
         ├──► [ Shared Redis: redis-service.redis.svc.cluster.local:6379 ]
         ├──► [ LLM Gateway: https://llm.dungxbuif.com/v1 ]
         └──► [ MacOCR Proxy: https://ocr.dungxbuif.com ]
```

---

## 2. 🚀 Deployment Details

* **Namespace:** `omniscan`
* **Deployment:** `omniscan-bot` (Image: `registry.dungxbuif.com/omniscan:v1.0.0`, Replicas: `1` fixed)
* **Ingress / Domain:** **Không expose Domain** (Do là client daemon kết nối outbound tới Mezon Gateway).
* **Secret Configuration:** Managed via `omniscan-secrets` in namespace `omniscan`.

---

## 3. 🔑 Environment Variables & Secrets Reference

All sensitive credentials and endpoints are defined in `local_vars.json` under `OMNISCAN_SECRETS`:

| Secret Key | Reference in `local_vars.json` | Description |
| :--- | :--- | :--- |
| `MEZON_BOT_ID` | `OMNISCAN_SECRETS.MEZON_BOT_ID` | Mezon Bot Client ID |
| `MEZON_BOT_TOKEN` | `OMNISCAN_SECRETS.MEZON_BOT_TOKEN` | Mezon Bot Secret Token |
| `MEZON_HOST` | `gw.mezon.ai` | Mezon Gateway Host |
| `MEZON_PORT` | `443` | Mezon Gateway SSL Port |
| `OCR_PROXY_URL` | `OMNISCAN_SECRETS.OCR_PROXY_URL` | Production OCR API |
| `OCR_API_KEY` | `OMNISCAN_SECRETS.OCR_API_KEY` | Secret API Key for MacOCR |
| `DATABASE_URL` | `OMNISCAN_SECRETS.DATABASE_URL` | Central PostgreSQL |
| `REDIS_URL` | `OMNISCAN_SECRETS.REDIS_URL` | Cluster-shared Redis |
| `LLM_BASE_URL` | `OMNISCAN_SECRETS.LLM_BASE_URL` | LLM Gateway Endpoint |
| `LLM_API_KEY` | `OMNISCAN_SECRETS.LLM_API_KEY` | LM Studio / OpenAI API Key |
| `LLM_MODEL` | `OMNISCAN_SECRETS.LLM_MODEL` | Target LLM Model |
| `DAILY_SCAN_LIMIT`| `3` | Scans allowed per day |
| `DAILY_OCR_LIMIT` | `5` | OCR requests allowed per day |
| `SESSION_ASK_LIMIT`| `3` | QA followup questions per session |
| `SINGLE_HOST_LOCK`| `false` | PostgreSQL + Redis synchronization |
