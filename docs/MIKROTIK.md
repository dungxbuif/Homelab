---
type: Reference
title: "MikroTik hEX S Configuration Guide"
description: "Operational guidelines for PPPoE dialing, local network DHCP, WireGuard routing tables, and security hardening on MikroTik"
timestamp: 2026-07-03T15:14:00Z
---

# 🛜 MikroTik Router Configuration & Network Guide

This document outlines the detailed configuration, network architecture, and security hardening for the core router in the homelab.

---

## 🛠️ Hardware Specification & Role

*   **Model:** MikroTik hEX S (RB760iGS)
*   **Architecture:** mmips (MediaTek MT7621A, 2-Core / 4-Threads)
*   **Operating System:** RouterOS v7.18.2 (stable)
*   **Memory:** 256 MB RAM (typical free: ~196-206 MiB)
*   **Static LAN IP:** `<MIKROTIK_IP>`
*   **Core Role:** Primary Router & Local Gateway. Handles PPPoE dialing, NAT/firewall configurations, local subnet routing, and DHCP leases.

---

## 📐 Network Topography & Interfaces

```text
       Viettel ONT (Bridge Mode, VLAN 35)
                     |
                     | PPPoE WAN (103.82.x.x / Dynamic Public IP)
                     v
             +---------------+
             | MikroTik hEXS | <---> Netbird/Wireguard Admin clients (10.66.66.x)
             |  (<MIKROTIK_IP>)  |
             +-------+-------+
                     |
         +-----------+-----------+
         |                       |
         v                       v
Raspberry Pi 5 Gateway      Local LAN & Mesh WiFi
     (<PI_IP>)            (<LAN_SUBNET> subnet)
```

### 1. Port Mapping & Interface Status
*   **`ether1`**: WAN Interface (connected to the Viettel Bridge modem).
*   **`ether2` - `ether5`**: Configured as part of the primary LAN `bridge`. Hardware Offload is enabled on all ports to optimize performance.
*   **Link Speeds:** All active ports negotiate at `1Gbps` full-duplex.

### 2. PPPoE WAN Configuration
PPPoE dialing is managed via the `pppoe-out1` interface on top of `ether1`.
*   **MTU/MRU:** `1492`
*   **VLAN Tag:** `35` (required by Viettel ISP).

### 3. IP Allocation & DHCP Server
*   **Primary Subnet:** `<LAN_SUBNET>` (Gateway: `<MIKROTIK_IP>`).
*   **DHCP Server:** Managed by MikroTik. Hands out leases within the `10.10.0.x` range.
*   **DHCP DNS Server Options:** Advertises `<PI_IP>` (Raspberry Pi 5 AdGuard Home) as primary DNS, and `1.1.1.1` as secondary.
*   **Reserved Ranges:** Node IPs for Kubernetes control planes (`<K8S_VIP>-33`) are reserved and excluded from the dynamic DHCP pool.

---

## 🔒 Routing & Transit Forwarding (Admin VPN Access)

To access and manage the router (`<MIKROTIK_IP>`) and other LAN devices remotely through the WireGuard VPN subnet (`10.66.66.x`), the Raspberry Pi 5 (`<PI_IP>`) acts as a gateway proxy.

### Return Path Routing (NAT Masquerade)
Because the MikroTik router does not maintain a return route config for `10.66.66.x` traffic, packets would normally be discarded. To bypass this, the Pi 5 applies an **iptables NAT Masquerade** rule:
```bash
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
```
This masks the source IP of incoming VPN packets to look like they originate from the Pi 5's native IP (`<PI_IP>`), resolving the missing return path.

---

## 🛡️ Hardening & Security Actions

### 1. Management Services Status
MikroTik runs several administration services by default. The recommended baseline is:
*   **Telnet / FTP**: ❌ **Disabled** (high security risk).
*   **SSH / WWW / API / WinBox**: Enabled but should be restricted by address lists to prevent exposure.
*   **SNMP**: Disabled by default; if enabled, it must be restricted to localhost or specific admin subnets.

### 2. Restricting API & WebFig Access
To lock down management endpoints to the local LAN and the VPN subnet only, configure matching IP address restrictions:
```routeros
/ip service
set winbox address=<LAN_SUBNET>,<WIREGUARD_SUBNET>
set www address=<LAN_SUBNET>,<WIREGUARD_SUBNET>
set ssh address=<LAN_SUBNET>,<WIREGUARD_SUBNET>
set api address=<LAN_SUBNET>,<WIREGUARD_SUBNET>
```

### 3. Password Modification Bypass on SSH
Logging into RouterOS SSH using default credentials may prompt for password change:
```text
Change your password
new password>
```
Pressing `Ctrl+C` at this prompt bypasses the check, landing on `[admin@MikroTik] >`. For long-term automated scripting, it is recommended to create a dedicated read-only operational user with a custom password.