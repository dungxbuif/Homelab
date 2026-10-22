# DB Operations VM OpenTofu boundary

This module owns VM110 (`db-ops`) only. It is separate from the protected
VM100 import module so a DB-operations change cannot target production compute
by accident.

| Field | Value |
|---|---|
| VM ID | `110` |
| LAN | `10.10.0.32` |
| Allocation | 4 vCPU, 8192 MiB RAM, 80 GiB `local-lvm` |
| Source | Ubuntu 22.04 cloud-init template `9000` |
| Public ports | None |
| Production data | Remains on Pi5 |

The first run is import-only. Inject the API token, state encryption key and
public SSH key from Semaphore/1Password; never commit a tfvars file or private
key. The first plan must show only the import and no mutation. `prevent_destroy`
is intentional. Scheduler cutover is separate and keeps VM100 as rollback until
remote post-check and restore acceptance pass.
