# Security policy

As Driven is a local SimHub plugin. It does not run a
service, accept remote connections, or automatically download data.

Do not open a public issue for a suspected security vulnerability. Use GitHub's
[private vulnerability-reporting form](https://github.com/Milky28/as-driven/security/advisories/new),
which reaches the maintainer without disclosing the report.

Include the affected plugin or dataset version, the installation source,
reproduction steps, and any relevant file hashes. Do not attach personal
telemetry, contribution drafts, or machine paths unless they are necessary and
have been reviewed.

Only packages and checksums attached to an official project release should be
treated as release artifacts. The published binaries and PowerShell scripts
are not code-signed; verify the published SHA-256 checksum before installing.

Security fixes are supported for the newest plugin release and the
current schema-v1 dataset line. Older development builds may be asked to upgrade
before a report is investigated.
