# CI secret scan failure handling

Pipeline 2 job 5 reported success even though Git refused `/workspace` because
of checkout ownership. The old `! git grep` inverted every error, not just the
documented no-match status. Do not treat that pipeline as security validation.

Implement a dedicated scanner: trust only its explicit repository path, report
matching filenames without secret contents, return success only for grep exit
1, and fail on both matches and execution errors. Keep the existing tracked-file
and non-Markdown scope; this is a limited credential-pattern check, not a full
secret detector. Test clean, matching and invalid repositories, plus simulated
Git failure. Wire tests and the scanner into CI. No public app behavior changes.

Implemented: four regression tests pass on macOS and inside the local execution
image; ShellCheck passes and the current tracked checkout passes the scanner.
The scanner no longer prints matching secret values. Fresh CI is still required
to verify cross-user checkout ownership on VM100. The earlier pipeline may
publish its SHA-tagged image; do not deploy that image as a validated executor.
