---
type: Reference
title: "Code Index: traefik"
description: "Aggregated code index for traefik folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: traefik

> This index aggregates code files in the [[traefik/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [docker-compose.yml](./docker-compose.yml)

```yaml
services:
   traefik:
      image: docker.io/library/traefik:v3.1.1
      container_name: traefik
      command:
         - '--log.level=DEBUG'
      ports:
         - 80:80
         - 443:443
         # -- (Optional) Enable Dashboard, don't do in production
         - 8080:8080
      volumes:
         - /run/docker.sock:/run/docker.sock:ro
         - ./treafik-ssl-cert:/ssl-certs
         - ./logs:/var/log/traefik
         - ./config/traefik.yaml:/etc/traefik/traefik.yaml:ro
         - ./config/conf/:/etc/traefik/conf/
         - ./config/certs/:/etc/traefik/certs/
      # -- (Optional) When using Cloudflare as Cert Resolver
      environment:
         # https://doc.traefik.io/traefik/https/acme/#dnschallenge
         - CF_DNS_API_TOKEN=<CLOUDFLARE_DNS_API_TOKEN>
      # -- (Optional) When using a custom network
      networks:
         - traefik
      restart: unless-stopped

networks:
   traefik:
      external: true

```

---
