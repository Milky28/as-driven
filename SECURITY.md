# Security policy

As Driven is a local SimHub plugin. It does not run a service, accept remote
connections, or perform background downloads. A release package is downloaded
only after a manual update check finds one and the driver separately confirms
**Download and install**.

Do not open a public issue for a suspected security vulnerability. Use GitHub's
[private vulnerability-reporting form](https://github.com/Milky28/as-driven/security/advisories/new),
which reaches the maintainer without disclosing the report.

Include the affected plugin or dataset version, the installation source,
reproduction steps, and any relevant file hashes. Do not attach personal
telemetry, contribution drafts, or machine paths unless they are necessary and
have been reviewed.

Only packages and checksums attached to an official project release should be
treated as release artifacts. The automatic installer requires an HTTPS package
address and verifies the downloaded ZIP against the SHA-256 in the HTTPS update
manifest before it runs. Automatic installation is limited to release URLs in
the official `Milky28/as-driven` GitHub repository, even if an advanced user
points the version check at a custom manifest. The published binaries and PowerShell scripts are not
code-signed, so Windows still requests administrator approval.

Security fixes are supported for the newest plugin release and the
current schema-v1 dataset line. Older development builds may be asked to upgrade
before a report is investigated.
