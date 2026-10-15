# Include documentation in credential-pattern checks

The CI tracked-file credential scanner excludes all Markdown. This permits
supported token/private-key patterns in runbooks to pass even though documentation
is part of the source-preservation scope. Remove that extension exclusion while
preserving filename-only diagnostics and fail-closed Git execution handling.

Verification: add a regression with a synthetic token in a tracked Markdown
file, observe failure before the fix, then run the scanner tests and the full
automation Python suite. Scan the clean GitLab publication checkout without
printing matched contents. This remains a limited pattern gate, not proof of
the absence of arbitrary passwords or unsupported credential formats. Do not
use a clean result to authorize publishing local credential files or full old
history. No production service behavior or public docs change.

The regression returned false success before the fix. After removing the
exclusion, all 70 automation Python tests pass, including Markdown rejection
without echoing its synthetic token. The clean GitLab publication checkout also
passes the updated tracked-file scan. This does not scan ignored files or prove
the safety of unpublished legacy worktree content.
