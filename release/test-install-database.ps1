param(
    [Parameter(Mandatory = $true)]
    [string]$PackagePath
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$packageFile = [System.IO.Path]::GetFullPath($PackagePath)
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    "AuthenticControlsDatabaseInstallerTest-" + [Guid]::NewGuid().ToString("N"))
$tempParent = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\') + '\'
$resolvedTestRoot = [System.IO.Path]::GetFullPath($testRoot)
if (-not $resolvedTestRoot.StartsWith(
    $tempParent,
    [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to create an installer test outside the temporary directory."
}

New-Item -ItemType Directory -Path $testRoot | Out-Null
try {
    $simHubRoot = Join-Path $testRoot "SimHub"
    New-Item -ItemType Directory -Path $simHubRoot | Out-Null
    New-Item -ItemType File -Path (Join-Path $simHubRoot "SimHubWPF.exe") | Out-Null
    $pluginPath = Join-Path $simHubRoot "AuthenticControls.Plugin.dll"
    Set-Content -LiteralPath $pluginPath -Value "plugin-sentinel" -Encoding ASCII
    $pluginHash = (Get-FileHash -LiteralPath $pluginPath -Algorithm SHA256).Hash

    $oldDataRoot = Join-Path $simHubRoot "PluginsData\AuthenticControls\Database\data\v1"
    New-Item -ItemType Directory -Path $oldDataRoot -Force | Out-Null
    '{"dataset_version":"0.3.12"}' |
        Set-Content -LiteralPath (Join-Path $oldDataRoot "index.json") -Encoding UTF8
    $backupRoot = Join-Path $testRoot "Rollback"

    & (Join-Path $PSScriptRoot "install-database.ps1") `
        -PackagePath $packageFile `
        -SimHubInstallPath $simHubRoot `
        -BackupDirectory $backupRoot

    $installedIndexPath = Join-Path $simHubRoot (
        "PluginsData\AuthenticControls\Database\data\v1\index.json")
    $installedIndex = Get-Content -LiteralPath $installedIndexPath -Raw | ConvertFrom-Json
    $packageRootName = [System.IO.Path]::GetFileNameWithoutExtension($packageFile)
    $expectedVersion = $packageRootName.Substring("authentic-controls-db-".Length)
    if ([string]$installedIndex.dataset_version -ne $expectedVersion) {
        throw "Installer test expected dataset $expectedVersion but found $($installedIndex.dataset_version)."
    }
    if ((Get-FileHash -LiteralPath $pluginPath -Algorithm SHA256).Hash -ne $pluginHash) {
        throw "The database-only installer modified a plugin binary."
    }
    $backupIndex = Get-Content -LiteralPath (
        Join-Path $backupRoot "Database\data\v1\index.json") -Raw | ConvertFrom-Json
    if ([string]$backupIndex.dataset_version -ne "0.3.12") {
        throw "The database-only installer did not preserve the previous dataset backup."
    }
    if (Get-ChildItem -LiteralPath (Join-Path $simHubRoot "PluginsData\AuthenticControls") `
        -Directory -Filter ".Database-previous-*") {
        throw "The database-only installer left a previous-directory swap artifact behind."
    }

    $badPackage = Join-Path $testRoot "authentic-controls-db-corrupt-checksum.zip"
    Copy-Item -LiteralPath $packageFile -Destination $badPackage
    ("0" * 64) + "  " + [System.IO.Path]::GetFileName($badPackage) |
        Set-Content -LiteralPath "$badPackage.sha256" -Encoding ASCII
    $checksumRejected = $false
    try {
        & (Join-Path $PSScriptRoot "install-database.ps1") `
            -PackagePath $badPackage `
            -SimHubInstallPath $simHubRoot `
            -BackupDirectory (Join-Path $testRoot "RejectedBackup")
    }
    catch {
        $checksumRejected = $_.Exception.Message -like "*checksum does not match*"
    }
    if (-not $checksumRejected) {
        throw "The database-only installer did not reject a bad ZIP checksum."
    }
    $stillInstalled = Get-Content -LiteralPath $installedIndexPath -Raw | ConvertFrom-Json
    if ([string]$stillInstalled.dataset_version -ne $expectedVersion) {
        throw "A rejected package changed the installed dataset."
    }

    Write-Host "PASS: database-only install, rollback backup, plugin preservation, and checksum rejection"
}
finally {
    if (Test-Path -LiteralPath $resolvedTestRoot) {
        Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force
    }
}
