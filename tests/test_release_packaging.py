from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from as_driven_db.update_manifest import (  # noqa: E402
    check_update_manifest,
    read_update_manifest,
    release_request,
)


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
        self.assertIn("package_url", publisher)
        self.assertIn("package_sha256 = $pluginHash", publisher)
        self.assertNotIn("gh release edit", publisher)
        # The existence check must decide on the exit code alone. gh writes
        # "release not found" to stderr for a tag nobody has published, and
        # Windows PowerShell turns a native command's stderr into a terminating
        # error while ErrorActionPreference is Stop - so the first release, the
        # one case with no existing tag, threw instead of proceeding.
        guard = publisher[publisher.index("gh release view") - 400:]
        self.assertIn('$ErrorActionPreference = "Continue"', guard)
        self.assertIn("$releaseExists = ($LASTEXITCODE -eq 0)", guard)


    def test_the_readme_release_section_names_the_current_client_version(self) -> None:
        """The README's "New in" blurb is written by hand and drifts silently.

        At 0.21.5 the heading was updated while 0.21.4's bullets stayed beneath
        it, and the section described the wrong release for two versions without
        anything failing. This does not read the bullets, which no test can
        check, but a heading that still names the previous release is the signal
        that nobody rewrote them.
        """
        assembly = (
            ROOT / "simhub" / "AsDriven.Plugin" / "Properties" / "AssemblyInfo.cs"
        ).read_text(encoding="utf-8-sig")
        match = re.search(r'AssemblyVersion\("(\d+)\.(\d+)\.(\d+)\.\d+"\)', assembly)
        self.assertIsNotNone(match, "no AssemblyVersion in the plugin assembly info")
        version = ".".join(match.groups())

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        headings = re.findall(r"^## New in (\S+)\s*$", readme, re.M)
        self.assertEqual(
            [version],
            headings,
            "README needs exactly one '## New in <client version>' section, "
            "rewritten for the release being prepared",
        )

    def test_the_public_update_manifest_matches_its_release(self) -> None:
        """The file the plugin's default endpoint actually reads.

        The endpoint is a raw URL on the default branch, so this file is what
        every installation is told when it checks. A prepared draft may be ahead
        of it; pushing a draft must not announce an unavailable public download.
        """
        manifest = json.loads(
            (ROOT / "as-driven-latest.json").read_text(encoding="utf-8")
        )
        index = json.loads(
            (ROOT / "data" / "v1" / "index.json").read_text(encoding="utf-8-sig")
        )
        self.assertRegex(manifest["dataset_version"], r"^\d+\.\d+\.\d+$")
        self.assertLessEqual(tuple(map(int, manifest["dataset_version"].split('.'))),
                             tuple(map(int, index["dataset_version"].split('.'))))
        self.assertRegex(manifest["plugin_version"], r"^\d+\.\d+\.\d+$")
        changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
        section = re.search(r'^## ' + re.escape(manifest['plugin_version'])
                            + r' - [^\n]+\n(.*?)(?=^## |\Z)', changelog, re.M | re.S)
        self.assertIsNotNone(section, 'The announced release must have a changelog entry')
        self.assertIn('dataset ' + manifest['dataset_version'], section.group(1))
        self.assertEqual(
            f"https://github.com/Milky28/as-driven/releases/tag/v{manifest['plugin_version']}",
            manifest["release_url"],
        )
        # The endpoint the client ships must be the file this test just checked.
        settings = (
            ROOT / "simhub" / "AsDriven.Plugin" / "AsDrivenSettings.cs"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "https://raw.githubusercontent.com/Milky28/as-driven/main/as-driven-latest.json",
            settings,
        )

    def test_next_release_manifest_enables_verified_install(self) -> None:
        builder = (ROOT / "release" / "build-release.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn('""package_url""', builder)
        self.assertIn('""package_sha256""', builder)
        self.assertIn("$zipHash", builder)

        publisher = (ROOT / "release" / "publish-github-release.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("releases/download/$tag/", publisher)
        self.assertIn("package_sha256 = $pluginHash", publisher)


class UpdateManifestPromotionTests(unittest.TestCase):
    """The root manifest must not lag the newest release a driver can download.

    Publishing writes the manifest as a release asset and stops; copying it
    into the root is manual, and 0.21.5 was published with the root still
    announcing 0.21.4. Every installation that checked was told it was current.
    """

    @staticmethod
    def _release(tag: str, *, draft: bool = False, prerelease: bool = False):
        return {"tag_name": tag, "draft": draft, "prerelease": prerelease}

    def test_a_manifest_behind_the_published_latest_is_an_error(self) -> None:
        errors = check_update_manifest(
            {"plugin_version": "0.21.4"},
            [self._release("v0.21.5"), self._release("v0.21.4")],
        )
        self.assertEqual(1, len(errors), errors)
        self.assertIn("v0.21.5", errors[0])

    def test_a_manifest_matching_the_published_latest_passes(self) -> None:
        self.assertEqual(
            [],
            check_update_manifest(
                {"plugin_version": "0.21.5"},
                [self._release("v0.21.5"), self._release("v0.21.4")],
            ),
        )

    def test_a_draft_is_not_something_a_driver_can_download(self) -> None:
        """The root stays on the last published release while a candidate drafts."""
        self.assertEqual(
            [],
            check_update_manifest(
                {"plugin_version": "0.21.5"},
                [self._release("v0.21.6", draft=True), self._release("v0.21.5")],
            ),
        )

    def test_announcing_an_unpublished_version_is_an_error(self) -> None:
        errors = check_update_manifest(
            {"plugin_version": "0.21.6"}, [self._release("v0.21.5")]
        )
        self.assertEqual(1, len(errors), errors)
        self.assertIn("does not exist", errors[0])

    def test_a_prerelease_is_downloadable_but_is_not_the_latest(self) -> None:
        releases = [self._release("v0.22.0", prerelease=True), self._release("v0.21.5")]
        self.assertEqual([], check_update_manifest({"plugin_version": "0.21.5"}, releases))
        self.assertEqual([], check_update_manifest({"plugin_version": "0.22.0"}, releases))

    def test_the_listing_call_uses_a_token_when_the_run_has_one(self) -> None:
        """Anonymous api.github.com calls share an hourly budget a runner burns."""
        anonymous = release_request("owner/repo", environment={})
        self.assertNotIn("Authorization", anonymous.headers)
        authenticated = release_request("owner/repo", environment={"GITHUB_TOKEN": "t"})
        self.assertEqual("Bearer t", authenticated.headers["Authorization"])
        self.assertIn("owner/repo", authenticated.full_url)

    def test_a_workflow_checks_the_endpoint_after_a_release_is_published(self) -> None:
        """A release does not push a commit, so no ordinary trigger sees the gap."""
        workflow = (
            ROOT / ".github" / "workflows" / "update-endpoint.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("check-update-manifest", workflow)
        self.assertIn("types: [published, released, unpublished, deleted]", workflow)
        self.assertIn("cron:", workflow)
        # A release event checks out its own tag; the file under test is main's.
        self.assertIn("ref: main", workflow)

    def test_the_checked_in_manifest_is_current_for_its_own_release(self) -> None:
        """Offline: the manifest against a listing containing what it announces."""
        manifest = read_update_manifest(ROOT)
        self.assertEqual(
            [],
            check_update_manifest(
                manifest, [self._release("v" + manifest["plugin_version"])]
            ),
        )

if __name__ == "__main__":
    unittest.main()
