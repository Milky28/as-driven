$ErrorActionPreference = "Stop"
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    "AuthenticControlsUninstallTest-" + [Guid]::NewGuid().ToString("N"))
$resolvedTestRoot = [System.IO.Path]::GetFullPath($testRoot)
$tempParent = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\') + '\'
if (-not $resolvedTestRoot.StartsWith($tempParent, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to create an uninstaller test outside the temporary directory."
}

New-Item -ItemType Directory -Path $testRoot | Out-Null
try {
    $simHubRoot = Join-Path $testRoot "SimHub"
    $backupRoot = Join-Path $testRoot "Backup"
    New-Item -ItemType Directory -Path $simHubRoot | Out-Null
    New-Item -ItemType File -Path (Join-Path $simHubRoot "SimHubWPF.exe") | Out-Null
    foreach ($relativePath in @(
        "AuthenticControls.Plugin.dll",
        "AuthenticControls.Plugin.pdb",
        "AuthenticControls.Core.dll",
        "AuthenticControls.Core.pdb"
    )) {
        Set-Content -LiteralPath (Join-Path $simHubRoot $relativePath) -Value "test" -Encoding ASCII
    }
    $dashboard = Join-Path $simHubRoot "DashTemplates\Authentic Controls Preflight Overlay"
    New-Item -ItemType Directory -Path $dashboard -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $dashboard "test.djson") -Value "{}" -Encoding ASCII
    $data = Join-Path $simHubRoot "PluginsData\AuthenticControls\Database\data\v1"
    New-Item -ItemType Directory -Path $data -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $data "index.json") -Value "data-sentinel" -Encoding ASCII
    $layouts = Join-Path $simHubRoot "OverlayLayouts"
    New-Item -ItemType Directory -Path $layouts -Force | Out-Null
    $layout = Join-Path $layouts "Authentic Controls.olayout"
    Set-Content -LiteralPath $layout -Value "layout-sentinel" -Encoding ASCII

    & (Join-Path $PSScriptRoot "uninstall.ps1") `
        -SimHubInstallPath $simHubRoot `
        -BackupDirectory $backupRoot

    if (Test-Path -LiteralPath (Join-Path $simHubRoot "AuthenticControls.Plugin.dll")) {
        throw "The uninstaller left the plugin binary installed."
    }
    if (Test-Path -LiteralPath $dashboard) {
        throw "The uninstaller left a packaged dashboard installed."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $data "index.json"))) {
        throw "The uninstaller removed the installed database."
    }
    if (-not (Test-Path -LiteralPath $layout)) {
        throw "The uninstaller removed a customized overlay layout by default."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $backupRoot "AuthenticControls.Plugin.dll")) `
        -or -not (Test-Path -LiteralPath (
            Join-Path $backupRoot "DashTemplates\Authentic Controls Preflight Overlay\test.djson"))) {
        throw "The uninstaller did not back up the removed files."
    }

    Write-Host "PASS: uninstaller backup, removal, and user-data preservation"
}
finally {
    if (Test-Path -LiteralPath $resolvedTestRoot) {
        Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force
    }
}
