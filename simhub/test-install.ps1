param(
    [string]$PackagePath = (Join-Path $PSScriptRoot "dist\AuthenticControls")
)

$ErrorActionPreference = "Stop"
$packageRoot = [System.IO.Path]::GetFullPath($PackagePath)
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    "AuthenticControlsInstallTest-" + [Guid]::NewGuid().ToString("N"))
$resolvedTestRoot = [System.IO.Path]::GetFullPath($testRoot)
$tempParent = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\') + '\'
if (-not $resolvedTestRoot.StartsWith($tempParent, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to create an installer test outside the temporary directory."
}

New-Item -ItemType Directory -Path $testRoot | Out-Null
try {
    $simHubRoot = Join-Path $testRoot "SimHub"
    New-Item -ItemType Directory -Path $simHubRoot | Out-Null
    New-Item -ItemType File -Path (Join-Path $simHubRoot "SimHubWPF.exe") | Out-Null
    Set-Content -LiteralPath (Join-Path $simHubRoot "AuthenticControls.Plugin.dll") `
        -Value "old-plugin" -Encoding ASCII

    $layoutDirectory = Join-Path $simHubRoot "OverlayLayouts"
    New-Item -ItemType Directory -Path $layoutDirectory -Force | Out-Null
    $sourceLayout = Get-ChildItem -LiteralPath (Join-Path $packageRoot "OverlayLayouts") `
        -File -Filter "Authentic Controls.olayout" | Select-Object -First 1
    if ($null -eq $sourceLayout) {
        throw "The package has no default Authentic Controls layout."
    }
    $installedLayout = Join-Path $layoutDirectory $sourceLayout.Name
    Copy-Item -LiteralPath $sourceLayout.FullName -Destination $installedLayout
    $layoutHash = (Get-FileHash -LiteralPath $installedLayout -Algorithm SHA256).Hash

    & (Join-Path $PSScriptRoot "install.ps1") `
        -PackagePath $packageRoot `
        -SimHubInstallPath $simHubRoot

    $installedPlugin = Join-Path $simHubRoot "AuthenticControls.Plugin.dll"
    if ((Get-FileHash -LiteralPath $installedPlugin -Algorithm SHA256).Hash -ne
        (Get-FileHash -LiteralPath (Join-Path $packageRoot "AuthenticControls.Plugin.dll") -Algorithm SHA256).Hash) {
        throw "The installer did not copy the packaged plugin binary."
    }
    if (-not (Test-Path -LiteralPath (
        Join-Path $simHubRoot "PluginsData\AuthenticControls\Database\data\v1\index.json"))) {
        throw "The installer did not copy the bundled database."
    }
    if (-not (Test-Path -LiteralPath (
        Join-Path $simHubRoot "DashTemplates\Authentic Controls Preflight Overlay"))) {
        throw "The installer did not copy the packaged dashboards."
    }
    if ((Get-FileHash -LiteralPath $installedLayout -Algorithm SHA256).Hash -ne $layoutHash) {
        throw "The installer replaced or modified an existing customized layout."
    }

    Write-Host "PASS: plugin install, bundled database, dashboards, backup, and layout preservation"
}
finally {
    if (Test-Path -LiteralPath $resolvedTestRoot) {
        Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force
    }
}
