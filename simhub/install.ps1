param(
    [string]$SimHubInstallPath = "C:\Program Files (x86)\SimHub",
    [string]$PackagePath = (Join-Path $PSScriptRoot "dist\AsDriven"),
    [switch]$ReplaceOverlayLayouts
)

$ErrorActionPreference = "Stop"
$packageRoot = [System.IO.Path]::GetFullPath($PackagePath)
$simHubRoot = [System.IO.Path]::GetFullPath($SimHubInstallPath)

if (-not (Test-Path -LiteralPath (Join-Path $packageRoot "AsDriven.Plugin.dll"))) {
    throw "The built As Driven package was not found: $packageRoot"
}
if (-not (Test-Path -LiteralPath (Join-Path $simHubRoot "SimHubWPF.exe"))) {
    throw "The SimHub installation could not be verified: $simHubRoot"
}
$targetExecutable = [System.IO.Path]::GetFullPath((Join-Path $simHubRoot "SimHubWPF.exe"))
$defaultRoot = [System.IO.Path]::GetFullPath("C:\Program Files (x86)\SimHub")
# The running process is asked where it was launched from so a SimHub installed
# somewhere else is not mistaken for this one. That question can fail - an
# elevated or 32-bit process does not always yield a readable MainModule - and
# when it does, the answer for the default location is to assume the worst and
# refuse. Nothing here may throw inside the try: a thrown string surfaces as the
# same RuntimeException a failed lookup does, and catching both together is what
# used to replace this message with a raw .NET path error.
foreach ($process in @(Get-Process -Name "SimHubWPF" -ErrorAction SilentlyContinue)) {
    $runningExecutable = $null
    $lookupFailed = $false
    try { $runningExecutable = [System.IO.Path]::GetFullPath($process.MainModule.FileName) }
    catch { $lookupFailed = $true }

    if ($lookupFailed) {
        if ($simHubRoot.Equals($defaultRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Close SimHub before installing As Driven. (SimHubWPF is running; its location could not be read, so the installation at $simHubRoot is assumed to be the one in use.)"
        }
    }
    elseif ($runningExecutable.Equals($targetExecutable, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Close SimHub before installing As Driven."
    }
}

$backupRoot = Join-Path $env:TEMP ("AsDriven-SimHub-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

function Backup-RelativePath {
    param([string]$RelativePath)

    $source = Join-Path $simHubRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        return
    }
    $target = Join-Path $backupRoot $RelativePath
    New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
}

foreach ($relativePath in @(
    "AsDriven.Plugin.dll",
    "AsDriven.Plugin.pdb",
    "AsDriven.Core.dll",
    "AsDriven.Core.pdb",
    "PluginsData\AsDriven",
    "DashTemplates\As Driven Preflight Overlay",
    "DashTemplates\As Driven Preflight Compact",
    "DashTemplates\As Driven Preflight Glance",
    "DashTemplates\As Driven Preflight Display",
    "DashTemplates\As Driven Verification Drive"
)) {
    Backup-RelativePath $relativePath
}

$installedLayoutDirectory = Join-Path $simHubRoot "OverlayLayouts"
if (Test-Path -LiteralPath $installedLayoutDirectory) {
    foreach ($layout in Get-ChildItem -LiteralPath $installedLayoutDirectory -Filter "As Driven*.olayout") {
        Backup-RelativePath ("OverlayLayouts\" + $layout.Name)
    }
}

foreach ($fileName in @(
    "AsDriven.Plugin.dll",
    "AsDriven.Plugin.pdb",
    "AsDriven.Core.dll",
    "AsDriven.Core.pdb"
)) {
    Copy-Item -LiteralPath (Join-Path $packageRoot $fileName) -Destination $simHubRoot -Force
}
Copy-Item -LiteralPath (Join-Path $packageRoot "PluginsData") -Destination $simHubRoot -Recurse -Force
Copy-Item -LiteralPath (Join-Path $packageRoot "DashTemplates") -Destination $simHubRoot -Recurse -Force

New-Item -ItemType Directory -Path $installedLayoutDirectory -Force | Out-Null
$preservedLayouts = @()
$resizedLayouts = @()
$extendedLayouts = @()
foreach ($sourceLayout in Get-ChildItem -LiteralPath (Join-Path $packageRoot "OverlayLayouts") -Filter "*.olayout") {
    $installedLayout = Join-Path $installedLayoutDirectory $sourceLayout.Name
    if ((Test-Path -LiteralPath $installedLayout) -and -not $ReplaceOverlayLayouts) {
        $preservedLayouts += $sourceLayout.Name
        continue
    }
    Copy-Item -LiteralPath $sourceLayout.FullName -Destination $installedLayout -Force
}

# Version 0.9.6 narrowed the Detailed surface. Version 0.10.3 adds technique
# guidance to Compact and raises its height from 260 to 300. Preserve customized
# positions by keeping each migrated part centered, and leave any already-custom-
# sized part untouched. Version 0.11.0 adds the in-sim verification surface to
# existing layouts without replacing their customized preflight positions. The
# pre-install backup makes these migrations reversible.
if (-not $ReplaceOverlayLayouts) {
    foreach ($layout in Get-ChildItem -LiteralPath $installedLayoutDirectory -Filter "As Driven*.olayout") {
        $payload = Get-Content -LiteralPath $layout.FullName -Raw | ConvertFrom-Json
        $changed = $false
        foreach ($part in $payload.OverlayLayoutParts) {
            if ($part.DashboardName -like "*As Driven Preflight Overlay.djson" -and
                [double]$part.Width -eq 900.0) {
                $center = [double]$part.Left + ([double]$part.Width / 2.0)
                $part.Width = 840.0
                $part.Left = $center - 420.0
                $changed = $true
            }
            if ($part.DashboardName -like "*As Driven Preflight Compact.djson" -and
                [double]$part.Height -eq 260.0) {
                $center = [double]$part.Top + ([double]$part.Height / 2.0)
                $part.Height = 300.0
                $part.Top = $center - 150.0
                $changed = $true
            }
        }
        $verificationPart = $payload.OverlayLayoutParts | Where-Object {
            $_.DashboardName -like "*As Driven Verification Drive.djson"
        } | Select-Object -First 1
        if ($null -eq $verificationPart) {
            $detailedPart = $payload.OverlayLayoutParts | Where-Object {
                $_.DashboardName -like "*As Driven Preflight Overlay.djson"
            } | Select-Object -First 1
            if ($null -ne $detailedPart) {
                $verificationLeft = [double]$detailedPart.Left + ([double]$detailedPart.Width / 2.0) - 350.0
                $verificationTop = [double]$detailedPart.Top + [double]$detailedPart.Height + 10.0
            }
            else {
                $verificationLeft = 610.0
                $verificationTop = 430.0
            }
            $newPart = [pscustomobject]@{
                DashboardName = "DashTemplates\As Driven Verification Drive\As Driven Verification Drive.djson"
                Top = $verificationTop
                Left = $verificationLeft
                Width = 700.0
                Height = 220.0
                Version = 1
                PartId = [Guid]::NewGuid().ToString()
                Placed = $true
                Transparent = $true
            }
            $payload.OverlayLayoutParts = @($payload.OverlayLayoutParts) + $newPart
            $extendedLayouts += $layout.Name
            $changed = $true
        }
        if ($changed) {
            $json = $payload | ConvertTo-Json -Depth 20
            [System.IO.File]::WriteAllText(
                $layout.FullName,
                $json,
                (New-Object System.Text.UTF8Encoding($false)))
            $resizedLayouts += $layout.Name
        }
    }
}

Write-Host "Installed As Driven from: $packageRoot"
Write-Host "Rollback backup: $backupRoot"
if ($preservedLayouts.Count -gt 0) {
    Write-Host ("Preserved customized overlay layouts: " + ($preservedLayouts -join ", "))
}
if ($resizedLayouts.Count -gt 0) {
    Write-Host ("Centered and resized updated overlay surfaces in: " + ($resizedLayouts -join ", "))
}
if ($extendedLayouts.Count -gt 0) {
    Write-Host ("Added the guided verification surface to: " + ($extendedLayouts -join ", "))
}
