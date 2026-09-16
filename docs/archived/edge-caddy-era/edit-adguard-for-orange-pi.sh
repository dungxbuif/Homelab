#!/usr/bin/env bash
# Phase P0.11b + Phase D3-prep — AdGuardHome.yaml edits for orange-pi迁移
#
# TWO edits required in /opt/edge/adguard/conf/AdGuardHome.yaml
# (orange-pi copy, after Phase P0.11 unpacked from snapshot):
#
#   1. bind_hosts:  - 0.0.0.0      →  - 10.10.0.2
#      Avoid port-53 conflict with orange-pi systemd-resolved stub
#      (loops on 127.0.0.53 only; wildcard 0.0.0.0:53 can race).
#
#   2. rewrites:
#        - domain: '*.dungxbuif.com'     (unchanged)
#          answer: 10.10.0.5             → 10.10.0.2  (CRITICAL)
#      This rewrite tells LAN clients where *.dungxbuif.com is. After
#      migration, Caddy lives on orange-pi (.2), so LAN clients hitting
#      *.dungxbuif.com must be sent to .2 — otherwise they hit Pi5:443
#      (stopped) and get connection refused.
#
#      Public clients via Cloudflare: not affected (CF proxied records
#      point to VPS Rathole server :7000 which tunnels back to orange-pi).
#      Only LAN clients use this AdGuard rewrite to bypass VPS.
#
#      The other rewrite `netbird.dungxbuif.com → 103.82.21.202` is for
#      Netbird on the VPS and does NOT change.
#
# USAGE (on orange-pi, AFTER P0.11 unpacked the snapshot):
#   sudo bash /opt/edge/adguard/edit-for-orange-pi.sh
#
# Implementation note: uses `perl -i` for portability (same behavior on
# macOS BSD and Linux GNU). Avoids sed incompatibilities between platforms.

set -euo pipefail
CONF=/opt/edge/adguard/conf/AdGuardHome.yaml

if [ ! -f "$CONF" ]; then
  echo "ERROR: $CONF not found — run P0.11 (unpack snapshot) first." >&2
  exit 1
fi

echo "==> Before:"
grep -nE "^  - 0\.0\.0\.0|domain: '\*\.dungxbuif\.com'|answer:" "$CONF" | head -5

# 1) bind_hosts: replace list item "- 0.0.0.0" (any indent) with "- 10.10.0.2"
#    Safe: 0.0.0.0 appears only in bind_hosts in AdGuardHome.yaml default configs.
perl -i -pe 's/^\s+- 0\.0\.0\.0$/    - 10.10.0.2/' "$CONF"

# 2) *.dungxbuif.com rewrite: capture the whole prefix (incl. "answer: "
#    with trailing space) so we re-emit it without an extra space.
#    Slurp mode (-0777) needed for \n across the capture.
perl -i -0777 -pe 's/(- domain: '\''\*\.dungxbuif\.com'\''\n\s+answer: )10\.10\.0\.5/${1}10.10.0.2/' "$CONF"

echo
echo "==> After:"
grep -nE "^  - 10\.10\.0\.2|domain: '\*\.dungxbuif\.com'|answer:" "$CONF" | head -5

echo
echo "==> Verify both edits applied:"
A1=$(grep -c "^\s*- 10\.10\.0\.2$" "$CONF")
A2=$(perl -ne 'print "OK\n" and exit if $prev =~ /\*\.dungxbuif\.com/ && /answer: 10\.10\.0\.2/; $prev = $_' "$CONF")
echo "  bind_hosts -> 10.10.0.2 : $A1 occurrence(s) [expect >=1]"
echo "  *.dungxbuif.com answer -> 10.10.0.2 : ${A2:-MISSING} [expect OK]"
echo
echo "Done. Run adguardhome to verify it binds 10.10.0.2:53 and answers *.dungxbuif.com -> 10.10.0.2"
