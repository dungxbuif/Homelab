---
type: Reference
title: "Code Index: gitlab"
description: "Aggregated code index for gitlab folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: gitlab

> This index aggregates code files in the [[gitlab/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [docker-compose.yml](./docker-compose.yml)

```yaml
services:
   gitlab:
      image: 'gitlab/gitlab-ce:latest'
      container_name: 'gitlab'
      restart: always
      volumes:
         - ./config:/etc/gitlab
         - ./logs:/var/log/gitlab
         - ./data:/var/opt/gitlab
      shm_size: '256m'
      networks:
         gitlab-network:
           aliases:
             - registry-gitlab.dungxbuif.com

   tunnel:
      image: cloudflare/cloudflared:latest
      container_name: 'cloudflare-tunnel'
      restart: always
      command: tunnel run --token <tokken>
      depends_on:
         - gitlab
      networks:
         - gitlab-network

networks:
   gitlab-network:
      driver: bridge

```

---
