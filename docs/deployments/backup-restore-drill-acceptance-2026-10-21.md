# Monthly restore drill acceptance: 2026-10-21

## Result

The first VM100 restore drill completed successfully after the disposable
target cleanup trap was corrected.

| Class | Snapshot | Result |
|---|---|---|
| `databases` | `45fc58a1c463cb5ec85a008007e26ee1f0e5376d40ee1f858d2afe50436762cb` | Restored and checksum-verified |
| `database-instances` | `164f85eb25e03f936a9cba0c29185d00712bf4cfbc155d1818726224ea3e72c7` | Restored and checksum-verified |
| `gitlab` | `a0cbb341f856d2ef324cb57b4ddb29dc4eab23f22c690e9c0d131531cac26fb` | Restored and checksum-verified |
| `rustfs` | `667cb32216c6417d1ab9d2b7a6b28d2839d04e5e5b672af8e87329d6b942942c` | Restored and checksum-verified |

The service exited with status `0` and wrote:

```text
/opt/apps/homelab-backup/runs/.state/restore-drill.success
```

The dedicated cleanup regression run restored the RustFS class again using the
same code path, then verified that both its target directory and temporary
status directory no longer existed. No production volume or host port was
used.

## Correction made during acceptance

`restic-lib.sh` installs an internal temporary rclone cleanup trap. The drill
had installed its own `EXIT` trap before sourcing that file, so the internal
trap replaced the drill cleanup trap. The drill now installs its trap after
sourcing the library and explicitly removes the temporary rclone workdir.

## Runtime

- Service: `homelab-backup-restore-drill.service`
- Timer: `homelab-backup-restore-drill.timer`
- Schedule: first day of each month at 14:00 Asia/Ho_Chi_Minh
- Current VM100 disk after cleanup-check: about 30 GB free
- Production restore marker remains separate from the cleanup regression
  status root.
