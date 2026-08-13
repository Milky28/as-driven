param(
    [string]$OutputDirectory = "",
    [string]$SimHubInstallPath = "C:\Program Files (x86)\SimHub"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path $PSScriptRoot -Parent
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $repositoryRoot "dist\early-access"
}
$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null

Push-Location $repositoryRoot
try {
    & python -m as_driven_db validate
    if ($LASTEXITCODE -ne 0) {
        throw "Database validation failed."
    }
    & python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Database tests failed."
    }
}
finally {
    Pop-Location
}

& powershell -NoProfile -ExecutionPolicy Bypass -File `
    (Join-Path $repositoryRoot "simhub\build.ps1") `
    -Configuration Release `
    -SimHubInstallPath $SimHubInstallPath
if ($LASTEXITCODE -ne 0) {
    throw "The SimHub release build failed."
}

& powershell -NoProfile -ExecutionPolicy Bypass -File `
    (Join-Path $repositoryRoot "simhub\test-uninstall.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "The SimHub uninstaller test failed."
}

& powershell -NoProfile -ExecutionPolicy Bypass -File `
    (Join-Path $PSScriptRoot "build-database.ps1") `
    -OutputDirectory $outputRoot `
    -SkipChecks
if ($LASTEXITCODE -ne 0) {
    throw "The database release build failed."
}

$pluginAssembly = [System.Reflection.AssemblyName]::GetAssemblyName(
    (Join-Path $repositoryRoot "simhub\dist\AsDriven\AsDriven.Plugin.dll"))
$coreAssembly = [System.Reflection.AssemblyName]::GetAssemblyName(
    (Join-Path $repositoryRoot "simhub\dist\AsDriven\AsDriven.Core.dll"))
$pluginVersion = $pluginAssembly.Version.ToString(3)
$coreVersion = $coreAssembly.Version.ToString(3)
if ($pluginVersion -ne $coreVersion) {
    throw "Plugin $pluginVersion and core $coreVersion release versions do not match."
}
$datasetIndex = Get-Content -LiteralPath (
    Join-Path $repositoryRoot "data\v1\index.json") -Raw | ConvertFrom-Json
$datasetVersion = [string]$datasetIndex.dataset_version
$recordCount = @($datasetIndex.records).Count

$staging = Join-Path ([System.IO.Path]::GetTempPath()) (
    "ACea-" + [Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $staging | Out-Null
try {
    $releaseName = "as-driven-simhub-$pluginVersion-early-access"
    # Keep temporary paths short: Dash Studio filenames are descriptive and
    # older PowerShell/.NET Framework file APIs still enforce MAX_PATH.
    $packageRoot = Join-Path $staging "AsDriven"
    New-Item -ItemType Directory -Path (Join-Path $packageRoot "simhub\dist") -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $repositoryRoot "simhub\dist\AsDriven") `
        -Destination (Join-Path $packageRoot "simhub\dist") -Recurse
    foreach ($script in @("install.ps1", "uninstall.ps1")) {
        Copy-Item -LiteralPath (Join-Path $repositoryRoot "simhub\$script") `
            -Destination (Join-Path $packageRoot "simhub")
    }
    foreach ($document in @(
        "EARLY_ACCESS.md",
        "PRIVACY.md",
        "SECURITY.md",
        "CHANGELOG.md",
        "LICENSE",
        "DATA_LICENSE.md"
    )) {
        Copy-Item -LiteralPath (Join-Path $repositoryRoot $document) -Destination $packageRoot
    }

    $manifest = [ordered]@{
        package_format = "as-driven-simhub"
        package_format_version = "1.0.0"
        release_channel = "early-access"
        plugin_version = $pluginVersion
        core_version = $coreVersion
        bundled_dataset_version = $datasetVersion
        bundled_record_count = $recordCount
        tested_simhub_version = "9.11.22"
        tested_simulator = "Automobilista 2"
        tested_simulator_version = "1.6.9.91"
        generated_at = [DateTime]::UtcNow.ToString("o")
    }
    $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (
        Join-Path $packageRoot "release-manifest.json") -Encoding UTF8

    $fileManifest = Get-ChildItem -LiteralPath $packageRoot -File -Recurse |
        Sort-Object FullName |
        ForEach-Object {
            [ordered]@{
                path = $_.FullName.Substring($packageRoot.Length + 1).Replace('\', '/')
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
                bytes = $_.Length
            }
        }
    $fileManifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (
        Join-Path $packageRoot "file-manifest.json") -Encoding UTF8

    $zipPath = Join-Path $outputRoot "$releaseName.zip"
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Compress-Archive -LiteralPath $packageRoot -DestinationPath $zipPath -CompressionLevel Optimal
    $zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    "$zipHash  $([System.IO.Path]::GetFileName($zipPath))" |
        Set-Content -LiteralPath "$zipPath.sha256" -Encoding ASCII

    & powershell -NoProfile -ExecutionPolicy Bypass -File `
        (Join-Path $PSScriptRoot "test-early-access-package.ps1") `
        -PackagePath $zipPath
    if ($LASTEXITCODE -ne 0) {
        throw "The final early-access package test failed."
    }

    $releaseMetadata = [ordered]@{
        release_channel = "early-access"
        plugin_version = $pluginVersion
        dataset_version = $datasetVersion
        record_count = $recordCount
        plugin_package = [System.IO.Path]::GetFileName($zipPath)
        plugin_sha256 = $zipHash
        database_package = "as-driven-db-$datasetVersion.zip"
        database_sha256 = (Get-FileHash -LiteralPath (
            Join-Path $outputRoot "as-driven-db-$datasetVersion.zip") -Algorithm SHA256).Hash.ToLowerInvariant()
        tested_simhub_version = "9.11.22"
        tested_ams2_version = "1.6.9.91"
        generated_at = [DateTime]::UtcNow.ToString("o")
    }
    $releaseMetadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (
        Join-Path $outputRoot "early-access-release.json") -Encoding UTF8

    Write-Host "Built early-access release candidates: $outputRoot"
}
finally {
    if (Test-Path -LiteralPath $staging) {
        Remove-Item -LiteralPath $staging -Recurse -Force
    }
}
