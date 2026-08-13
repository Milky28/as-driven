param(
    [string]$OutputDirectory = "",
    [switch]$SkipChecks
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path $PSScriptRoot -Parent
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $repositoryRoot "dist\database"
}
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)

if (-not $SkipChecks) {
    Push-Location $repositoryRoot
    try {
        & python -m as_driven_db validate
        if ($LASTEXITCODE -ne 0) { throw "Database validation failed." }
        & python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) { throw "Database tests failed." }
    }
    finally {
        Pop-Location
    }
}

$index = Get-Content -LiteralPath (Join-Path $repositoryRoot "data\v1\index.json") -Raw |
    ConvertFrom-Json
$datasetVersion = [string]$index.dataset_version
if ($datasetVersion -notmatch '^\d+\.\d+\.\d+$') {
    throw "Dataset index contains an invalid version: $datasetVersion"
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$staging = Join-Path ([System.IO.Path]::GetTempPath()) (
    "AsDrivenDatabase-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $staging | Out-Null
try {
    $packageRoot = Join-Path $staging "as-driven-db-$datasetVersion"
    New-Item -ItemType Directory -Path $packageRoot | Out-Null
    Copy-Item -LiteralPath (Join-Path $repositoryRoot "data") -Destination $packageRoot -Recurse
    Copy-Item -LiteralPath (Join-Path $repositoryRoot "schema") -Destination $packageRoot -Recurse
    New-Item -ItemType Directory -Path (Join-Path $packageRoot "docs") | Out-Null
    foreach ($document in @("data-model.md", "evidence-boundaries.md")) {
        Copy-Item -LiteralPath (Join-Path $repositoryRoot "docs\$document") `
            -Destination (Join-Path $packageRoot "docs")
    }
    foreach ($document in @("README.md", "DATA_LICENSE.md", "LICENSE")) {
        Copy-Item -LiteralPath (Join-Path $repositoryRoot $document) -Destination $packageRoot
    }

    $files = Get-ChildItem -LiteralPath $packageRoot -File -Recurse |
        Sort-Object FullName |
        ForEach-Object {
            [ordered]@{
                path = $_.FullName.Substring($packageRoot.Length + 1).Replace('\', '/')
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
                bytes = $_.Length
            }
        }
    $manifest = [ordered]@{
        package_format = "as-driven-database"
        package_format_version = "1.0.0"
        dataset_version = $datasetVersion
        schema_major = 1
        generated_at = [DateTime]::UtcNow.ToString("o")
        files = @($files)
    }
    $manifest | ConvertTo-Json -Depth 6 |
        Set-Content -LiteralPath (Join-Path $packageRoot "release-manifest.json") -Encoding UTF8

    $zipPath = Join-Path $OutputDirectory "as-driven-db-$datasetVersion.zip"
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Compress-Archive -LiteralPath $packageRoot -DestinationPath $zipPath -CompressionLevel Optimal
    $zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    "$zipHash  $([System.IO.Path]::GetFileName($zipPath))" |
        Set-Content -LiteralPath "$zipPath.sha256" -Encoding ASCII
    & powershell -NoProfile -ExecutionPolicy Bypass -File `
        (Join-Path $PSScriptRoot "test-install-database.ps1") -PackagePath $zipPath
    if ($LASTEXITCODE -ne 0) {
        throw "Database-only installer test failed."
    }
    Write-Host "Built independent database release: $zipPath"
}
finally {
    if (Test-Path -LiteralPath $staging) {
        Remove-Item -LiteralPath $staging -Recurse -Force
    }
}
