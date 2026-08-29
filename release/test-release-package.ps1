param(
    [Parameter(Mandatory = $true)]
    [string]$PackagePath
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$packageFile = [System.IO.Path]::GetFullPath($PackagePath)
$checksumFile = "$packageFile.sha256"
if (-not (Test-Path -LiteralPath $packageFile) `
    -or -not (Test-Path -LiteralPath $checksumFile)) {
    throw "The release ZIP and adjacent checksum are required."
}
$expectedHash = ((Get-Content -LiteralPath $checksumFile -Raw).Trim() -split '\s+')[0]
$actualHash = (Get-FileHash -LiteralPath $packageFile -Algorithm SHA256).Hash.ToLowerInvariant()
if ($expectedHash -ne $actualHash) {
    throw "The release ZIP checksum does not match."
}

$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    "ACpkg-" + [Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $testRoot | Out-Null
try {
    Expand-Archive -LiteralPath $packageFile -DestinationPath $testRoot
    $roots = @(Get-ChildItem -LiteralPath $testRoot -Directory)
    if ($roots.Count -ne 1) {
        throw "The release ZIP must contain exactly one root directory."
    }
    $packageRoot = $roots[0].FullName
    $releaseManifestPath = Join-Path $packageRoot "release-manifest.json"
    $fileManifestPath = Join-Path $packageRoot "file-manifest.json"
    if (-not (Test-Path -LiteralPath $releaseManifestPath) `
        -or -not (Test-Path -LiteralPath $fileManifestPath)) {
        throw "The release package manifests are missing."
    }
    $releaseManifest = Get-Content -LiteralPath $releaseManifestPath -Raw | ConvertFrom-Json
    if ([string]$releaseManifest.package_format -ne "as-driven-simhub" `
        -or [string]$releaseManifest.plugin_version -notmatch '^\d+\.\d+\.\d+$' `
        -or [string]$releaseManifest.bundled_dataset_version -notmatch '^\d+\.\d+\.\d+$') {
        throw "The release manifest is invalid."
    }

    $fileEntries = Get-Content -LiteralPath $fileManifestPath -Raw | ConvertFrom-Json
    foreach ($entry in $fileEntries) {
        $relativePath = [string]$entry.path
        if ([string]::IsNullOrWhiteSpace($relativePath) `
            -or [System.IO.Path]::IsPathRooted($relativePath) `
            -or $relativePath.Split('/') -contains '..') {
            throw "The file manifest contains an unsafe path: $relativePath"
        }
        $file = Join-Path $packageRoot $relativePath.Replace('/', '\')
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "The release package is missing: $relativePath"
        }
        if ((Get-Item -LiteralPath $file).Length -ne [long]$entry.bytes) {
            throw "The release package file size does not match: $relativePath"
        }
        $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($hash -ne [string]$entry.sha256) {
            throw "The release package file hash does not match: $relativePath"
        }
    }

    $manifestPaths = @($fileEntries | ForEach-Object { [string]$_.path } | Sort-Object)
    $actualPaths = @(Get-ChildItem -LiteralPath $packageRoot -File -Recurse |
        ForEach-Object {
            $_.FullName.Substring($packageRoot.Length + 1).Replace('\', '/')
        } |
        Where-Object { $_ -ne "file-manifest.json" } |
        Sort-Object)
    if (Compare-Object $manifestPaths $actualPaths -SyncWindow 0) {
        throw "The release package contains a file missing from its manifest."
    }

    foreach ($requiredPath in @(
        "START HERE.txt",
        "Install As Driven.cmd",
        "Uninstall As Driven.cmd"
    )) {
        if (-not (Test-Path -LiteralPath (Join-Path $packageRoot $requiredPath) -PathType Leaf)) {
            throw "The release package is missing its user entry point: $requiredPath"
        }
    }
    if (Get-ChildItem -LiteralPath $packageRoot -File -Recurse -Filter "*.pdb") {
        throw "The release package contains private development symbols."
    }
    foreach ($privateDocument in @("AGENTS.md", "CLAUDE.md")) {
        if (Test-Path -LiteralPath (Join-Path $packageRoot $privateDocument)) {
            throw "The release package contains an internal handoff document: $privateDocument"
        }
    }
    foreach ($file in Get-ChildItem -LiteralPath $packageRoot -File -Recurse) {
        $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
        $ascii = [System.Text.Encoding]::ASCII.GetString($bytes)
        $unicode = [System.Text.Encoding]::Unicode.GetString($bytes)
        if ($ascii -match '(?i)[a-z]:\\users\\|/users/' `
            -or $unicode -match '(?i)[a-z]:\\users\\|/users/') {
            $relativePath = $file.FullName.Substring($packageRoot.Length + 1)
            throw "The release package exposes a local user path: $relativePath"
        }
    }

    $pluginPackage = Join-Path $packageRoot "simhub\dist\AsDriven"
    foreach ($requiredPath in @(
        "AsDriven.Plugin.dll",
        "AsDriven.Core.dll",
        "PluginsData\AsDriven\Database\data\v1\index.json",
        "DashTemplates",
        "OverlayLayouts"
    )) {
        if (-not (Test-Path -LiteralPath (Join-Path $pluginPackage $requiredPath))) {
            throw "The extracted SimHub package is incomplete: $requiredPath"
        }
    }
    & (Join-Path $repositoryRoot "simhub\test-install.ps1") -PackagePath $pluginPackage

    Write-Host "PASS: release ZIP privacy, checksum, manifests, contents, and extracted install"
}
finally {
    if (Test-Path -LiteralPath $testRoot) {
        Remove-Item -LiteralPath $testRoot -Recurse -Force
    }
}
