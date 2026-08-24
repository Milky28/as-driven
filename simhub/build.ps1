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
    "AsDriven.Core\AsDriven.Core.csproj",
    "AsDriven.Core.Tests\AsDriven.Core.Tests.csproj",
    "AsDriven.Diagnostics\AsDriven.Diagnostics.csproj",
    "AsDriven.Plugin\AsDriven.Plugin.csproj"
)
foreach ($project in $projects) {
    & $msbuild (Join-Path $PSScriptRoot $project) /nologo /verbosity:minimal /target:Rebuild "/property:Configuration=$Configuration" "/property:Platform=AnyCPU" "/property:FrameworkPathOverride=$frameworkDirectory" "/property:SimHubInstallPath=$SimHubInstallPath"
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed: $project"
    }
}

$pluginOutput = Join-Path $PSScriptRoot "AsDriven.Plugin\bin\$Configuration"
foreach ($dependency in @(
    # Native SimHub settings controls merge host UI dictionaries when they are
    # constructed. Preload those installed assemblies for the headless settings
    # smoke test; none of them are copied into the plugin package.
    "MahApps.Metro.dll",
    "GongSolutions.WPF.DragDrop.dll",
    "WoteverLocalization.dll",
    "AvalonDock.dll",
    "AvalonDock.Themes.VS2013.dll",
    "WoteverCommon.dll",
    "log4net.dll",
    "SimHub.Logging.dll",
    "GameReaderCommon.dll",
    "SimHub.Plugins.dll"
)) {
    [System.Reflection.Assembly]::LoadFrom(
        (Join-Path $SimHubInstallPath $dependency)) | Out-Null
}
[System.Reflection.Assembly]::LoadFrom(
    (Join-Path $pluginOutput "AsDriven.Core.dll")) | Out-Null
$pluginAssembly = [System.Reflection.Assembly]::LoadFrom(
    (Join-Path $pluginOutput "AsDriven.Plugin.dll"))
$pluginType = $pluginAssembly.GetType(
    "AsDriven.Plugin.AsDriven", $true)
$pluginInstance = [System.Activator]::CreateInstance($pluginType)
$instanceFlags = [System.Reflection.BindingFlags]::Instance -bor [System.Reflection.BindingFlags]::NonPublic
$showPopupMethod = $pluginType.GetMethod("ShowPopup", $instanceFlags)
$togglePopupMethod = $pluginType.GetMethod("TogglePopup", $instanceFlags)
$snapshotMethod = $pluginType.GetMethod("GetGuidedDriveSnapshot", $instanceFlags)
$retryMethod = $pluginType.GetMethod("GuidedVerificationRetry", $instanceFlags)
if ($null -eq $showPopupMethod -or $null -eq $togglePopupMethod `
    -or $null -eq $snapshotMethod -or $null -eq $retryMethod) {
    throw "The direct popup and guided-drive integration methods are incomplete."
}
if ($showPopupMethod.Invoke($pluginInstance, $null) `
    -or $togglePopupMethod.Invoke($pluginInstance, $null)) {
    throw "Mapped popup actions must refuse to show without live car data or a catalog preview."
}
$firstSnapshot = $snapshotMethod.Invoke($pluginInstance, $null)
$sameSnapshot = $snapshotMethod.Invoke($pluginInstance, $null)
if ($null -eq $firstSnapshot -or -not [object]::ReferenceEquals($firstSnapshot, $sameSnapshot)) {
    throw "Guided-drive properties must share one cached snapshot between state changes."
}
$retryMethod.Invoke($pluginInstance, $null) | Out-Null
$refreshedSnapshot = $snapshotMethod.Invoke($pluginInstance, $null)
if ([object]::ReferenceEquals($firstSnapshot, $refreshedSnapshot)) {
    throw "Guided-drive actions must refresh the cached snapshot."
}
$menuIcon = $pluginType.GetProperty("PictureIcon").GetValue(
    $pluginInstance, $null)
