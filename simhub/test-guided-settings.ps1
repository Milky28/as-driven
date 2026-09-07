param($Control, $PluginAssembly, [string]$PreviewDirectory = "")
$ErrorActionPreference = "Stop"
$flags = [Reflection.BindingFlags]::Instance -bor [Reflection.BindingFlags]::NonPublic
$type = $Control.GetType()
function Field($name) { $type.GetField($name, $flags).GetValue($Control) }
function SetField($name, $value) { $type.GetField($name, $flags).SetValue($Control, $value) }
function InvokeControl($name, [object[]]$arguments) { $type.GetMethod($name, $flags).Invoke($Control, [object[]]@($arguments | ForEach-Object { if ($null -eq $_) { $null } else { $_.PSObject.BaseObject } })) | Out-Null }
function ExpectVisibility($name, $visible) {
    $expected = if ($visible) { [Windows.Visibility]::Visible } else { [Windows.Visibility]::Collapsed }
    if ((Field $name).Visibility -ne $expected) { throw "$name must be $expected in this workflow stage." }
}
function RenderPreview($name) {
    if (-not $PreviewDirectory) { return }
    New-Item -ItemType Directory -Force -Path $PreviewDirectory | Out-Null
    $Control.Width = 850
    $Control.SetValue([Windows.Documents.TextElement]::ForegroundProperty, [Windows.Media.Brushes]::White)
    $Control.Background = [Windows.Media.BrushConverter]::new().ConvertFromString("#242424")
    $Control.Measure([Windows.Size]::new(850, [double]::PositiveInfinity))
    $Control.Arrange([Windows.Rect]::new(0, 0, 850, $Control.DesiredSize.Height))
    $Control.UpdateLayout()
    $Control.Measure([Windows.Size]::new(850, [double]::PositiveInfinity))
    $height = [math]::Ceiling($Control.DesiredSize.Height)
    $Control.Arrange([Windows.Rect]::new(0, 0, 850, $height))
    $Control.UpdateLayout()
    $bitmap = [Windows.Media.Imaging.RenderTargetBitmap]::new(850, $height, 96, 96, [Windows.Media.PixelFormats]::Pbgra32)
    $bitmap.Render($Control)
    $encoder = [Windows.Media.Imaging.PngBitmapEncoder]::new()
    $encoder.Frames.Add([Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
    $stream = [IO.File]::Create((Join-Path $PreviewDirectory "$name.png"))
    try { $encoder.Save($stream) } finally { $stream.Dispose() }
    Write-Host "Settings preview: $name (850 x $height)"
}
# Synthetic UI state only: no simulator actions, profile writes, or saved drafts.
SetField '_capture' $null
SetField '_loadingAssistProfile' $true
(Field '_assistSettingsConfirmed').IsChecked = $false
SetField '_loadingAssistProfile' $false
InvokeControl 'UpdateWorkflowGuidance' @($null, $null)
ExpectVisibility '_setupPanel' $false
ExpectVisibility '_captureStart' $true
ExpectVisibility '_guidedDrivePanel' $false
RenderPreview '01-capture'
$contextType = $PluginAssembly.GetType('AsDriven.Plugin.VerificationCaptureContext', $true)
$context = [Activator]::CreateInstance($contextType)
$context.Simulator = 'ams2'
$context.SimulatorDisplayName = 'Automobilista 2'
SetField '_capture' $context
(Field '_capturedIdentity').Text = 'Audi V8 quattro DTM | Automobilista 2 | Preview fixture'
(Field '_liveAvailability').Text = 'Captured car'
(Field '_save').IsEnabled = $true
InvokeControl 'UpdateWorkflowGuidance' @($null, $null)
ExpectVisibility '_setupPanel' $true
ExpectVisibility '_captureStart' $false
ExpectVisibility '_guidedDrivePanel' $false
RenderPreview '02-setup'
SetField '_loadingAssistProfile' $true
(Field '_automaticClutch').SelectedIndex = 1
(Field '_automaticShifting').SelectedIndex = 1
(Field '_automaticThrottleBlip').SelectedIndex = 3
(Field '_assistSettingsConfirmed').IsChecked = $true
SetField '_loadingAssistProfile' $false
InvokeControl 'UpdateWorkflowGuidance' @($null, $null)
ExpectVisibility '_guidedDrivePanel' $true
ExpectVisibility '_setupPanel' $false
ExpectVisibility '_driveActions' $false
RenderPreview '03-ready'
SetField '_guidedDriveStarted' $true
$snapshot = New-Object AsDriven.Core.GuidedDriveSnapshot
InvokeControl 'UpdateWorkflowGuidance' @($null, $snapshot)
ExpectVisibility '_setupPanel' $false
ExpectVisibility '_guidedStart' $false
ExpectVisibility '_driveActions' $true
RenderPreview '04-driving'
InvokeControl 'SetupStageClicked' @($null, $null)
InvokeControl 'UpdateWorkflowGuidance' @($null, $snapshot)
ExpectVisibility '_setupPanel' $true
ExpectVisibility '_guidedDrivePanel' $false
InvokeControl 'DriveStageClicked' @($null, $null)
InvokeControl 'UpdateWorkflowGuidance' @($null, $snapshot)
ExpectVisibility '_setupPanel' $false
ExpectVisibility '_guidedDrivePanel' $true
$snapshot.Completed = $true
InvokeControl 'SetReviewVisibility' @($true)
InvokeControl 'UpdateWorkflowGuidance' @($null, $snapshot)
ExpectVisibility '_setupPanel' $false
ExpectVisibility '_guidedDrivePanel' $false
ExpectVisibility '_reviewBorder' $true
(Field '_reviewHint').Text = 'Review captured results. Cockpit and wheel details are optional.'
# Reproduce a cockpit prompt with driving results previously expanded.
(Field '_drivingResultsExpander').IsExpanded = $true
InvokeControl 'HighlightReviewTarget' @((Field '_visibleHardwareBorder'), 'NEXT: Select the shift hardware visible in the cockpit.')
if (!(Field '_cockpitReview').IsExpanded -or (Field '_drivingResultsExpander').IsExpanded) { throw 'Cockpit prompt must reveal cockpit controls and collapse driving results.' }
(Field '_drivingResultsExpander').IsExpanded = $true
InvokeControl 'HighlightReviewTarget' @((Field '_visibleHardwareBorder'), 'NEXT: Select the shift hardware visible in the cockpit.')
if (!(Field '_drivingResultsExpander').IsExpanded) { throw 'Repeated guidance must preserve manual expansion.' }
InvokeControl 'HighlightReviewTarget' @((Field '_wheelShape'), 'NEXT: Review the wheel shape.')
if (!(Field '_wheelReview').IsExpanded -or (Field '_cockpitReview').IsExpanded -or (Field '_drivingResultsExpander').IsExpanded) { throw 'Wheel prompt must reveal wheel controls.' }
InvokeControl 'HighlightReviewTarget' @((Field '_automaticCut'), 'NEXT: Review automatic cut.')
if (!(Field '_drivingResultsExpander').IsExpanded -or (Field '_wheelReview').IsExpanded) { throw 'Driving prompt must reveal driving results.' }
InvokeControl 'HighlightReviewTarget' @((Field '_visibleHardwareBorder'), 'NEXT: Select the shift hardware visible in the cockpit.')
(Field '_wheelNotes').Text = ''
(Field '_evidenceNotes').Text = ''
InvokeControl 'HighlightReviewTarget' @((Field '_save'), 'NEXT: Finish and save your draft.')
if ((Field '_wheelReview').IsExpanded -or (Field '_cockpitReview').IsExpanded -or (Field '_drivingResultsExpander').IsExpanded -or (Field '_notesReview').IsExpanded) { throw 'Finish must collapse completed sections and empty notes.' }
(Field '_wheelNotes').Text = 'Observed wheel detail'
InvokeControl 'HighlightReviewTarget' @((Field '_wheelShape'), 'NEXT: Review the wheel shape.')
InvokeControl 'HighlightReviewTarget' @((Field '_save'), 'NEXT: Finish and save your draft.')
if (!(Field '_notesReview').IsExpanded) { throw 'Existing notes must remain visible at finish.' }
InvokeControl 'HighlightReviewTarget' @((Field '_visibleHardwareBorder'), 'NEXT: Select the shift hardware visible in the cockpit.')
RenderPreview '05-review'
(Field '_evidenceNotes').Text = 'Preserve my review notes.'
InvokeControl 'SetupStageClicked' @($null, $null)
InvokeControl 'ReviewStageClicked' @($null, $null)
if ((Field '_evidenceNotes').Text -ne 'Preserve my review notes.') { throw 'Stage navigation discarded review notes.' }
(Field '_save').IsEnabled = $false
(Field '_capturedIdentity').Text = 'Completed: preview fixture'
(Field '_savedDraftActions').Visibility = [Windows.Visibility]::Visible
InvokeControl 'SetReviewVisibility' @($false)
InvokeControl 'UpdateWorkflowGuidance' @($null, $snapshot)
ExpectVisibility '_setupPanel' $false
ExpectVisibility '_guidedDrivePanel' $false
ExpectVisibility '_savedDraftActions' $true
RenderPreview '06-saved'
Write-Host 'PASS: guided settings capture, setup, drive, review, saved, and revisit states'
