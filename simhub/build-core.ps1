param(
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [Parameter(Mandatory = $true)]
    [string]$NewtonsoftJsonPath
)

$ErrorActionPreference = "Stop"
$newtonsoftJson = [System.IO.Path]::GetFullPath($NewtonsoftJsonPath)
if (-not (Test-Path -LiteralPath $newtonsoftJson)) {
    throw "Newtonsoft.Json.dll was not found: $newtonsoftJson"
}

$frameworkDirectory = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319"
if (-not (Test-Path -LiteralPath $frameworkDirectory)) {
    $frameworkDirectory = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319"
}
$msbuild = Join-Path $frameworkDirectory "MSBuild.exe"
if (-not (Test-Path -LiteralPath $msbuild)) {
    throw "The .NET Framework MSBuild executable was not found: $msbuild"
}

# The core deliberately depends only on Newtonsoft.Json, which public CI can
# restore without distributing any SimHub SDK assemblies. The plugin adapter
# and its native-settings smoke test remain the maintainer's SDK-backed gate.
$newtonsoftDirectory = Split-Path -Parent $newtonsoftJson
foreach ($project in @(
    "AsDriven.Core\AsDriven.Core.csproj",
    "AsDriven.Core.Tests\AsDriven.Core.Tests.csproj"
)) {
    $buildArguments = @(
        (Join-Path $PSScriptRoot $project),
        "/nologo",
        "/verbosity:minimal",
        "/target:Rebuild",
        "/property:Configuration=$Configuration",
        "/property:Platform=AnyCPU",
        "/property:FrameworkPathOverride=$frameworkDirectory",
        "/property:SimHubInstallPath=$newtonsoftDirectory"
    )
    & $msbuild @buildArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Core build failed: $project"
    }
}

$testExecutable = Join-Path $PSScriptRoot "AsDriven.Core.Tests\bin\$Configuration\AsDriven.Core.Tests.exe"
& $testExecutable
if ($LASTEXITCODE -ne 0) {
    throw "Core test assertions failed."
}
Write-Output "Built and tested the SDK-independent As Driven core."
