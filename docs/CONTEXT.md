---
type: Reference
title: "Network Diagnostics Context"
description: "Retired diagnostic trace; points to current network references"
timestamp: 2026-10-31T12:00:00+07:00
---

# Network Diagnostics Context

This file used to hold a 2026-06 network speed/DNS trace and the retired
Kubernetes bootstrap log. None of it describes the current lab; it remains in
git history.

Current network facts:

- Topology, addresses and ingress: [MAIN.md](./MAIN.md), [STACK.md](./STACK.md).
- Router configuration: [MIKROTIK.md](./MIKROTIK.md).
- Still-relevant lessons from the old trace: ISP throttles high-volume UDP
  (why public ingress uses TCP Rathole); MikroTik `pppoe-out1` MTU 1492
  (unverified current).

For a new diagnostic session, record results in a dated note and update
STACK/STATUS with anything that changes current state.
