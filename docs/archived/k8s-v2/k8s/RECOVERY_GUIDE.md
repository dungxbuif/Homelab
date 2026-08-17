---
type: Playbook
title: "Workload & Data Recovery Guide"
description: "Step-by-step instructions on recovering stateless and stateful services during outages or hardware failovers"
timestamp: 2026-07-03T15:14:00Z
---

# 🆘 System Recovery Guide

This document details the step-by-step procedures to restore system configurations and database backups from Google Drive in the event of hardware failures, storage drive corruption, or accidental deletions.

## 1. Restore Database (PostgreSQL)

If a database schema is corrupted or needs to be rolled back to a previous state:

1.  **Retrieve Backup File:** Navigate to the `server-backups/db` folder on your remote Google Drive storage and download the latest SQL snapshot archive: `postgres_all_YYYYMMDD.sql.zip`.
2.  **Decompress:** Extract the zip file: `unzip postgres_all_YYYYMMDD.sql.zip`.
3.  **Restore to PostgreSQL Container:**
    ```bash
    # Copy the raw SQL script into the active postgres container volume
    docker cp postgres_all_YYYYMMDD.sql postgres:/tmp/restore.sql
    
    # Run the database restore tool (Warning: this will overwrite existing target tables/schemas)
    docker exec -it postgres psql -U admin -f /tmp/restore.sql postgres
    ```

## 2. Restore Gateway Infrastructure Services (Caddy, n8n, RustFS, etc.)

To recover application data or configuration files from a historical backup:

1.  **Retrieve Backup File:** Navigate to `server-backups/files` on Google Drive and download the target service snapshot (e.g., `n8n_YYYYMMDD.zip`).
2.  **Clear Corrupted Data:** Wipe the existing target directory (Warning: execute carefully!):
    ```bash
    rm -rf /ssd-data/infra/n8n/n8n_storage/*
    ```
3.  **Extract & Copy Files:**
    ```bash
    unzip n8n_YYYYMMDD.zip -d /tmp/restore_n8n
    cp -r /tmp/restore_n8n/n8n_storage/* /ssd-data/infra/n8n/n8n_storage/
    ```
4.  **Recreate & Restart Container Stack:**
    ```bash
    cd /ssd-data/infra
    docker compose up -d n8n
    ```

---

## 🔍 Verifying Backup Health

On the Raspberry Pi gateway host, verify backup pipeline logs periodically via `/var/log/backup.log`. The presence of the following tag confirms successful synchronization:
`✅ Upload verified (Hash matched)`
This confirms that the daily snapshot has been successfully uploaded to Google Drive with matching file hashes.