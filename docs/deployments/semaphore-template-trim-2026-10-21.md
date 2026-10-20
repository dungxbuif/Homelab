# Semaphore template trim

Date: 2026-10-21

## Change

The `Homelab Control Plane` project had accumulated 14 retired `Knowledge
Hub ...` templates for one-off network, CouchLoom and n8n experiments. They
were removed through the authenticated Semaphore API, one template at a time;
all DELETE requests returned HTTP `204`.

Removed template IDs:

```text
11 12 13 14 15 16 17 18 19 21 29 30 31 32
```

## Retained templates

The project now contains only these seven operational templates:

- `3` Check backup health (read only)
- `5` Inspect Pi5 runtime (read only)
- `4` Inspect VM100 runtime (read only)
- `1` Provision database and application owner
- `6` Release approved Homepage
- `7` Release backup client (Pi5)
- `2` Verify GitLab source and control connectivity

## Verification

- Live template listing returned exactly the seven retained templates.
- Project task history currently contains 68 records, all associated with the
  seven retained templates. Entries associated with the retired templates no
  longer appear in the project history after the API deletion, so the old
  Knowledge Hub failure burst is no longer mixed into the operator view.
- The separate `Homelab Audit` project remains available for read-only audits.

Future one-off experiments must use a temporary branch and be removed from the
live project after completion; they must not become permanent operator UI
templates.
