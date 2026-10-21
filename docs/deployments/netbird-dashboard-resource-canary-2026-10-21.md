# NetBird dashboard resource canary

Date: 2026-10-21

The stateless Swarm service `netbird_netbird-dashboard` was capped without
changing its image, networks, routes, or control-plane configuration:

```text
CPU:    0.50 vCPU
Memory: 512 MiB
Order:  start-first
```

The Swarm update completed successfully and the public dashboard
`https://netbird.dungxbuif.com/` returned HTTP 200. The NetBird server was not
changed because it owns the control-plane bind configuration and persistent
volume; it remains a separate measurement task.
