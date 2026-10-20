#!/usr/bin/env python3
"""Preview or remove Dead Swarm tasks without deleting images or volumes."""

import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess


def docker(*args):
    return subprocess.run(["docker", *args], capture_output=True, text=True)


def running_ids():
    result = docker("ps", "--no-trunc", "-q")
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return sorted(result.stdout.split())


def inspect_candidate(container_id):
    result = docker("inspect", container_id)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    data = json.loads(result.stdout)[0]
    labels = data["Config"].get("Labels") or {}
    diff = docker("diff", container_id)
    missing_layer = any(message in diff.stderr for message in (
        "rw layer snapshot not found", "RWLayer is unexpectedly nil",
    ))
    changes = diff.stdout.splitlines()
    eligible = (
        data["State"]["Status"] == "dead"
        and not data["State"].get("Running")
        and bool(labels.get("com.docker.swarm.task.id"))
        and ((diff.returncode == 0 and not changes) or missing_layer)
    )
    return {
        "id": data["Id"],
        "name": data["Name"],
        "status": data["State"]["Status"],
        "task_id": labels.get("com.docker.swarm.task.id"),
        "image": data["Image"],
        "mounts": data.get("Mounts", []),
        "writable_changes": len(changes),
        "diff_error": diff.stderr.strip(),
        "eligible": eligible,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    before = running_ids()
    result = docker("ps", "-a", "--no-trunc", "--filter", "status=dead", "-q")
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    candidates = [inspect_candidate(cid) for cid in result.stdout.split()]
    report = {"apply": args.apply, "running_before": before, "candidates": candidates}
    report_path = None
    if args.apply:
        os.umask(0o077)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        directory = Path("/var/lib/homelab-maintenance") / stamp
        directory.mkdir(parents=True, exist_ok=False)
        report_path = directory / "dead-tasks.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        for candidate in candidates:
            if not candidate["eligible"]:
                continue
            # Recheck after preview; never force-remove a task that restarted.
            current = inspect_candidate(candidate["id"])
            if not current["eligible"]:
                raise RuntimeError("candidate changed: " + candidate["id"])
            removed = docker("rm", candidate["id"])
            candidate["removed"] = removed.returncode == 0
            candidate["remove_error"] = removed.stderr.strip()
            report_path.write_text(json.dumps(report, indent=2) + "\n")
            if removed.returncode:
                raise RuntimeError(removed.stderr.strip())
    report["running_after"] = running_ids()
    report["running_unchanged"] = report["running_after"] == before
    if report_path:
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print("report_path=" + str(report_path))
    print(json.dumps({
        "apply": args.apply,
        "dead_count": len(candidates),
        "eligible_count": sum(c["eligible"] for c in candidates),
        "removed_count": sum(c.get("removed", False) for c in candidates),
        "skipped": [c for c in candidates if not c["eligible"]],
        "running_count": len(before),
        "running_unchanged": report["running_unchanged"],
    }, indent=2))
    if not report["running_unchanged"]:
        raise RuntimeError("running containers changed; inspect before continuing")


if __name__ == "__main__":
    main()
