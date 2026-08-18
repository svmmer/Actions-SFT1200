#!/usr/bin/env python3
"""Validate, read, and update the repository's immutable source lock."""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path


REVISION_KEYS = {
    "BUILDER_REV",
    "SIFLOWER_SDK_REV",
    "BASE_PACKAGES_REV",
    "BASE_LUCI_REV",
    "BASE_ROUTING_REV",
    "BASE_TELEPHONY_REV",
    "GL_FEED_REV",
    "LUCI2_REV",
    "PACKAGES2_REV",
    "PWPACKAGES_REV",
    "PASSWALL_REV",
    "HELLOWORLD_REV",
    "GOLANG_REV",
    "ALIYUNDRIVE_REV",
    "LEDE_REV",
    "OPENSSL_ENGINE_ORIGIN_REV",
    "DEPENDENCIES_ORIGIN_REV",
    "ADGUARDHOME_REV",
    "ARGON_REV",
}

REPOSITORY_KEYS = {
    "BUILDER_REPO",
    "BASE_PACKAGES_REPO",
    "BASE_LUCI_REPO",
    "BASE_ROUTING_REPO",
    "BASE_TELEPHONY_REPO",
    "GL_FEED_REPO",
    "LUCI2_REPO",
    "PACKAGES2_REPO",
    "PWPACKAGES_REPO",
    "PASSWALL_REPO",
    "HELLOWORLD_REPO",
    "GOLANG_REPO",
    "ALIYUNDRIVE_REPO",
    "LEDE_REPO",
    "ADGUARDHOME_REPO",
    "ARGON_REPO",
}

BRANCH_KEYS = {
    "BUILDER_BRANCH",
    "PWPACKAGES_BRANCH",
    "PASSWALL_BRANCH",
    "GOLANG_BRANCH",
    "ALIYUNDRIVE_BRANCH",
    "LEDE_BRANCH",
    "ADGUARDHOME_BRANCH",
}

VERSION_KEYS = {
    "PASSWALL_PKG_VERSION",
    "PASSWALL_PKG_RELEASE",
    "XRAY_PKG_VERSION",
    "XRAY_PKG_RELEASE",
}

DIGEST_KEYS = {"LIBS_ZIP_SHA256", "BOARD_BLOB_SHA256"}
REQUIRED_KEYS = (
    {"LOCK_SCHEMA"}
    | REVISION_KEYS
    | REPOSITORY_KEYS
    | BRANCH_KEYS
    | VERSION_KEYS
    | DIGEST_KEYS
)

KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
REV_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
REPO_RE = re.compile(r"^https://[A-Za-z0-9._/-]+\.git$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
VERSION_RE = re.compile(r"^[0-9][0-9A-Za-z.+~_-]*$")


class LockError(ValueError):
    pass


def parse_lock(path: Path) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise LockError(f"{path}:{line_number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        if not KEY_RE.fullmatch(key):
            raise LockError(f"{path}:{line_number}: invalid key {key!r}")
        if key in values:
            raise LockError(f"{path}:{line_number}: duplicate key {key}")
        if not value or any(character.isspace() for character in value):
            raise LockError(f"{path}:{line_number}: invalid value for {key}")
        values[key] = value
    return values, lines


def validate(values: dict[str, str]) -> None:
    missing = sorted(REQUIRED_KEYS - values.keys())
    unknown = sorted(values.keys() - REQUIRED_KEYS)
    if missing:
        raise LockError(f"missing keys: {', '.join(missing)}")
    if unknown:
        raise LockError(f"unknown keys: {', '.join(unknown)}")
    if values["LOCK_SCHEMA"] != "1":
        raise LockError("LOCK_SCHEMA must be 1")

    for key in sorted(REVISION_KEYS):
        if not REV_RE.fullmatch(values[key]):
            raise LockError(f"{key} must be a full lowercase Git revision")
    for key in sorted(REPOSITORY_KEYS):
        if not REPO_RE.fullmatch(values[key]):
            raise LockError(f"{key} must be an HTTPS .git URL")
    for key in sorted(BRANCH_KEYS):
        if not BRANCH_RE.fullmatch(values[key]):
            raise LockError(f"{key} contains invalid branch characters")
    for key in sorted(VERSION_KEYS):
        if not VERSION_RE.fullmatch(values[key]):
            raise LockError(f"{key} contains an invalid package version")
    for key in sorted(DIGEST_KEYS):
        if not DIGEST_RE.fullmatch(values[key]):
            raise LockError(f"{key} must be a lowercase SHA-256 digest")


def update_lock(path: Path, assignments: list[str]) -> None:
    values, lines = parse_lock(path)
    validate(values)
    updates: dict[str, str] = {}
    for assignment in assignments:
        if "=" not in assignment:
            raise LockError(f"invalid update {assignment!r}; expected KEY=VALUE")
        key, value = assignment.split("=", 1)
        if key not in REQUIRED_KEYS:
            raise LockError(f"cannot update unknown key {key}")
        updates[key] = value

    candidate = values | updates
    validate(candidate)
    rendered: list[str] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0]
            if key in updates:
                newline = "\n" if raw_line.endswith("\n") else ""
                raw_line = f"{key}={updates[key]}{newline}"
        rendered.append(raw_line)

    mode = path.stat().st_mode
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.writelines(rendered)
        temporary_path = Path(handle.name)
    os.chmod(temporary_path, mode)
    os.replace(temporary_path, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "env", "get", "update"))
    parser.add_argument("lock_file", type=Path)
    parser.add_argument("arguments", nargs="*")
    args = parser.parse_args()

    try:
        if args.command == "update":
            if not args.arguments:
                raise LockError("update requires at least one KEY=VALUE")
            update_lock(args.lock_file, args.arguments)

        values, _ = parse_lock(args.lock_file)
        validate(values)

        if args.command == "env":
            if args.arguments:
                raise LockError("env does not accept extra arguments")
            for key in sorted(values):
                print(f"{key}={values[key]}")
        elif args.command == "get":
            if len(args.arguments) != 1:
                raise LockError("get requires exactly one key")
            key = args.arguments[0]
            if key not in values:
                raise LockError(f"unknown key {key}")
            print(values[key])
        elif args.command == "validate":
            if args.arguments:
                raise LockError("validate does not accept extra arguments")
            print(f"Validated {args.lock_file} ({len(values)} locked values)")
    except (OSError, LockError) as error:
        print(f"source-lock: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
