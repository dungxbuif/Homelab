---
type: Reference
title: "Code Index: example-service-container"
description: "Aggregated code index for example-service-container folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: example-service-container

> This index aggregates code files in the [[example-service-container/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [docker-compose.yml](./docker-compose.yml)

```yaml
version: '3.8'

services:
   whiteboard:
      image: dungxbuif/be-whiteboard:latest
      container_name: whiteboard
      restart: always
      labels:
         - 'traefik.enable=true'
         - 'traefik.http.routers.whiteboard.rule=Host(`api-whiteboard.dungxbuif.com`)'
         - 'traefik.http.routers.whiteboard.entrypoints=websecure'
         - 'traefik.http.services.whiteboard.loadbalancer.server.port=80'
      networks:
         - traefik

networks:
   traefik:
      external: true

```

---
