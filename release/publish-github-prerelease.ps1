param(
    [string]$ArtifactsDirectory = "",
    [string]$Repository = "",
    [switch]$Approve
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path $PSScriptRoot -Parent
if ([string]::IsNullOrWhiteSpace($ArtifactsDirectory)) {
    $ArtifactsDirectory = Join-Path $repositoryRoot "dist\early-access"
}
$artifactRoot = [System.IO.Path]::GetFullPath($ArtifactsDirectory)
$metadataPath = Join-Path $artifactRoot "early-access-release.json"
if (-not (Test-Path -LiteralPath $metadataPath -PathType Leaf)) {
    throw "Build the early-access release before publishing: $metadataPath"
}

$metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
$pluginVersion = [string]$metadata.plugin_version
$datasetVersion = [string]$metadata.dataset_version
if ($pluginVersion -notmatch '^\d+\.\d+\.\d+$' `
    -or $datasetVersion -notmatch '^\d+\.\d+\.\d+$') {
    throw "The release metadata contains an invalid plugin or dataset version."
}

function Resolve-Artifact {
    param([string]$FileName)

    if ([string]::IsNullOrWhiteSpace($FileName) `
        -or [System.IO.Path]::GetFileName($FileName) -ne $FileName) {
        throw "Release metadata contains an unsafe artifact name: $FileName"
    }
    $path = Join-Path $artifactRoot $FileName
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "A required release artifact is missing: $path"
    }
    return $path
}

function Read-AdjacentChecksum {
    param([string]$PackagePath)

    $checksumPath = "$PackagePath.sha256"
    if (-not (Test-Path -LiteralPath $checksumPath -PathType Leaf)) {
        throw "A required checksum is missing: $checksumPath"
    }
    $value = ((Get-Content -LiteralPath $checksumPath -Raw).Trim() -split '\s+')[0]
    if ($value -notmatch '^[0-9a-fA-F]{64}$') {
        throw "A release checksum is malformed: $checksumPath"
    }
    return $value.ToLowerInvariant()
}

$pluginPackage = Resolve-Artifact ([string]$metadata.plugin_package)
$databasePackage = Resolve-Artifact ([string]$metadata.database_package)
$releaseNotes = Resolve-Artifact ([string]$metadata.release_notes)
$pluginHash = (Get-FileHash -LiteralPath $pluginPackage -Algorithm SHA256).Hash.ToLowerInvariant()
$databaseHash = (Get-FileHash -LiteralPath $databasePackage -Algorithm SHA256).Hash.ToLowerInvariant()
if ($pluginHash -ne [string]$metadata.plugin_sha256 `
    -or $pluginHash -ne (Read-AdjacentChecksum $pluginPackage)) {
    throw "The SimHub package does not match its release metadata and checksum."
}
if ($databaseHash -ne [string]$metadata.database_sha256 `
    -or $databaseHash -ne (Read-AdjacentChecksum $databasePackage)) {
    throw "The database package does not match its release metadata and checksum."
}
if ((Get-Content -LiteralPath $releaseNotes -Raw) -match '\{\{[A-Z_]+\}\}') {
    throw "The generated release notes still contain an unresolved template value."
}

& powershell -NoProfile -ExecutionPolicy Bypass -File `
    (Join-Path $PSScriptRoot "test-early-access-package.ps1") `
    -PackagePath $pluginPackage
if ($LASTEXITCODE -ne 0) {
    throw "The SimHub release package failed its final verification."
}
& powershell -NoProfile -ExecutionPolicy Bypass -File `
    (Join-Path $PSScriptRoot "test-install-database.ps1") `
    -PackagePath $databasePackage
if ($LASTEXITCODE -ne 0) {
    throw "The database release package failed its final verification."
}

if ([string]::IsNullOrWhiteSpace($Repository)) {
    $remote = (& git -C $repositoryRoot remote get-url origin).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "The GitHub repository could not be derived from the origin remote."
    }
    $remote = $remote -replace '\.git$', ''
    if ($remote -notmatch 'github\.com[/:]([^/]+/[^/]+)$') {
        throw "The origin remote is not a GitHub repository: $remote"
    }
    $Repository = $Matches[1]
}

$tag = "v$pluginVersion"
$title = "As Driven $pluginVersion early access"
$assetPaths = @(
    $pluginPackage,
    "$pluginPackage.sha256",
    $databasePackage,
    "$databasePackage.sha256",
    $metadataPath,
    $releaseNotes
)

Write-Host "Verified draft prerelease:"
Write-Host "  Repository: $Repository"
Write-Host "  Tag: $tag"
Write-Host "  Title: $title"
Write-Host "  Plugin: $([System.IO.Path]::GetFileName($pluginPackage))"
Write-Host "  Database: $([System.IO.Path]::GetFileName($databasePackage))"

if (-not $Approve) {
    Write-Host "No GitHub changes were made. Rerun with -Approve to create the draft prerelease."
    exit 0
}

$branch = (& git -C $repositoryRoot branch --show-current).Trim()
if ($branch -ne "main") {
    throw "Public prereleases must be created from main, not $branch."
}
$trackedChanges = @(& git -C $repositoryRoot status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0 -or $trackedChanges.Count -ne 0) {
    throw "Tracked repository changes must be committed before creating a prerelease."
}
$counts = ((& git -C $repositoryRoot rev-list --left-right --count '@{upstream}...HEAD').Trim() `
    -split '\s+')
if ($LASTEXITCODE -ne 0 -or $counts.Count -ne 2 `
    -or [int]$counts[0] -ne 0 -or [int]$counts[1] -ne 0) {
    throw "The main branch must be synchronized with its upstream before creating a prerelease."
}
if ($null -eq (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI is required. Install gh and run gh auth login."
}
& gh auth status -h github.com
if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI is not authenticated. Run gh auth login -h github.com."
}
& gh release view $tag --repo $Repository *> $null
if ($LASTEXITCODE -eq 0) {
    throw "A GitHub release already exists for $tag."
}

$commit = (& git -C $repositoryRoot rev-parse HEAD).Trim()
$arguments = @("release", "create", $tag) + $assetPaths + @(
    "--repo", $Repository,
    "--target", $commit,
    "--title", $title,
    "--notes-file", $releaseNotes,
    "--draft",
    "--prerelease"
)
& gh @arguments
if ($LASTEXITCODE -ne 0) {
    throw "GitHub did not create the draft prerelease."
}
Write-Host "Created draft prerelease $tag. Review it on GitHub before publishing."
