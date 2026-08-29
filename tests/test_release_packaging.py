from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]


class ReleasePackagingTests(unittest.TestCase):
    def test_release_builds_omit_private_debug_records(self) -> None:
        for project in (
            ROOT / "simhub" / "AsDriven.Core" / "AsDriven.Core.csproj",
            ROOT / "simhub" / "AsDriven.Plugin" / "AsDriven.Plugin.csproj",
        ):
            text = project.read_text(encoding="utf-8")
            release = re.search(
                r"<PropertyGroup Condition=\" '.*Release.*' \"[^>]*>(.*?)</PropertyGroup>",
                text,
                re.DOTALL,
            )
            self.assertIsNotNone(release, project)
            self.assertIn("<DebugSymbols>false</DebugSymbols>", release.group(1))
            self.assertIn("<DebugType>none</DebugType>", release.group(1))

        build = (ROOT / "simhub" / "build.ps1").read_text(encoding="utf-8")
        self.assertIn('if ($Configuration -eq "Debug")', build)
        self.assertIn('"AsDriven.Plugin.pdb", "AsDriven.Core.pdb"', build)

    def test_public_package_has_clear_user_entry_points(self) -> None:
        package = ROOT / "release" / "package"
        start = (package / "START HERE.txt").read_text(encoding="utf-8")
        install = (package / "Install As Driven.cmd").read_text(encoding="utf-8")
        uninstall = (package / "Uninstall As Driven.cmd").read_text(encoding="utf-8")

        self.assertIn('Double-click "Install As Driven.cmd"', start)
        self.assertIn("Settings > Plugins", start)
        self.assertIn("Start-Process", install)
        self.assertIn("-Verb RunAs", install)
        self.assertIn("simhub\\install.ps1", install)
        self.assertIn("simhub\\uninstall.ps1", uninstall)

    def test_package_verifier_rejects_private_release_contents(self) -> None:
        verifier = (
            ROOT / "release" / "test-release-package.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn('Filter "*.pdb"', verifier)
        self.assertIn('"AGENTS.md", "CLAUDE.md"', verifier)
        self.assertIn("local user path", verifier)
        self.assertIn("Compare-Object $manifestPaths $actualPaths", verifier)

    def test_publisher_is_draft_only_and_requires_approval(self) -> None:
        publisher = (
            ROOT / "release" / "publish-github-release.ps1"
        ).read_text(encoding="utf-8")
        approval_gate = publisher.index("if (-not $Approve)")
        github_mutation = publisher.index('$arguments = @("release", "create", $tag)')

        self.assertLess(approval_gate, github_mutation)
        # Draft is the safety gate and stays. Prerelease was the early-access
        # support tier and does not: the project publishes ordinary releases.
        self.assertIn('"--draft"', publisher)
        self.assertNotIn("--prerelease", publisher)
        self.assertIn('if ($branch -ne "main")', publisher)
        self.assertIn("status --porcelain --untracked-files=no", publisher)
        self.assertIn("test-release-package.ps1", publisher)
        self.assertIn("test-install-database.ps1", publisher)
        self.assertNotIn("gh release edit", publisher)


if __name__ == "__main__":
    unittest.main()
