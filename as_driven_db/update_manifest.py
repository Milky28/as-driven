"""Check that the update endpoint announces the newest published release.

`release/publish-github-release.ps1` writes `as-driven-latest.json` as a
release asset and stops. Copying it into the repository root is a separate
manual step, deliberately so: while a candidate is still a draft the root
manifest has to keep pointing at the last release a driver can actually
download. Nothing prompted the maintainer once the draft was published,
and 0.21.5 shipped with the root still announcing 0.21.4.

The comparison is pure and the fetch is separate, so the rules can be tested
without a network.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.request
from typing import Any, Iterable, Mapping

DEFAULT_REPOSITORY = "Milky28/as-driven"
MANIFEST_NAME = "as-driven-latest.json"


class UpdateManifestError(ValueError):
    """The published update manifest cannot be checked."""


def read_update_manifest(root: Path) -> dict[str, Any]:
    path = root / MANIFEST_NAME
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exception:
        raise UpdateManifestError(f"cannot read {path}: {exception}") from exception


def _version(tag: str) -> tuple[int, ...] | None:
    """A release tag as a comparable version, or None if it is not one."""
    parts = tag.lstrip("vV").split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def check_update_manifest(
    manifest: dict[str, Any], releases: Iterable[dict[str, Any]]
) -> list[str]:
    """Errors describing how the manifest disagrees with published releases.

    A draft is not published, so it never counts. A prerelease is downloadable
    but is not the latest, matching what GitHub itself calls Latest.
    """
    announced_text = manifest.get("plugin_version")
    announced = _version(str(announced_text)) if announced_text else None
    if announced is None:
        return [f"the manifest announces no usable plugin version: {announced_text!r}"]

    published: dict[tuple[int, ...], str] = {}
    latest: tuple[int, ...] | None = None
    for release in releases:
        if release.get("draft"):
            continue
        tag = str(release.get("tag_name") or release.get("tagName") or "")
        version = _version(tag)
        if version is None:
            continue
        published[version] = tag
        if not release.get("prerelease") and (latest is None or version > latest):
            latest = version

    if not published:
        return ["no published release was found to check the manifest against"]

    errors: list[str] = []
    if announced not in published:
        errors.append(
            f"the manifest announces {announced_text}, which is not published; "
            "a driver would be offered a download that does not exist"
        )
    if latest is not None and announced < latest:
        errors.append(
            f"the manifest announces {announced_text} but {published[latest]} is the "
            "published latest; copy that release's as-driven-latest.json into the "
            "repository root and commit it"
        )
    return errors


def release_request(
    repository: str = DEFAULT_REPOSITORY, environment: Mapping[str, str] | None = None
) -> urllib.request.Request:
    """The releases listing call, authenticated when a token is in the run.

    Anonymous api.github.com calls share a per-address hourly budget, which a
    shared CI runner exhausts. Actions always has GITHUB_TOKEN, so use it when
    it is there and stay anonymous when it is not.
    """
    environment = os.environ if environment is None else environment
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "as-driven-db",
    }
    token = environment.get("GITHUB_TOKEN") or environment.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(
        f"https://api.github.com/repos/{repository}/releases?per_page=100",
        headers=headers,
    )


def fetch_releases(repository: str = DEFAULT_REPOSITORY) -> list[dict[str, Any]]:
    """Releases from the GitHub API, newest first. Drafts need a token to see."""
    request = release_request(repository)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError) as exception:
        raise UpdateManifestError(
            f"cannot list releases for {repository}: {exception}"
        ) from exception
    if not isinstance(payload, list):
        raise UpdateManifestError(f"unexpected release listing for {repository}")
    return payload
