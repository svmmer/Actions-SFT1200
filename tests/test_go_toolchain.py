#!/usr/bin/env python3
"""Regression tests for selecting an Xray-compatible Go toolchain."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GO_TOOLCHAIN_SCRIPT = REPOSITORY_ROOT / "scripts" / "go-toolchain.py"


class GoToolchainTests(unittest.TestCase):
    def run_tool(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(GO_TOOLCHAIN_SCRIPT), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_required_xray_go_version_selects_matching_feed_branch(self) -> None:
        result = self.run_tool("branch", "1.27")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "27.x\n")

    def test_rejects_toolchain_older_than_xray_requirement(self) -> None:
        result = self.run_tool("check", "1.27", "1.26.8")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires Go 1.27", result.stderr)
        self.assertIn("provides 1.26.8", result.stderr)

    def test_accepts_matching_or_newer_toolchain(self) -> None:
        for toolchain in ("1.27", "1.27.1", "1.28"):
            with self.subTest(toolchain=toolchain):
                result = self.run_tool("check", "1.27", toolchain)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_malformed_go_versions(self) -> None:
        for version in ("27", "go1.27", "1.27-rc1", "2.0"):
            with self.subTest(version=version):
                result = self.run_tool("branch", version)
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
