---
type: Reference
title: "Database Schema & Inventory"
description: "Specifications of schemas, user privileges, and structural details of Postgres/Redis instances"
timestamp: 2026-07-03T15:14:00Z
---

# 🗄️ Database Inventory (Centralized PostgreSQL with PgBouncer)

This document lists all active databases currently hosted on the Raspberry Pi 5 (`10.10.0.5`), managed through a centralized connection pooler (**PgBouncer**).

## 🔑 General Connection Details
*   **Entrypoint Host:** `10.10.0.5` (or `postgres.dungxbuif.com` for local routing)
*   **Entrypoint Port:** `5432` (Exposed by **PgBouncer** in `transaction` mode)
*   **Internal DB Server:** `postgres` (Port `5432` internal, hidden from host network)
*   **Default Username:** `admin`
*   **Password:** `Rcuh3jiV0qf8w/vLC5Vy9IbE`

---

## 📂 Active Database List

| Database Name | Owner | Consumer Service | Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **`homelab`** | `admin` | System | Active | Default initialization database |
| **`n8n`** | `admin` | n8n Automation | Active | Stores n8n workflows, credentials, and execution logs |
| **`macocr`** | `admin` | MacOCR Platform | Active | Stores MacOCR users, API keys, document metadata & configs |
| **`whiteboard`** | `admin` | Whiteboard App | Planned | Proposed deployment on Kubernetes cluster |

---

## 🛠️ Management Guide
1.  **GUI Access:** Administer using pgAdmin at [https://pgadmin.dungxbuif.com](https://pgadmin.dungxbuif.com).
2.  **Create a New Database:**
    ```sql
    CREATE DATABASE <new_db_name> OWNER admin;
    ```
3.  **Manual Backup:**
    ```bash
    ssh pi "docker exec postgres pg_dump -U admin -d <db_name> > backup.sql"
    ```