import base64
import os
from pathlib import Path
import secrets
import subprocess


SOURCE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = SOURCE_DIR / "runtime"
IMAGE = "rapiz1/rathole@sha256:a31b9178e985d4a84f46d4c3af6aa200ee0c5e7f821c7075a1f6669fb77392b1"


def read_key(output: str, label: str) -> str:
    lines = output.splitlines()
    for index, line in enumerate(lines[:-1]):
        if line.strip() == label:
            key = lines[index + 1].strip()
            if len(base64.b64decode(key, validate=True)) != 32:
                raise ValueError("Invalid Noise key length")
            return key
    raise ValueError(f"Missing {label}")


def write_config(name: str, replacements: dict[str, str]) -> None:
    template = (SOURCE_DIR / f"{name}.template").read_text(encoding="ascii")
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    if "__" in template:
        raise ValueError(f"Unrendered marker in {name}")
    fd = os.open(RUNTIME_DIR / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as target:
        target.write(template)
    if name == "server.toml":
        os.chown(RUNTIME_DIR / name, 1000, 1000)


if RUNTIME_DIR.exists():
    raise SystemExit(f"Runtime directory already exists: {RUNTIME_DIR}")

result = subprocess.run(
    ["docker", "run", "--rm", "--pull=never", IMAGE, "--genkey"],
    check=True,
    capture_output=True,
    text=True,
)
private_key = read_key(result.stdout, "Private Key:")
public_key = read_key(result.stdout, "Public Key:")
token = secrets.token_hex(32)
RUNTIME_DIR.mkdir(mode=0o700)
write_config("server.toml", {"__TOKEN__": token, "__NOISE_PRIVATE__": private_key})
write_config("client.toml", {"__TOKEN__": token, "__NOISE_PUBLIC__": public_key})
print("Noise keypair and matching server/client configs generated (secrets not printed)")
