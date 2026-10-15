# Drift policy input validation

The read-only inventory comparator currently defaults absent policy collections
to empty lists and collapses duplicate IDs into sets. An incomplete or corrupted
policy can therefore produce a false matching inventory. Policy parsing also
occurs outside the structured error boundary.

Require an explicit object with hosts/services/routes lists, object entries,
unique nonempty string IDs without surrounding whitespace. Empty lists remain
valid when explicitly declared. Invalid YAML, inaccessible files, and malformed
policy input must exit 2 with status `not_verified`, without echoing file content.
Reject duplicate YAML mapping keys before construction can discard declarations,
including duplicate `id` fields within entries. Mapping keys must be strings.
Existing matching/drift exit codes (0/1) and `inventory_ids_only` scope remain.
This does not certify topology, resources, routes, policy completeness, or live
collection provenance; those acceptance requirements remain open.

Verification: real CLI regression tests for invalid policy cases, existing
fresh/stale observation tests, and the automation Python suite. No live runtime
configuration changes. Public application docs do not change; this is an internal
automation input contract, documented in the automation operator README.

Verification result: all 13 malformed-policy regression cases failed against
the original CLI, including duplicate IDs and absent routes incorrectly returning
exit 0. After correction, all 69 automation Python tests pass in the pinned local
execution image. Error responses contain a fixed reason, not YAML content or
file paths. Review identified duplicate YAML keys as a second way to discard
declarations. Two further regressions reproduced false success before adding a
strict SafeLoader subclass; both now require structured rejection. Publication
and CI acceptance are tracked separately from local tests.
