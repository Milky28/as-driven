param(
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [string]$SimHubInstallPath = "C:\Program Files (x86)\SimHub"
)

$ErrorActionPreference = "Stop"
$frameworkDirectory = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319"
if (-not (Test-Path -LiteralPath $frameworkDirectory)) {
    $frameworkDirectory = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319"
}
$msbuild = Join-Path $frameworkDirectory "MSBuild.exe"
if (-not (Test-Path -LiteralPath $msbuild)) {
    throw "The .NET Framework MSBuild executable was not found: $msbuild"
}
if (-not (Test-Path -LiteralPath (Join-Path $SimHubInstallPath "SimHub.Plugins.dll"))) {
    throw "SimHub SDK assemblies were not found: $SimHubInstallPath"
}

$projects = @(
    "AuthenticControls.Core\AuthenticControls.Core.csproj",
    "AuthenticControls.Core.Tests\AuthenticControls.Core.Tests.csproj",
    "AuthenticControls.Diagnostics\AuthenticControls.Diagnostics.csproj",
    "AuthenticControls.Plugin\AuthenticControls.Plugin.csproj"
)
foreach ($project in $projects) {
    & $msbuild (Join-Path $PSScriptRoot $project) /nologo /verbosity:minimal /target:Rebuild "/property:Configuration=$Configuration" "/property:Platform=AnyCPU" "/property:FrameworkPathOverride=$frameworkDirectory" "/property:SimHubInstallPath=$SimHubInstallPath"
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed: $project"
    }
}

$repositoryRoot = Split-Path $PSScriptRoot -Parent
$tests = Join-Path $PSScriptRoot "AuthenticControls.Core.Tests\bin\$Configuration\AuthenticControls.Core.Tests.exe"
& $tests $repositoryRoot
if ($LASTEXITCODE -ne 0) {
    throw "The .NET lookup tests failed."
}

$distRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "dist\AuthenticControls"))
$expectedParent = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "dist")) + [System.IO.Path]::DirectorySeparatorChar
if (-not $distRoot.StartsWith($expectedParent, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to package outside the SimHub dist directory: $distRoot"
}
if (Test-Path -LiteralPath $distRoot) {
    Remove-Item -LiteralPath $distRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $distRoot | Out-Null

$pluginOutput = Join-Path $PSScriptRoot "AuthenticControls.Plugin\bin\$Configuration"
Copy-Item -LiteralPath (Join-Path $pluginOutput "AuthenticControls.Plugin.dll") -Destination $distRoot
Copy-Item -LiteralPath (Join-Path $pluginOutput "AuthenticControls.Plugin.pdb") -Destination $distRoot
Copy-Item -LiteralPath (Join-Path $pluginOutput "AuthenticControls.Core.dll") -Destination $distRoot
Copy-Item -LiteralPath (Join-Path $pluginOutput "AuthenticControls.Core.pdb") -Destination $distRoot

$databaseTarget = Join-Path $distRoot "PluginsData\AuthenticControls\Database\data\v1"
New-Item -ItemType Directory -Path $databaseTarget -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $repositoryRoot "data\v1\index.json") -Destination $databaseTarget
Copy-Item -LiteralPath (Join-Path $repositoryRoot "data\v1\sources.json") -Destination $databaseTarget
Copy-Item -LiteralPath (Join-Path $repositoryRoot "data\v1\cars") -Destination $databaseTarget -Recurse

Write-Host "Built and tested Authentic Controls. SimHub-ready package: $distRoot"
