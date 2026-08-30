#!/usr/bin/env python3
"""Regression tests for the automatic firmware-build update gate."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_LOCK = REPOSITORY_ROOT / "sources.lock"
SOURCE_LOCK_SCRIPT = REPOSITORY_ROOT / "scripts" / "source-lock.py"

BASELINE = {
    "PASSWALL_REV": "a" * 40,
    "PWPACKAGES_REV": "b" * 40,
    "GOLANG_REV": "c" * 40,
    "PASSWALL_PKG_VERSION": "26.8.26",
    "PASSWALL_PKG_RELEASE": "1",
    "XRAY_PKG_VERSION": "26.7.28",
    "XRAY_PKG_RELEASE": "1",
}


class ProxyUpdateGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.lock_file = Path(self.temporary_directory.name) / "sources.lock"

        replacements = BASELINE.copy()
        rendered_lines = []
        for line in SOURCE_LOCK.read_text(encoding="utf-8").splitlines(keepends=True):
            key = line.partition("=")[0]
            if key in replacements:
                newline = "\n" if line.endswith("\n") else ""
                line = f"{key}={replacements[key]}{newline}"
            rendered_lines.append(line)
        self.lock_file.write_text("".join(rendered_lines), encoding="utf-8")

    def run_gate(self, **overrides: str) -> subprocess.CompletedProcess[str]:
        candidate = {
            "PASSWALL_REV": "d" * 40,
            "PWPACKAGES_REV": "e" * 40,
            "GOLANG_REV": "f" * 40,
            **{
                key: BASELINE[key]
                for key in (
                    "PASSWALL_PKG_VERSION",
                    "PASSWALL_PKG_RELEASE",
                    "XRAY_PKG_VERSION",
                    "XRAY_PKG_RELEASE",
                )
            },
            **overrides,
        }
        return subprocess.run(
            [
                sys.executable,
                str(SOURCE_LOCK_SCRIPT),
                "proxy-update-needed",
                str(self.lock_file),
                *(f"{key}={value}" for key, value in candidate.items()),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_revision_only_changes_do_not_trigger_firmware_build(self) -> None:
        result = self.run_gate()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "false\n")

    def test_each_proxy_package_version_or_release_change_triggers_build(self) -> None:
        changes = {
            "PASSWALL_PKG_VERSION": "26.8.27",
            "PASSWALL_PKG_RELEASE": "2",
            "XRAY_PKG_VERSION": "26.8.1",
            "XRAY_PKG_RELEASE": "2",
        }

        for key, value in changes.items():
            with self.subTest(key=key):
                result = self.run_gate(**{key: value})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "true\n")

    def test_incomplete_candidate_is_rejected_instead_of_silently_skipped(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SOURCE_LOCK_SCRIPT),
                "proxy-update-needed",
                str(self.lock_file),
                "PASSWALL_PKG_VERSION=26.8.27",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing candidate keys", result.stderr)


if __name__ == "__main__":
    unittest.main()