if ($null -eq $menuIcon -or $menuIcon.Width -ne 24 -or $menuIcon.Height -ne 24) {
    throw "The As Driven left-menu icon must be a non-null 24x24 image."
}
$stride = 24 * 4
$pixels = New-Object byte[] ($stride * 24)
$menuIcon.CopyPixels($pixels, $stride, 0)
if ($pixels[3] -ne 0 -or -not ($pixels | Where-Object { $_ -ne 0 })) {
    throw "The As Driven left-menu glyph must have a transparent corner and visible content."
}
$resources = $pluginAssembly.GetManifestResourceNames()
if ($resources -notcontains "AsDriven.Plugin.Assets.as-driven-mark.png") {
    throw "The As Driven production identity asset is not embedded."
}
try {
    $settingsControl = $pluginType.GetMethod("GetWPFSettingsControl").Invoke(
        $pluginInstance, @($null))
}
catch {
    $errorDetail = $_.Exception.ToString()
    $inner = $_.Exception.InnerException
    while ($null -ne $inner) {
        $errorDetail += [Environment]::NewLine + "INNER: " + $inner.ToString()
        $inner = $inner.InnerException
    }
    throw $errorDetail
}
if ($null -eq $settingsControl -or $null -eq $settingsControl.Content) {
    throw "The As Driven native settings page could not be created."
}
$verificationType = $pluginAssembly.GetType(
    "AsDriven.Plugin.VerificationControl", $true)
function Get-UiDescendants {
    param([System.Windows.DependencyObject]$Root)

    $queue = New-Object System.Collections.Queue
    $seen = New-Object 'System.Collections.Generic.HashSet[System.Windows.DependencyObject]'
    $queue.Enqueue($Root)
    while ($queue.Count -gt 0) {
        $node = $queue.Dequeue()
        if ($null -eq $node -or -not $seen.Add($node)) {
            continue
        }
        Write-Output $node
        try {
            foreach ($child in [System.Windows.LogicalTreeHelper]::GetChildren($node)) {
                if ($child -is [System.Windows.DependencyObject]) {
                    $queue.Enqueue($child)
                }
            }
        }
        catch {
            # Some WPF primitives have no logical children.
        }
        try {
            for ($index = 0; $index -lt [System.Windows.Media.VisualTreeHelper]::GetChildrenCount($node); $index++) {
                $queue.Enqueue([System.Windows.Media.VisualTreeHelper]::GetChild($node, $index))
            }
        }
        catch {
            # Not every DependencyObject is a Visual.
        }
    }
}

function Get-UiAncestor {
    param(
        [System.Windows.DependencyObject]$Node,
        [Type]$Type
    )

    $current = $Node
    while ($null -ne $current) {
        if ($Type.IsInstanceOfType($current)) {
            return $current
        }
        try {
            $current = [System.Windows.LogicalTreeHelper]::GetParent($current)
        }
        catch {
            return $null
        }
    }
    return $null
}

$ui = @(Get-UiDescendants $settingsControl)
$verificationControl = @($ui | Where-Object { $verificationType.IsInstanceOfType($_) } | Select-Object -First 1)
if ($verificationControl.Count -ne 1) {
    throw "The native settings page does not contain guided verification."
}
$verificationControl = $verificationControl[0]
$tabs = @($ui | Where-Object { $_ -is [SimHub.Plugins.Styles.SHTabControl] } | Select-Object -First 1)
$expectedTabs = @("Overlay", "Car browser", "Contribute data", "Advanced")
$actualTabs = @($tabs[0].Items | ForEach-Object { [string]$_.Header })
if ($tabs.Count -ne 1 `
    -or $actualTabs.Count -ne $expectedTabs.Count `
    -or (Compare-Object $expectedTabs $actualTabs -SyncWindow 0)) {
    throw "The settings page must expose Overlay, Car browser, Contribute data, and Advanced tabs."
}
$showPopupButton = @($ui | Where-Object {
        $_ -is [System.Windows.Controls.Button] -and $_.Content -eq "Show popup"
    } | Select-Object -First 1)
if ($showPopupButton.Count -ne 1 -or $showPopupButton[0].IsEnabled) {
    throw "Show popup must remain disabled until live car data or a catalog preview is available."
}
$captureStartButton = @($ui | Where-Object {
        $_ -is [System.Windows.Controls.Button] -and $_.Content -eq "Capture current car"
    } | Select-Object -First 1)
