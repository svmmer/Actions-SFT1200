#!/usr/bin/env python3
"""Select and validate the Go feed required by an Xray release."""

from __future__ import annotations

import argparse
import re
import sys


GO_VERSION_RE = re.compile(r"^1\.([0-9]+)(?:\.([0-9]+))?$")


class GoVersionError(ValueError):
    pass


def parse_go_version(value: str) -> tuple[int, int]:
    match = GO_VERSION_RE.fullmatch(value)
    if not match:
        raise GoVersionError(f"invalid stable Go version: {value}")
    return int(match.group(1)), int(match.group(2) or 0)


def required_feed_branch(required_version: str) -> str:
    minor, _ = parse_go_version(required_version)
    return f"{minor}.x"


def check_compatibility(required_version: str, toolchain_version: str) -> None:
    required = parse_go_version(required_version)
    provided = parse_go_version(toolchain_version)
    if provided < required:
        raise GoVersionError(
            f"Xray requires Go {required_version}, but the selected feed provides "
            f"{toolchain_version}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    branch_parser = subparsers.add_parser("branch")
    branch_parser.add_argument("required_version")

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("required_version")
    check_parser.add_argument("toolchain_version")

    args = parser.parse_args()
    try:
        if args.command == "branch":
            print(required_feed_branch(args.required_version))
        else:
            check_compatibility(args.required_version, args.toolchain_version)
            print(
                f"Go {args.toolchain_version} satisfies Xray's "
                f"Go {args.required_version} requirement"
            )
    except GoVersionError as error:
        print(f"go-toolchain: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
