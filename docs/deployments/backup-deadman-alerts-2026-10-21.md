# Backup dead-man alert hardening: 2026-10-21

The VM100 health service already calls the allow-listed Pi5 health command and
sends its result to Mezon. Before this change, a Pi5 health command could exit
successfully while printing `missing success marker` or `stale success marker`
as a warning. VM100 therefore recorded `Pi backup health check passed` and did
not raise an alert.

VM100 now treats these remote marker messages, invalid markers, and an
explicitly reported remote failure as a health failure. The existing
lock-aware behavior is preserved: an active backup may defer a marker without
triggering a false alarm. No new SSH permission, port, or Pi5 service was
introduced.

Verification is the scheduler contract suite plus a live VM100 health run;
the live run must show `restore-drill.success_age`, a free backup lock, and no
failed backup unit.
