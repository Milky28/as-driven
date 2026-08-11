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

$pluginOutput = Join-Path $PSScriptRoot "AuthenticControls.Plugin\bin\$Configuration"
foreach ($dependency in @(
    "log4net.dll",
    "SimHub.Logging.dll",
    "GameReaderCommon.dll",
    "SimHub.Plugins.dll"
)) {
    [System.Reflection.Assembly]::LoadFrom(
        (Join-Path $SimHubInstallPath $dependency)) | Out-Null
}
[System.Reflection.Assembly]::LoadFrom(
    (Join-Path $pluginOutput "AuthenticControls.Core.dll")) | Out-Null
$pluginAssembly = [System.Reflection.Assembly]::LoadFrom(
    (Join-Path $pluginOutput "AuthenticControls.Plugin.dll"))
$pluginType = $pluginAssembly.GetType(
    "AuthenticControls.Plugin.AuthenticControls", $true)
$pluginInstance = [System.Activator]::CreateInstance($pluginType)
$menuIcon = $pluginType.GetProperty("PictureIcon").GetValue(
    $pluginInstance, $null)
if ($null -eq $menuIcon -or $menuIcon.Width -ne 24 -or $menuIcon.Height -ne 24) {
    throw "The Authentic Controls left-menu icon must be a non-null 24x24 image."
}
$stride = 24 * 4
$pixels = New-Object byte[] ($stride * 24)
$menuIcon.CopyPixels($pixels, $stride, 0)
if ($pixels[3] -ne 0 -or -not ($pixels | Where-Object { $_ -ne 0 })) {
    throw "The Authentic Controls left-menu glyph must have a transparent corner and visible content."
}
$resources = $pluginAssembly.GetManifestResourceNames()
if ($resources -notcontains "AuthenticControls.Plugin.Assets.authentic-controls-mark.png") {
    throw "The Authentic Controls production identity asset is not embedded."
}
$settingsControl = $pluginType.GetMethod("GetWPFSettingsControl").Invoke(
    $pluginInstance, @($null))
if ($null -eq $settingsControl -or $null -eq $settingsControl.Content) {
    throw "The Authentic Controls native settings page could not be created."
}
$verificationType = $pluginAssembly.GetType(
    "AuthenticControls.Plugin.VerificationControl", $true)
$queue = New-Object System.Collections.Queue
$queue.Enqueue($settingsControl)
$verificationFound = $false
while ($queue.Count -gt 0) {
    $node = $queue.Dequeue()
    if ($verificationType.IsInstanceOfType($node)) {
        $verificationFound = $true
        break
    }
    if ($node -is [System.Windows.DependencyObject]) {
        foreach ($child in [System.Windows.LogicalTreeHelper]::GetChildren($node)) {
            if ($null -ne $child) {
                $queue.Enqueue($child)
            }
        }
    }
}
if (-not $verificationFound) {
    throw "The native settings page does not contain guided verification."
}
Write-Host "PASS: Authentic Controls menu icon, settings page, and guided verification"

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

Copy-Item -LiteralPath (Join-Path $pluginOutput "AuthenticControls.Plugin.dll") -Destination $distRoot
Copy-Item -LiteralPath (Join-Path $pluginOutput "AuthenticControls.Plugin.pdb") -Destination $distRoot
Copy-Item -LiteralPath (Join-Path $pluginOutput "AuthenticControls.Core.dll") -Destination $distRoot
Copy-Item -LiteralPath (Join-Path $pluginOutput "AuthenticControls.Core.pdb") -Destination $distRoot

$databaseTarget = Join-Path $distRoot "PluginsData\AuthenticControls\Database\data\v1"
New-Item -ItemType Directory -Path $databaseTarget -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $repositoryRoot "data\v1\index.json") -Destination $databaseTarget
Copy-Item -LiteralPath (Join-Path $repositoryRoot "data\v1\sources.json") -Destination $databaseTarget
Copy-Item -LiteralPath (Join-Path $repositoryRoot "data\v1\cars") -Destination $databaseTarget -Recurse

$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) {
    throw "Python is required to generate the Dash Studio artifacts."
}
$dashboardTarget = Join-Path $distRoot "DashTemplates"
& $python.Source (Join-Path $PSScriptRoot "dash\generate.py") --output $dashboardTarget
if ($LASTEXITCODE -ne 0) {
    throw "Dash Studio artifact generation failed."
}

$overlayLayoutTarget = Join-Path $distRoot "OverlayLayouts"
New-Item -ItemType Directory -Path $overlayLayoutTarget -Force | Out-Null
Copy-Item -Path (Join-Path $PSScriptRoot "overlay\*.olayout") -Destination $overlayLayoutTarget

Write-Host "Built and tested Authentic Controls. SimHub-ready package: $distRoot"
