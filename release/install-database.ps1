param(
    [string]$PackagePath = "",
    [string]$SimHubInstallPath = "C:\Program Files (x86)\SimHub",
    [string]$BackupDirectory = "",
    [switch]$AllowDowngrade
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path $PSScriptRoot -Parent

function Resolve-DefaultPackage {
    $releaseDirectory = Join-Path $repositoryRoot "dist\database"
    $packages = @(Get-ChildItem -LiteralPath $releaseDirectory -File -Filter "authentic-controls-db-*.zip" |
        ForEach-Object {
            $versionText = $_.BaseName.Substring("authentic-controls-db-".Length)
            $parsedVersion = $null
            if ([Version]::TryParse($versionText, [ref]$parsedVersion)) {
                [pscustomobject]@{ File = $_; Version = $parsedVersion }
            }
        } | Sort-Object Version -Descending)
    if ($packages.Count -eq 0) {
        throw "No database release package was found under: $releaseDirectory"
    }
    return $packages[0].File.FullName
}

function Assert-ChildPath {
    param([string]$Parent, [string]$Candidate, [string]$Description)

    $resolvedParent = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
    $resolvedCandidate = [System.IO.Path]::GetFullPath($Candidate)
    if (-not $resolvedCandidate.StartsWith(
        $resolvedParent,
        [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Description is outside its required parent directory: $resolvedCandidate"
    }
}

function Remove-VerifiedTree {
    param([string]$Parent, [string]$Target)

    if (-not (Test-Path -LiteralPath $Target)) {
        return
    }
    Assert-ChildPath $Parent $Target "Removal target"
    Remove-Item -LiteralPath $Target -Recurse -Force
}

if ([string]::IsNullOrWhiteSpace($PackagePath)) {
    $PackagePath = Resolve-DefaultPackage
}
$packageFile = [System.IO.Path]::GetFullPath($PackagePath)
$simHubRoot = [System.IO.Path]::GetFullPath($SimHubInstallPath)
if (-not (Test-Path -LiteralPath $packageFile -PathType Leaf)) {
    throw "The database release package was not found: $packageFile"
}
if ([System.IO.Path]::GetExtension($packageFile) -ne ".zip") {
    throw "The database release package must be a ZIP file: $packageFile"
}
if (-not (Test-Path -LiteralPath (Join-Path $simHubRoot "SimHubWPF.exe") -PathType Leaf)) {
    throw "The SimHub installation could not be verified: $simHubRoot"
}

$checksumPath = "$packageFile.sha256"
if (Test-Path -LiteralPath $checksumPath) {
    $checksumText = (Get-Content -LiteralPath $checksumPath -Raw).Trim()
    if ($checksumText -notmatch '^([0-9a-fA-F]{64})\s+') {
        throw "The package checksum file is malformed: $checksumPath"
    }
    $expectedPackageHash = $Matches[1].ToLowerInvariant()
    $actualPackageHash = (Get-FileHash -LiteralPath $packageFile -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualPackageHash -ne $expectedPackageHash) {
        throw "The database ZIP checksum does not match: $packageFile"
    }
}

$extractionRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    "AuthenticControlsDatabaseInstall-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $extractionRoot | Out-Null

$authenticControlsRoot = Join-Path $simHubRoot "PluginsData\AuthenticControls"
$databaseRoot = Join-Path $authenticControlsRoot "Database"
$stagingRoot = Join-Path $authenticControlsRoot (
    ".Database-staging-" + [Guid]::NewGuid().ToString("N"))
$previousRoot = Join-Path $authenticControlsRoot (
    ".Database-previous-" + [Guid]::NewGuid().ToString("N"))
if ([string]::IsNullOrWhiteSpace($BackupDirectory)) {
    $backupRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
        "AuthenticControls-Database-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss") +
        "-" + [Guid]::NewGuid().ToString("N").Substring(0, 8))
}
else {
    $backupRoot = [System.IO.Path]::GetFullPath($BackupDirectory)
}
$authenticControlsPrefix = [System.IO.Path]::GetFullPath($authenticControlsRoot).TrimEnd('\') + '\'
if ($backupRoot.StartsWith(
    $authenticControlsPrefix,
    [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The rollback backup must be outside the installed Authentic Controls directory."
}

try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($packageFile)
    try {
        if ($archive.Entries.Count -gt 10000) {
            throw "The database package contains too many files."
        }
        [long]$expandedBytes = 0
        foreach ($entry in $archive.Entries) {
            $expandedBytes += [long]$entry.Length
            if ($expandedBytes -gt 268435456) {
                throw "The expanded database package exceeds the 256 MiB safety limit."
            }
            $entryPath = $entry.FullName.Replace('/', '\')
            if ($entryPath.Contains(':') -or
                [System.IO.Path]::IsPathRooted($entryPath) -or
                $entryPath.Split('\') -contains '..') {
                throw "The database package contains an unsafe path: $($entry.FullName)"
            }
        }
    }
    finally {
        $archive.Dispose()
    }

    Expand-Archive -LiteralPath $packageFile -DestinationPath $extractionRoot
    $packageRoots = @(Get-ChildItem -LiteralPath $extractionRoot -Directory)
    if ($packageRoots.Count -ne 1 -or $packageRoots[0].Name -notlike "authentic-controls-db-*") {
        throw "The database package must contain exactly one authentic-controls-db-* root directory."
    }
    $expandedPackageRoot = $packageRoots[0].FullName
    $manifestPath = Join-Path $expandedPackageRoot "release-manifest.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "The database package does not contain release-manifest.json."
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.package_format -ne "authentic-controls-database" -or
        $manifest.package_format_version -ne "1.0.0") {
        throw "The database package format is not supported."
    }
    if ([int]$manifest.schema_major -ne 1) {
        throw "This installer supports schema major 1; package requires $($manifest.schema_major)."
    }
    if ([string]$manifest.dataset_version -notmatch '^\d+\.\d+\.\d+$') {
        throw "The release manifest contains an invalid dataset version."
    }

    $expectedFiles = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($file in $manifest.files) {
        $relativePath = ([string]$file.path).Replace('/', '\')
        if ($relativePath.Contains(':') -or
            [System.IO.Path]::IsPathRooted($relativePath) -or
            $relativePath.Split('\') -contains '..') {
            throw "The release manifest contains an unsafe path: $($file.path)"
        }
        if (-not $expectedFiles.Add($relativePath)) {
            throw "The release manifest repeats a file: $($file.path)"
        }
        $payloadPath = Join-Path $expandedPackageRoot $relativePath
        Assert-ChildPath $expandedPackageRoot $payloadPath "Manifest payload"
        if (-not (Test-Path -LiteralPath $payloadPath -PathType Leaf)) {
            throw "A file listed in the release manifest is missing: $($file.path)"
        }
        $payloadItem = Get-Item -LiteralPath $payloadPath
        if ($payloadItem.Length -ne [long]$file.bytes) {
            throw "A packaged file has the wrong size: $($file.path)"
        }
        $payloadHash = (Get-FileHash -LiteralPath $payloadPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($payloadHash -ne ([string]$file.sha256).ToLowerInvariant()) {
            throw "A packaged file failed its SHA-256 check: $($file.path)"
        }
    }
    $actualFiles = @(Get-ChildItem -LiteralPath $expandedPackageRoot -File -Recurse |
        ForEach-Object { $_.FullName.Substring($expandedPackageRoot.Length + 1) })
    foreach ($relativePath in $actualFiles) {
        if ($relativePath -ne "release-manifest.json" -and -not $expectedFiles.Contains($relativePath)) {
            throw "The database package contains an unlisted file: $relativePath"
        }
    }

    $newIndexPath = Join-Path $expandedPackageRoot "data\v1\index.json"
    $newIndex = Get-Content -LiteralPath $newIndexPath -Raw | ConvertFrom-Json
    $newVersion = [string]$newIndex.dataset_version
    if ($newVersion -ne [string]$manifest.dataset_version) {
        throw "The dataset index version does not match the release manifest."
    }

    $currentVersion = $null
    $currentIndexPath = Join-Path $databaseRoot "data\v1\index.json"
    if (Test-Path -LiteralPath $currentIndexPath -PathType Leaf) {
        $currentIndex = Get-Content -LiteralPath $currentIndexPath -Raw | ConvertFrom-Json
        $currentVersion = [string]$currentIndex.dataset_version
        if (-not $AllowDowngrade -and
            [Version]$newVersion -lt [Version]$currentVersion) {
            throw "Refusing to downgrade dataset $currentVersion to $newVersion. Use -AllowDowngrade to override."
        }
    }

    New-Item -ItemType Directory -Path $authenticControlsRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $stagingRoot | Out-Null
    Get-ChildItem -LiteralPath $expandedPackageRoot -Force |
        Copy-Item -Destination $stagingRoot -Recurse -Force

    if (Test-Path -LiteralPath $backupRoot) {
        throw "Refusing to overwrite an existing rollback backup: $backupRoot"
    }
    New-Item -ItemType Directory -Path $backupRoot | Out-Null
    if (Test-Path -LiteralPath $databaseRoot) {
        Copy-Item -LiteralPath $databaseRoot -Destination (Join-Path $backupRoot "Database") -Recurse -Force
        Move-Item -LiteralPath $databaseRoot -Destination $previousRoot
    }

    try {
        Move-Item -LiteralPath $stagingRoot -Destination $databaseRoot
        $installedIndex = Get-Content -LiteralPath (Join-Path $databaseRoot "data\v1\index.json") -Raw |
            ConvertFrom-Json
        if ([string]$installedIndex.dataset_version -ne $newVersion) {
            throw "Post-install validation read an unexpected dataset version."
        }
    }
    catch {
        Remove-VerifiedTree $authenticControlsRoot $databaseRoot
        if (Test-Path -LiteralPath $previousRoot) {
            Move-Item -LiteralPath $previousRoot -Destination $databaseRoot
        }
        throw
    }

    Remove-VerifiedTree $authenticControlsRoot $previousRoot
    Write-Host "Installed Authentic Controls dataset $newVersion only."
    if ($null -ne $currentVersion) {
        Write-Host "Previous dataset: $currentVersion"
    }
    Write-Host "Installed database: $databaseRoot"
    Write-Host "Rollback backup: $backupRoot"
    if (Get-Process -Name "SimHubWPF" -ErrorAction SilentlyContinue) {
        Write-Host "SimHub is running. Use Authentic Controls > Refresh database to load the update."
    }
}
finally {
    Remove-VerifiedTree ([System.IO.Path]::GetTempPath()) $extractionRoot
    Remove-VerifiedTree $authenticControlsRoot $stagingRoot
}
