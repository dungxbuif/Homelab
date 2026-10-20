#!/usr/bin/env python3
"""Report Swarm services without an explicit bounded json-file log policy."""

from __future__ import annotations

import json
import subprocess
import sys


def run(*args: str) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return result.stdout


def main() -> int:
    names = [line for line in run("docker", "service", "ls", "--format", "{{.Name}}").splitlines() if line]
    rows = []
    for name in names:
        payload = json.loads(run("docker", "service", "inspect", name))[0]
        spec = payload["Spec"]
        driver = spec.get("TaskTemplate", {}).get("LogDriver")
        options = (driver or {}).get("Options", {})
        bounded = (
            driver
            and driver.get("Name") == "json-file"
            and options.get("max-size")
            and options.get("max-file")
        )
        rows.append(
            {
                "service": name,
                "image": spec.get("TaskTemplate", {}).get("ContainerSpec", {}).get("Image", "").split("@", 1)[0],
                "driver": (driver or {}).get("Name") if driver else None,
                "max_size": options.get("max-size") if driver else None,
                "max_file": options.get("max-file") if driver else None,
                "bounded": bool(bounded),
            }
        )
    print(json.dumps({"service_count": len(rows), "unbounded": [row for row in rows if not row["bounded"]], "services": rows}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
