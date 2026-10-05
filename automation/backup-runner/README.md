# Backup Runner

The runner serializes each backup class behind one host lock. A class always
follows this order:

```text
native/API export -> COMPLETE + manifest + checksums -> restic backup/check
-> post-check -> one Mezon status
```

`run-class.sh` supports `databases`, `rustfs`, and `gitlab`. The GitLab class
receives a completed directory produced by the VM100 native wrapper; it never
copies a live GitLab filesystem itself. `run-retention.sh` is separate and
prunes only after repository checks, using the three class-specific restic
repositories.

Required runtime environment is secret-free in the repository and must be
provided by Semaphore/Docker secrets:

```text
RESTIC_PASSWORD_FILE
RCLONE_CONFIG_FILE
BACKUP_LOCAL_RCLONE_BIN
RCLONE_REMOTE
DRIVE_ROOT
MEZON_WEBHOOK_URL_FILE
RUSTFS_CREDENTIALS_FILE  # required for the rustfs class
```

The runner does not stop, scale, recreate, or remove production services. Exit
code `75` means another class already owns the global lock and the scheduler
should retry later without overlapping it.
