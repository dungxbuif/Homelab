# Proxmox API trust bootstrap

Purpose: remove the TLS-trust prerequisite for a future VM100 import without
using an insecure API client or changing VM state. Existing operator bootstrap
credentials may be used only to acquire public trust material; do not place
the password or API token in Git or command output.

The controller already trusts the ED25519 SSH host key for `10.10.0.20` in
known_hosts. A password-authenticated connection with `StrictHostKeyChecking=yes`,
`IdentityAgent=none` and public-key auth disabled succeeded and returned host
`pve`. It read only `/etc/pve/pve-root-ca.pem` and its SHA256 fingerprint.
This independently authenticated SSH channel, not an unverified HTTPS download,
is the trust source for the public CA certificate.

Expected certificate SHA256:
`375760fd7570a7e09d0625e8de31c18e057ba890dd2c1891ec1769434fd58fa3`.

Store the public CA under `automation/tofu/proxmox/pki/`, verify its DER hash
with a regression test, and test an HTTPS request to the existing API endpoint
using only that CA. Keep hostname verification enabled. Do not install this CA
globally, regenerate node certificates, restart Proxmox or import state during
this step. A future controlled OpenTofu job should inject its reviewed CA path
through `SSL_CERT_FILE`; private state keys and scoped credentials remain
separate prerequisites. No application/public documentation changes are needed.

Live TLS check found a second prerequisite: the node certificate contains
`pve`, `pve.nccsoft.office`, localhost and the old address `10.10.60.90`, not
the current `10.10.0.20`. The IP-based URL correctly fails hostname validation.
Use the certified name `https://pve:8006/` with an executor-only fixed mapping
`pve:10.10.0.20`; retain full chain/hostname verification. Update the module
default accordingly and document the mapping as required executor configuration.
Do not change system-wide DNS, Proxmox host configuration or its certificates
merely to bypass this mismatch. No live runner mapping has been deployed yet.

## Verification and compatibility limits

- The certificate regression verifies exactly one public CA and its DER hash;
  the default-endpoint regression caught the old IP URL before correction.
- Host curl and curl inside `homelab-automation-ee:local`, with only this CA and
  a fixed `pve:10.10.0.20` mapping, return HTTP 401 with verified chain and name.
  No authentication credential was sent. 401 proves TLS completed, not API rights.
- A disposable Go standard-library HTTP client with this sole RootCAs pool,
  normal hostname checking, fixed dial target and redirects disabled also
  returned 401. This is Go TLS evidence, not a live bpg provider plan.
- Python 3.13's default strict SSL verifier in the EE rejects this older CA:
  `CA cert does not include key usage extension`. Do NOT disable verification
  or strict flags to make a future Python/Ansible API task pass. Such clients
  require a separately planned PKI repair/rotation with dependent-client impact
  assessed. The bundled public CA is not claimed compatible with every client.
- All 14 OpenTofu Python tests and `tofu fmt -check` pass. No import, state
  creation, VM mutation, runner restart or global trust-store change occurred.

Reproduce the credential-free curl check from the repository root:

```sh
curl --disable --noproxy '*' --connect-timeout 5 --max-time 15 \
  --cacert automation/tofu/proxmox/pki/pve-root-ca.pem \
  --resolve pve:8006:10.10.0.20 --output /dev/null --write-out '%{http_code}\n' \
  https://pve:8006/api2/json/version
```