if ($captureStartButton.Count -ne 1 -or $captureStartButton[0].IsEnabled) {
    throw "The contributor capture button must remain disabled without live telemetry."
}
$persistentSubmissionButton = @($ui | Where-Object {
        $_ -is [System.Windows.Controls.Button] -and $_.Content -eq "Open submission form"
    } | Select-Object -First 1)
if ($persistentSubmissionButton.Count -ne 1 -or -not $persistentSubmissionButton[0].IsEnabled) {
    throw "The contribution page must always provide a way to reopen the submission form."
}
$submissionUrlMethod = $pluginType.GetMethod(
    "ObservationSubmissionUrl",
    [System.Reflection.BindingFlags]::Static -bor [System.Reflection.BindingFlags]::NonPublic)
$prefilledSubmissionUrl = if ($null -eq $submissionUrlMethod) {
    ""
}
else {
    [string]$submissionUrlMethod.Invoke($null, @("AMS2", "Test Car"))
}
if ($prefilledSubmissionUrl -notlike "*template=simulator-observation.yml*" `
    -or $prefilledSubmissionUrl -notlike "*title=%5BObservation%5D%3A%20AMS2%20%E2%80%94%20Test%20Car*") {
    throw "A saved drive must open the observation form with a descriptive prefilled title."
}
$guidedStartButton = @($ui | Where-Object {
        $_ -is [System.Windows.Controls.Button] -and $_.Content -eq "Start in-sim guided drive"
    } | Select-Object -First 1)
if ($guidedStartButton.Count -ne 1 -or $guidedStartButton[0].IsEnabled) {
    throw "The guided-start button must remain disabled until assist settings are confirmed."
}
$previewMethod = $pluginType.GetMethod(
    "ShouldLeavePreview",
    [System.Reflection.BindingFlags]::Static -bor [System.Reflection.BindingFlags]::NonPublic)
if ($null -eq $previewMethod `
    -or $previewMethod.Invoke($null, @($true, $true, "Live Car", "Live Car")) `
    -or -not $previewMethod.Invoke($null, @($true, $true, "Live Car", "Different Car")) `
    -or $previewMethod.Invoke($null, @($true, $true, "Live Car", ""))) {
    throw "Preview mode must survive same-car telemetry and exit only for a different live identity."
}
$reviewHint = @($ui | Where-Object {
        $_ -is [System.Windows.Controls.TextBlock] `
            -and $_.Text -eq "Run the guided drive to populate driving results. Optional review fields will be highlighted here."
    } | Select-Object -First 1)
$formPanel = if ($reviewHint.Count -eq 1) {
    [System.Windows.LogicalTreeHelper]::GetParent($reviewHint[0])
}
else {
    $null
}
if ($null -eq $formPanel -or $formPanel.Visibility -ne [System.Windows.Visibility]::Collapsed) {
    throw "The observation review area must remain hidden until a live car is captured."
}
$sidebarBorder = Get-UiAncestor $captureStartButton[0] ([System.Windows.Controls.Border])
$reviewBorder = Get-UiAncestor $reviewHint[0] ([System.Windows.Controls.Border])
$workspace = Get-UiAncestor $sidebarBorder ([System.Windows.Controls.Grid])
if ($null -eq $workspace -or $null -eq $sidebarBorder -or $null -eq $reviewBorder) {
    throw "The contributor responsive workspace is incomplete."
}

# Size the actual visual tree instead of invoking private layout helpers. This
# verifies the contributor page still provides a full-width setup view, stacks
# review at ordinary widths, and uses balanced columns on wide pages.
$verificationControl.Width = 1100
$verificationControl.Measure([System.Windows.Size]::new(1100, 2000))
$verificationControl.Arrange([System.Windows.Rect]::new(0, 0, 1100, 2000))
$verificationControl.UpdateLayout()
if ([System.Windows.Controls.Grid]::GetColumnSpan($sidebarBorder) -ne 3 `
    -or -not $workspace.ColumnDefinitions[0].Width.IsStar `
    -or $workspace.ColumnDefinitions[1].Width.Value -ne 0) {
    throw "Setup-only contribution mode must use the full workspace width."
}
$reviewBorder.Visibility = [System.Windows.Visibility]::Visible
$verificationControl.Width = 900
$verificationControl.Measure([System.Windows.Size]::new(900, 2000))
$verificationControl.Arrange([System.Windows.Rect]::new(0, 0, 900, 2000))
$verificationControl.UpdateLayout()
if ([System.Windows.Controls.Grid]::GetColumnSpan($sidebarBorder) -ne 3 `
    -or [System.Windows.Controls.Grid]::GetRow($reviewBorder) -ne 2) {
    throw "The contributor review must stack at ordinary window widths."
}
$verificationControl.Width = 1100
$verificationControl.Measure([System.Windows.Size]::new(1100, 2000))
$verificationControl.Arrange([System.Windows.Rect]::new(0, 0, 1100, 2000))
$verificationControl.UpdateLayout()
if ([System.Windows.Controls.Grid]::GetColumnSpan($sidebarBorder) -ne 1 `
    -or [System.Windows.Controls.Grid]::GetColumn($reviewBorder) -ne 2 `
    -or $workspace.ColumnDefinitions[0].Width.Value -ne 2 `
    -or $workspace.ColumnDefinitions[2].Width.Value -ne 3) {
    throw "The contributor review must use balanced columns on wide pages."
}
$reviewBorder.Visibility = [System.Windows.Visibility]::Collapsed
$assistConfirmation = @($ui | Where-Object {
        $_ -is [System.Windows.Controls.CheckBox] -and $_.Content -eq "Use this verified setup"
    } | Select-Object -First 1)
if ($assistConfirmation.Count -ne 1 -or $assistConfirmation[0].BorderThickness.Left -lt 2) {
    throw "The required assist confirmation must be visibly highlighted before selection."
}
Write-Host "PASS: As Driven menu icon, settings page, and optional contributor workflow"

$repositoryRoot = Split-Path $PSScriptRoot -Parent
$tests = Join-Path $PSScriptRoot "AsDriven.Core.Tests\bin\$Configuration\AsDriven.Core.Tests.exe"
& $tests $repositoryRoot
if ($LASTEXITCODE -ne 0) {
    throw "The .NET lookup tests failed."
}

$distRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "dist\AsDriven"))
$expectedParent = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "dist")) + [System.IO.Path]::DirectorySeparatorChar
if (-not $distRoot.StartsWith($expectedParent, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to package outside the SimHub dist directory: $distRoot"
}
if (Test-Path -LiteralPath $distRoot) {
    Remove-Item -LiteralPath $distRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $distRoot | Out-Null

Copy-Item -LiteralPath (Join-Path $pluginOutput "AsDriven.Plugin.dll") -Destination $distRoot
Copy-Item -LiteralPath (Join-Path $pluginOutput "AsDriven.Plugin.pdb") -Destination $distRoot
Copy-Item -LiteralPath (Join-Path $pluginOutput "AsDriven.Core.dll") -Destination $distRoot
Copy-Item -LiteralPath (Join-Path $pluginOutput "AsDriven.Core.pdb") -Destination $distRoot

$databaseTarget = Join-Path $distRoot "PluginsData\AsDriven\Database\data\v1"
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
$verificationDashboard = Join-Path $dashboardTarget "As Driven Verification Drive\As Driven Verification Drive.djson"
if (-not (Test-Path -LiteralPath $verificationDashboard)) {
    throw "The guided verification Dash Studio surface was not generated."
}
$verificationDashboardJson = Get-Content -LiteralPath $verificationDashboard -Raw
foreach ($requiredProperty in @(
    "AsDriven.VerificationDriveVisible",
    "AsDriven.VerificationDrivePromptLine1",
    "AsDriven.VerificationDrivePromptLine2",
    "AsDriven.VerificationDriveResult"
)) {
    if (-not $verificationDashboardJson.Contains($requiredProperty)) {
        throw "The guided verification surface is missing property: $requiredProperty"
    }
}

$overlayLayoutTarget = Join-Path $distRoot "OverlayLayouts"
New-Item -ItemType Directory -Path $overlayLayoutTarget -Force | Out-Null
Copy-Item -Path (Join-Path $PSScriptRoot "overlay\*.olayout") -Destination $overlayLayoutTarget

Write-Host "Built and tested As Driven. SimHub-ready package: $distRoot"
