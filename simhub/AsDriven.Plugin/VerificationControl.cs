using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Media;
using AsDriven.Core;

namespace AsDriven.Plugin
{
    internal sealed partial class VerificationControl : Border
    {
        private readonly AsDriven _plugin;
        private readonly Button[] _workflowSteps;
        private readonly Dictionary<ComboBox, string> _guidedOriginalChoices =
            new Dictionary<ComboBox, string>();
        private readonly HashSet<ComboBox> _manualOverrides =
            new HashSet<ComboBox>();
        private VerificationCaptureContext _capture;
        private bool _guidedDriveApplied;
        private bool _guidedDriveStarted;
        private bool _applyingGuidedResults;
        private bool _loadingAssistProfile;
        private string _guidedAutomaticCutMethod = string.Empty;
        private string _guidedAutomaticBlipMethod = string.Empty;
        private string _guidedEvidenceNotes = string.Empty;
        private string _savedDraftPath = string.Empty;
        // No form control: these are the first stage of a two-stage test, which
        // the drive either ran or did not. A reviewer editing the second stage
        // by hand must not silently restate the first.
        private string _guidedFullThrottleUpshift = "not-tested";
        private string _guidedCoastDownshift = "not-tested";

        public VerificationControl(AsDriven plugin)
        {
            _plugin = plugin;
            InitializeComponent();
            _workflowSteps = new[]
            {
                _workflowStep1,
                _workflowStep2,
                _workflowStep3,
                _workflowStep4,
            };
            _observer.Text = plugin.VerificationObserver;
            _draftDirectory.Text = plugin.VerificationDraftDirectory;
            AttachBadge(_moveOff, _moveOffBadge);
            AttachBadge(_forwardGears, _forwardGearsBadge);
            AttachBadge(_directGearSelection, _directGearSelectionBadge);
            AttachBadge(_clutchlessUpshift, _clutchlessUpshiftBadge);
            AttachBadge(_automaticCut, _automaticCutBadge);
            AttachBadge(_clutchlessDownshift, _clutchlessDownshiftBadge);
            AttachBadge(_automaticBlip, _automaticBlipBadge);
            AttachBadge(_primaryActuation, _primaryActuationBadge);
            AttachBadge(_shiftPattern, _shiftPatternBadge);
            AttachBadge(_wheelShape, _wheelShapeBadge);
            AttachBadge(_wheelDisplay, _wheelDisplayBadge);
            AttachBadge(_wheelShiftLights, _wheelShiftLightsBadge);
            AttachBadge(_wheelOpenTop, _wheelOpenTopBadge);
            _automaticClutch.SelectionChanged += AssistChoiceChanged;
            _automaticShifting.SelectionChanged += AssistChoiceChanged;
            _automaticThrottleBlip.SelectionChanged += AssistChoiceChanged;
            _assistSettingsConfirmed.Checked += AssistSettingsConfirmationChanged;
            _assistSettingsConfirmed.Unchecked += AssistSettingsConfirmationChanged;
            foreach (ComboBox guidedChoice in new[]
            {
                _moveOff, _directGearSelection, _clutchlessUpshift,
                _automaticCut, _clutchlessDownshift, _automaticBlip
            })
            {
                guidedChoice.SelectionChanged += GuidedChoiceEdited;
            }
            _forwardGears.TextChanged += GuidedTextEdited;
            _automaticCutMethod.TextChanged += GuidedTextEdited;
            _automaticBlipMethod.TextChanged += GuidedTextEdited;
            foreach (CheckBox visibleControl in new[]
            {
                _visiblePaddles, _visibleSequentialStick,
                _visibleHPattern, _visibleAutomaticLever
            })
            {
                visibleControl.Checked += VisibleHardwareChanged;
                visibleControl.Unchecked += VisibleHardwareChanged;
            }
            _primaryActuation.SelectionChanged += PrimaryActuationChanged;
            _actuationBasis.TextChanged += ManualEvidenceChanged;
            foreach (ComboBox optionalChoice in new[]
            {
                _primaryActuation, _shiftPattern, _wheelShape, _wheelDisplay,
                _wheelShiftLights, _wheelOpenTop
            })
            {
                optionalChoice.SelectionChanged += OptionalChoiceChanged;
            }
            _evidenceNotes.TextChanged += ManualEvidenceChanged;
            SizeChanged += VerificationControlSizeChanged;
            UpdateAssistConfirmationStyle();
            UpdateWheelOpenTopApplicability();
            UpdateLiveAvailability();
        }

        /// <summary>
        /// The car and its class, with the class left out when the simulator
        /// reports none. Assetto Corsa EVO groups no cars, and printing the word
        /// "unknown" there read as a fault in the capture rather than as
        /// something the game does not publish.
        /// </summary>
        private static string DescribeLiveCarName(VerificationCaptureContext live)
        {
            return string.IsNullOrWhiteSpace(live.TelemetryClass)
                    || live.TelemetryClass == "unknown"
                ? live.TelemetryName
                : live.TelemetryName + " - " + live.TelemetryClass;
        }

        /// <summary>
        /// The live car as the capture line names it, with the simulator and its
        /// build. Assetto Corsa EVO ships an executable with no version resource,
        /// so the plugin has no build to report there and says so rather than
        /// showing a gap the reader would take for a fault.
        /// </summary>
        private static string DescribeLiveCar(VerificationCaptureContext live)
        {
            string car = DescribeLiveCarName(live);
            string version =
                string.IsNullOrWhiteSpace(live.GameVersion) || live.GameVersion == "unknown"
                    ? "version not reported"
                    : live.GameVersion;
            return car + " (" + live.SimulatorDisplayName + ", " + version + ")";
        }

        internal void UpdateLiveAvailability()
        {
            VerificationCaptureContext live = _plugin.CaptureVerificationContext();
            if (live != null
                && DraftWasSaved()
                && !SameLiveCar(_capture, live))
            {
                PrepareForNextCar(live);
            }
            _liveAvailability.Text = live == null
                ? "Waiting for a live car. Start the simulator and load a car first."
                : "Ready to capture: " + DescribeLiveCar(live);
            _liveAvailability.Foreground = live == null ? Brushes.Goldenrod : Brushes.LightGreen;

            GuidedDriveSnapshot guided = _plugin.GetGuidedDriveSnapshot();
            if (guided.Completed && !_guidedDriveApplied)
            {
                if (_capture == null)
                {
                    _capture = _plugin.GetGuidedVerificationCapture();
                    if (_capture != null)
                    {
                        ResetForm();
                        _capturedIdentity.Text = "Captured: " + DescribeLiveCar(_capture)
                            + " | " + _capture.ClientVersion;
                        _save.IsEnabled = true;
                    }
                }
                if (_capture == null)
                {
                    UpdateWorkflowGuidance(live, guided);
                    return;
                }
                ApplyGuidedResults(_plugin.GetGuidedDriveResults());
                _guidedDriveApplied = true;
                SetReviewVisibility(true);
                SetStatus("Guided drive complete. Suggested driving results were filled in; review the cockpit and wheel fields before saving.", Brushes.LightGreen, true);
            }
            UpdateWorkflowGuidance(live, guided);
        }

        private bool DraftWasSaved()
        {
            return _capture != null
                && !_save.IsEnabled
                && _capturedIdentity.Text.StartsWith("Completed:", StringComparison.Ordinal);
        }

        private static bool SameLiveCar(
            VerificationCaptureContext captured,
            VerificationCaptureContext live)
        {
            return captured != null
                && live != null
                && string.Equals(captured.Simulator, live.Simulator, StringComparison.Ordinal)
                && string.Equals(captured.TelemetryName, live.TelemetryName, StringComparison.Ordinal)
                && (string.IsNullOrWhiteSpace(captured.InternalId)
                    || string.IsNullOrWhiteSpace(live.InternalId)
                    || string.Equals(captured.InternalId, live.InternalId, StringComparison.Ordinal));
        }

        private void PrepareForNextCar(VerificationCaptureContext live)
        {
            _capture = null;
            _savedDraftPath = string.Empty;
            _savedDraftActions.Visibility = Visibility.Collapsed;
            _guidedDriveApplied = true;
            _guidedDriveStarted = false;
            _save.IsEnabled = false;
            SetReviewVisibility(false);
            _capturedIdentity.Text = "Ready for a new verification: "
                + DescribeLiveCarName(live) + ".";
            SetStatus(
                "A different live car was detected. Capture the current car to begin a fresh draft.",
                Brushes.LightGreen,
                true);
        }

        private void StartClicked(object sender, RoutedEventArgs eventArgs)
        {
            VerificationCaptureContext live = _plugin.CaptureVerificationContext();
            if (live == null)
            {
                _status.Text = "No live car telemetry is available. Load a car in the simulator, then try again.";
                return;
            }
            BeginFromCapture(live);
        }

        internal void BeginFromCapture(VerificationCaptureContext live)
        {
            if (live == null)
            {
                throw new ArgumentNullException("live");
            }
            _capture = live;
            _guidedDriveApplied = true;
            _guidedDriveStarted = false;
            ResetForm();
            SetReviewVisibility(false);
            _capturedIdentity.Text = "Captured: " + DescribeLiveCar(live)
                + " | " + live.ClientVersion;
            _save.IsEnabled = true;
            SetStatus(live.SuggestedForwardGears.HasValue
                ? "Verification started. SimHub suggested " + live.SuggestedForwardGears.Value
                    + " forward gears; confirm it by selecting every gear."
                : "Verification started. Complete the form, then save a draft.", Brushes.LightGreen, false);
            UpdateWorkflowGuidance(_plugin.CaptureVerificationContext(), _plugin.GetGuidedDriveSnapshot());
        }

        private void ResetForm()
        {
            _savedDraftPath = string.Empty;
            _savedDraftActions.Visibility = Visibility.Collapsed;
            // Expansion is workflow state, not a user preference. Do not carry
            // the previous car's review state into a fresh verification.
            _drivingResultsExpander.IsExpanded = false;
            _loadingAssistProfile = true;
            foreach (ComboBox combo in new[]
            {
                _automaticClutch, _automaticShifting, _automaticThrottleBlip,
                _moveOff, _directGearSelection, _clutchlessUpshift, _automaticCut,
                _clutchlessDownshift, _automaticBlip, _primaryActuation,
                _shiftPattern, _wheelShape, _wheelDisplay, _wheelShiftLights,
                _wheelOpenTop
            })
            {
                combo.SelectedIndex = 0;
            }
            VerificationAssistProfile savedProfile =
                _plugin.GetVerificationAssistProfile(_capture.Simulator);
            if (savedProfile != null && savedProfile.Confirmed)
            {
                SelectChoice(_automaticClutch, savedProfile.AutomaticClutch);
                SelectChoice(_automaticShifting, savedProfile.AutomaticShifting);
                SelectChoice(_automaticThrottleBlip, savedProfile.AutomaticThrottleBlip);
                _assistSettingsConfirmed.IsChecked = true;
            }
            else if (string.Equals(_capture.Simulator, "ams2", StringComparison.Ordinal))
            {
                SelectChoice(_automaticClutch, "disabled");
                SelectChoice(_automaticShifting, "disabled");
                SelectChoice(_automaticThrottleBlip, "unavailable");
                _assistSettingsConfirmed.IsChecked = false;
            }
            else
            {
                _assistSettingsConfirmed.IsChecked = false;
            }
            _loadingAssistProfile = false;
            UpdateAssistConfirmationStyle();
            _forwardGears.Text = _capture.SuggestedForwardGears.HasValue
                ? _capture.SuggestedForwardGears.Value.ToString(CultureInfo.InvariantCulture)
                : string.Empty;
            _assistNotes.Text = string.Empty;
            _automaticCutMethod.Text = string.Empty;
            _automaticBlipMethod.Text = string.Empty;
            _actuationBasis.Text = string.Empty;
            _wheelNotes.Text = string.Empty;
            _evidenceNotes.Text = string.Empty;
            _visiblePaddles.IsChecked = false;
            _visibleSequentialStick.IsChecked = false;
            _visibleHPattern.IsChecked = false;
            _visibleAutomaticLever.IsChecked = false;
            _guidedOriginalChoices.Clear();
            _manualOverrides.Clear();
            _guidedAutomaticCutMethod = string.Empty;
            _guidedAutomaticBlipMethod = string.Empty;
            _guidedEvidenceNotes = string.Empty;
            _guidedFullThrottleUpshift = "not-tested";
            _guidedCoastDownshift = "not-tested";
            _evidenceNotes.BorderThickness = new Thickness(1);
            _evidenceNotes.BorderBrush = new SolidColorBrush(Color.FromArgb(80, 120, 150, 180));
            UpdateWheelOpenTopApplicability();
            foreach (Control control in new Control[]
            {
                _moveOff, _forwardGears, _directGearSelection,
                _clutchlessUpshift, _automaticCut, _automaticCutMethod,
                _clutchlessDownshift, _automaticBlip, _automaticBlipMethod
            })
            {
                ClearFieldBadge(control);
            }
            UpdateOptionalBadges();
        }

        private void SaveClicked(object sender, RoutedEventArgs eventArgs)
        {
            if (_capture == null)
            {
                _status.Text = "Start a verification from the live car first.";
                return;
            }
            if (_assistSettingsConfirmed.IsChecked != true)
            {
                SetStatus("Verify the simulator assist settings and check the confirmation box before saving.", Brushes.Goldenrod, false);
                return;
            }
            string[] missingEvidence = MissingManualOverrideEvidence();
            if (missingEvidence.Length > 0)
            {
                _evidenceNotes.BorderBrush = Brushes.Orange;
                _evidenceNotes.BorderThickness = new Thickness(2);
                SetStatus(
                    "Supporting evidence is required for the manual override: "
                        + string.Join(", ", missingEvidence)
                        + ". Describe what you observed in the related method field or Review notes.",
                    Brushes.Orange,
                    true);
                return;
            }
            int parsedGears;
            int? forwardGears = null;
            if (!string.IsNullOrWhiteSpace(_forwardGears.Text))
            {
                if (!int.TryParse(_forwardGears.Text.Trim(), out parsedGears)
                    || parsedGears < 1
                    || parsedGears > 20)
                {
                    _status.Text = "Forward gears must be blank or a number from 1 to 20.";
                    return;
                }
                forwardGears = parsedGears;
            }

            try
            {
                string[] visible = VisibleActuators();
                var draft = new VerificationObservationDraft
                {
                    Simulator = _capture.Simulator,
                    SourceGameName = _capture.SourceGameName,
                    GameVersion = _capture.GameVersion,
                    ClientVersion = _capture.ClientVersion,
                    DatasetVersion = _plugin.CurrentDatasetVersion,
                    ObservedAtUtc = _capture.ObservedAtUtc,
                    TelemetryName = _capture.TelemetryName,
                    TelemetryClass = _capture.TelemetryClass,
                    InternalId = _capture.InternalId,
                    AutomaticClutch = ChoiceValue(_automaticClutch),
                    AutomaticShifting = ChoiceValue(_automaticShifting),
                    AutomaticThrottleBlip = ChoiceValue(_automaticThrottleBlip),
                    AssistNotes = _assistNotes.Text,
                    MoveOffWithoutPhysicalClutch = ChoiceValue(_moveOff),
                    ForwardGears = forwardGears,
                    DirectGearSelectionBehavior = ChoiceValue(_directGearSelection),
                    ClutchlessUpshift = ChoiceValue(_clutchlessUpshift),
                    AutomaticCut = ChoiceValue(_automaticCut),
                    AutomaticCutMethod = _automaticCutMethod.Text,
                    ClutchlessDownshift = ChoiceValue(_clutchlessDownshift),
                    AutomaticBlip = ChoiceValue(_automaticBlip),
                    AutomaticBlipMethod = _automaticBlipMethod.Text,
                    FullThrottleUpshift = _guidedFullThrottleUpshift,
                    // GTR2 resolves and fingerprints its selected .CAR and
                    // physics files while the game is running. Assetto Corsa's
                    // package can be resolved from its content id at save time.
                    // Null remains an ordinary outcome when an installation is
                    // unavailable rather than making the drive itself fail.
                    Implementation = _capture.Implementation
                        ?? (_capture.Simulator == "ac"
                            ? CarImplementation.ForAssettoCorsa(_capture.InternalId)
                            : null),
                    CoastDownshift = _guidedCoastDownshift,
                    VisibleShiftActuators = visible,
                    PrimaryShiftActuation = ChoiceValue(_primaryActuation),
                    ShiftPattern = ChoiceValue(_shiftPattern),
                    ActuationBasis = _actuationBasis.Text,
                    WheelShape = ChoiceValue(_wheelShape),
                    WheelIntegratedDisplay = ChoiceValue(_wheelDisplay),
                    WheelShiftLights = ChoiceValue(_wheelShiftLights),
                    WheelOpenTop = ChoiceValue(_wheelOpenTop),
                    WheelNotes = _wheelNotes.Text,
                    EvidenceNotes = string.IsNullOrWhiteSpace(_evidenceNotes.Text)
                        ? new string[0]
                        : new[] { _evidenceNotes.Text.Trim() }
                };
                string path = _plugin.SaveVerificationDraft(draft, _observer.Text);
                _savedDraftPath = path;
                _savedDraftActions.Visibility = Visibility.Visible;
                _capturedIdentity.Text = "Completed: " + _capture.TelemetryName
                    + " - draft saved for review.";
                SetStatus("\u2713 DRAFT SAVED SUCCESSFULLY\n" + path, Brushes.LightGreen, true);
                _save.IsEnabled = false;
                SetReviewVisibility(false);
                UpdateWorkflowGuidance(
                    _plugin.CaptureVerificationContext(),
                    _plugin.GetGuidedDriveSnapshot());
            }
            catch (Exception exception)
            {
                _status.Text = "Could not save the draft: " + exception.Message;
            }
        }

        private void GuidedStartClicked(object sender, RoutedEventArgs eventArgs)
        {
            if (_capture == null)
            {
                SetStatus("Start a verification from the live car first.", Brushes.Goldenrod, false);
                return;
            }
            if (_assistSettingsConfirmed.IsChecked != true)
            {
                SetStatus("Verify the simulator assist settings and check the confirmation box before starting the guided drive.", Brushes.Goldenrod, false);
                return;
            }
            if (ChoiceValue(_automaticClutch) == "unknown"
                || ChoiceValue(_automaticShifting) == "unknown"
                || ChoiceValue(_automaticThrottleBlip) == "unknown")
            {
                SetStatus("Confirm all three simulator assist settings before starting the guided drive.", Brushes.Goldenrod, false);
                return;
            }
            if (ChoiceValue(_automaticClutch) == "enabled"
                || ChoiceValue(_automaticShifting) == "enabled"
                || ChoiceValue(_automaticThrottleBlip) == "enabled")
            {
                SetStatus("The guided drive cannot safely attribute results while one of these assists is enabled. Disable it if possible; otherwise keep the affected results Not tested and complete the form manually.", Brushes.Goldenrod, false);
                return;
            }
            _guidedDriveApplied = false;
            _guidedDriveStarted = true;
            _plugin.StartGuidedVerificationDrive(_capture);
            SetStatus("In-sim guided drive started. Follow the verification overlay prompts.", Brushes.LightGreen, true);
            UpdateWorkflowGuidance(
                _plugin.CaptureVerificationContext(),
                _plugin.GetGuidedDriveSnapshot());
        }

        private void GuidedNextClicked(object sender, RoutedEventArgs eventArgs)
        {
            _plugin.GuidedVerificationNext();
        }

        private void GuidedRetryClicked(object sender, RoutedEventArgs eventArgs)
        {
            _plugin.GuidedVerificationRetry();
        }

        private void GuidedSkipClicked(object sender, RoutedEventArgs eventArgs)
        {
            _plugin.GuidedVerificationSkip();
        }

        private void GuidedCancelClicked(object sender, RoutedEventArgs eventArgs)
        {
            _plugin.GuidedVerificationCancel();
            _guidedDriveStarted = false;
            SetStatus("Guided drive cancelled. Existing form entries were preserved.", Brushes.Goldenrod, false);
            UpdateWorkflowGuidance(
                _plugin.CaptureVerificationContext(),
                _plugin.GetGuidedDriveSnapshot());
        }

        private void ApplyGuidedResults(GuidedDriveResults results)
        {
            if (results == null)
            {
                return;
            }
            _applyingGuidedResults = true;
            try
            {
                ApplyGuidedChoice(_moveOff, results.MoveOffWithoutPhysicalClutch);
                ApplyGuidedChoice(_directGearSelection, results.DirectGearSelection);
                ApplyGuidedChoice(_clutchlessUpshift, results.ClutchlessUpshift);
                ApplyGuidedChoice(_automaticCut, results.AutomaticCut);
                ApplyGuidedChoice(_clutchlessDownshift, results.ClutchlessDownshift);
                ApplyGuidedChoice(_automaticBlip, results.AutomaticBlip);
                _guidedFullThrottleUpshift = results.FullThrottleUpshift;
                _guidedCoastDownshift = results.CoastDownshift;
                if (results.ForwardGears.HasValue)
                {
                    _forwardGears.Text = results.ForwardGears.Value.ToString(CultureInfo.InvariantCulture);
                    SetFieldBadge(_forwardGears, "AUTO-DETECTED", Brushes.Gray);
                }
                _automaticCutMethod.Text = results.AutomaticCutMethod ?? string.Empty;
                _automaticBlipMethod.Text = results.AutomaticBlipMethod ?? string.Empty;
                _guidedAutomaticCutMethod = _automaticCutMethod.Text;
                _guidedAutomaticBlipMethod = _automaticBlipMethod.Text;
                SetFieldBadge(
                    _automaticCutMethod,
                    string.IsNullOrWhiteSpace(_automaticCutMethod.Text) ? string.Empty : "AUTO-FILLED",
                    Brushes.Gray);
                SetFieldBadge(
                    _automaticBlipMethod,
                    string.IsNullOrWhiteSpace(_automaticBlipMethod.Text) ? string.Empty : "AUTO-FILLED",
                    Brushes.Gray);
                if (!string.IsNullOrWhiteSpace(results.EvidenceNote))
                {
                    _evidenceNotes.Text = string.IsNullOrWhiteSpace(_evidenceNotes.Text)
                        ? results.EvidenceNote
                        : _evidenceNotes.Text.Trim() + Environment.NewLine + results.EvidenceNote;
                }
                _guidedEvidenceNotes = _evidenceNotes.Text;
            }
            finally
            {
                _applyingGuidedResults = false;
            }
            RefreshManualOverrideBadges();
            _drivingResultsExpander.IsExpanded = GuidedResultsNeedReview();
            UpdateOptionalBadges();
        }

        private bool GuidedResultsNeedReview()
        {
            foreach (ComboBox combo in new[]
            {
                _moveOff, _clutchlessUpshift, _automaticCut,
                _clutchlessDownshift, _automaticBlip
            })
            {
                if (combo == _automaticCut && !AutomaticCutReviewApplies())
                {
                    continue;
                }
                if (combo == _clutchlessDownshift && !DownshiftReviewApplies())
                {
                    continue;
                }
                if (combo == _automaticBlip && !AutomaticBlipReviewApplies())
                {
                    continue;
                }
                if (IsUnresolved(ChoiceValue(combo)))
                {
                    return true;
                }
            }
            return DirectGearSelectionApplies()
                && IsUnresolved(ChoiceValue(_directGearSelection));
        }

        private void UpdateWorkflowGuidance(
            VerificationCaptureContext live,
            GuidedDriveSnapshot guided)
        {
            _captureStart.IsEnabled = live != null;
            SetNextStepButton(_captureStart, false);
            SetNextStepButton(_guidedStart, false);
            SetNextStepButton(_save, false);

            // Each stage shows the controls that stage can act on. A button that
            // cannot be used yet, or whose work is finished, is not merely
            // disabled but absent: this column is 320px wide and every row left
            // standing pushes the next real action further down it.
            SetNextStepButton(_submitSavedDraft, false);
            _observerPanel.Visibility = Visibility.Visible;
            _guidedDrivePanel.Visibility = Visibility.Collapsed;

            if (_capture == null)
            {
                UpdateWorkflowSteps(0, 0);
                _workflowStatus.Text = live == null
                    ? "STEP 1: Load a car in the simulator."
                    : "NEXT STEP: Start verification from the live car.";
                _assistConfirmationHint.Text = "Capture a live car before confirming the test setup.";
                _assistConfirmationHint.Foreground = Brushes.Goldenrod;
                SetNextStepButton(_captureStart, live != null);
                _guidedStart.IsEnabled = false;
                return;
            }

            if (DraftWasSaved())
            {
                UpdateWorkflowSteps(3, 3);
                // Saving is not the end of the contribution, only of the drive,
                // and this used to be the one stage that highlighted nothing.
                // The draft is on this machine and reaches nobody until the
                // submission form is opened, so that button is the next step and
                // is lit like every other next step in this workflow.
                _workflowStatus.Text = "SAVED. NEXT STEP: Open the submission form to share this drive.";
                _assistConfirmationHint.Text = "Simulator assist settings were confirmed for this draft.";
                _assistConfirmationHint.Foreground = Brushes.LightGreen;
                _guidedStart.IsEnabled = false;
                // The name is written into the saved draft and editing it now
                // would change nothing, and the drive controls have nothing left
                // to drive. Collapsing both is what brings the share panel up
                // the column into view rather than below the fold.
                _observerPanel.Visibility = Visibility.Collapsed;
                SetNextStepButton(_submitSavedDraft, true);
                return;
            }

            bool assistsConfirmed = _assistSettingsConfirmed.IsChecked == true;
            _guidedStart.IsEnabled = assistsConfirmed;
            _guidedDrivePanel.Visibility = assistsConfirmed
                ? Visibility.Visible
                : Visibility.Collapsed;
            if (!assistsConfirmed)
            {
                UpdateWorkflowSteps(0, 0);
                _workflowStatus.Text = "NEXT STEP: Verify the simulator setup, then select the green confirmation.";
                _assistConfirmationHint.Text = "REQUIRED ONCE PER SIMULATOR SETUP: Confirm to enable the guided drive.";
                _assistConfirmationHint.Foreground = Brushes.Orange;
                return;
            }

            _assistConfirmationHint.Text = "\u2713 SAVED FOR "
                + _capture.Simulator.ToUpperInvariant()
                + ": Guided drive is enabled.";
            _assistConfirmationHint.Foreground = Brushes.LightGreen;
            if (!_guidedDriveStarted)
            {
                UpdateWorkflowSteps(1, 1);
                _workflowStatus.Text = "NEXT STEP: Start the in-sim guided drive and follow its overlay prompts.";
                SetNextStepButton(_guidedStart, true);
                return;
            }

            if (guided != null && !guided.Completed)
            {
                UpdateWorkflowSteps(1, 1);
                _workflowStatus.Text = "GUIDED DRIVE ACTIVE: Follow the current prompt inside the simulator.";
                return;
            }

            int unresolved = OptionalUnresolvedCount();
            UpdateWorkflowSteps(2, 2);
            _workflowStatus.Text = unresolved == 0
                ? "NEXT STEP: Review the draft, then save it for review."
                : "NEXT STEP: Review the draft. " + unresolved
                    + " optional cockpit/wheel field(s) still need review; incomplete drafts are allowed.";
            if (_save.IsEnabled)
            {
                SetNextStepButton(_save, true);
            }
        }

        private static void SetNextStepButton(Button button, bool active)
        {
            if (button == null)
            {
                return;
            }
            if (active)
            {
                button.Background = new SolidColorBrush(Color.FromRgb(70, 210, 125));
                button.Foreground = new SolidColorBrush(Color.FromRgb(18, 32, 38));
            }
            else
            {
                button.ClearValue(Control.BackgroundProperty);
                button.ClearValue(Control.ForegroundProperty);
            }
            button.BorderBrush = active
                ? Brushes.White
                : new SolidColorBrush(Color.FromArgb(80, 120, 150, 180));
            button.BorderThickness = active ? new Thickness(2) : new Thickness(1);
            button.FontWeight = active ? FontWeights.Bold : FontWeights.Normal;
        }

        private void UpdateWorkflowSteps(int activeIndex, int completedCount)
        {
            if (_workflowSteps == null)
            {
                return;
            }
            for (int index = 0; index < _workflowSteps.Length; index++)
            {
                Button step = _workflowSteps[index];
                bool available = index <= activeIndex || index < completedCount;
                // SimHub's disabled button chrome uses a light fill with pale
                // text, which made future stages nearly disappear. Keep these
                // navigation labels visually enabled but non-interactive until
                // their stage is available.
                step.IsEnabled = true;
                step.IsHitTestVisible = available;
                step.Focusable = available;
                step.Opacity = available ? 1.0 : 0.78;
                if (index < completedCount)
                {
                    step.Foreground = Brushes.LightGreen;
                    step.FontWeight = FontWeights.SemiBold;
                    step.Content = "✓ " + WorkflowStepLabel(index);
                }
                else if (index == activeIndex)
                {
                    step.Foreground = Brushes.White;
                    step.FontWeight = FontWeights.Bold;
                    step.Content = "● " + WorkflowStepLabel(index);
                }
                else
                {
                    step.Foreground = new SolidColorBrush(Color.FromRgb(190, 205, 220));
                    step.FontWeight = FontWeights.Normal;
                    step.Content = "○ " + WorkflowStepLabel(index);
                }
            }
        }

        private static string WorkflowStepLabel(int index)
        {
            switch (index)
            {
                case 0: return "1  Setup";
                case 1: return "2  Guided drive";
                case 2: return "3  Review findings";
                default: return "4  Save and share";
            }
        }

        private void SetupStageClicked(object sender, RoutedEventArgs eventArgs)
        {
            if (_capture != null)
            {
                _assistEditorPanel.Visibility = Visibility.Visible;
                _assistSummaryPanel.Visibility = Visibility.Collapsed;
            }
            _sidebarBorder.BringIntoView();
        }

        private void DriveStageClicked(object sender, RoutedEventArgs eventArgs)
        {
            if (_capture != null && _assistSettingsConfirmed.IsChecked == true)
            {
                _guidedDrivePanel.Visibility = Visibility.Visible;
                _guidedDrivePanel.BringIntoView();
            }
        }

        private void ReviewStageClicked(object sender, RoutedEventArgs eventArgs)
        {
            if (_capture == null)
            {
                return;
            }
            SetReviewVisibility(true);
            _reviewBorder.BringIntoView();
        }

        private void ShareStageClicked(object sender, RoutedEventArgs eventArgs)
        {
            if (DraftWasSaved())
            {
                SetReviewVisibility(false);
                _savedDraftActions.BringIntoView();
                return;
            }
            ReviewStageClicked(sender, eventArgs);
            _save.BringIntoView();
        }

        private void SetReviewVisibility(bool visible)
        {
            _formPanel.Visibility = visible ? Visibility.Visible : Visibility.Collapsed;
            _reviewBorder.Visibility = visible ? Visibility.Visible : Visibility.Collapsed;
            UpdateResponsiveLayout(ActualWidth);
        }

        private void VerificationControlSizeChanged(object sender, SizeChangedEventArgs eventArgs)
        {
            UpdateResponsiveLayout(eventArgs.NewSize.Width);
        }

        private void UpdateResponsiveLayout(double width)
        {
            bool reviewVisible = _reviewBorder.Visibility == Visibility.Visible;
            bool stackedReview = width <= 0 || width < 1000;

            // Before a car is captured there is no review form to occupy the
            // second column. Let the setup workflow use the entire workspace
            // instead of reserving a large blank area beside it.
            if (!reviewVisible)
            {
                _workspace.ColumnDefinitions[0].Width = new GridLength(1, GridUnitType.Star);
                _workspace.ColumnDefinitions[1].Width = new GridLength(0);
                _workspace.ColumnDefinitions[2].Width = new GridLength(0);
                _workspace.RowDefinitions[0].Height = GridLength.Auto;
                _workspace.RowDefinitions[1].Height = new GridLength(0);
                _workspace.RowDefinitions[2].Height = new GridLength(0);
                Grid.SetColumn(_sidebarBorder, 0);
                Grid.SetRow(_sidebarBorder, 0);
                Grid.SetColumnSpan(_sidebarBorder, 3);
                Grid.SetColumn(_reviewBorder, 0);
                Grid.SetRow(_reviewBorder, 2);
                Grid.SetColumnSpan(_reviewBorder, 3);
            }
            else if (stackedReview)
            {
                _workspace.ColumnDefinitions[0].Width = new GridLength(1, GridUnitType.Star);
                _workspace.ColumnDefinitions[1].Width = new GridLength(0);
                _workspace.ColumnDefinitions[2].Width = new GridLength(0);
                _workspace.RowDefinitions[0].Height = GridLength.Auto;
                _workspace.RowDefinitions[1].Height = new GridLength(18);
                _workspace.RowDefinitions[2].Height = GridLength.Auto;
                Grid.SetColumn(_sidebarBorder, 0);
                Grid.SetRow(_sidebarBorder, 0);
                Grid.SetColumnSpan(_sidebarBorder, 3);
                Grid.SetColumn(_reviewBorder, 0);
                Grid.SetRow(_reviewBorder, 2);
                Grid.SetColumnSpan(_reviewBorder, 3);
            }
            else
            {
                // On genuinely wide pages, give both the workflow and review
                // form useful space rather than pinning the workflow to 320px.
                _workspace.ColumnDefinitions[0].Width = new GridLength(2, GridUnitType.Star);
                _workspace.ColumnDefinitions[1].Width = new GridLength(18);
                _workspace.ColumnDefinitions[2].Width = new GridLength(3, GridUnitType.Star);
                _workspace.RowDefinitions[0].Height = GridLength.Auto;
                _workspace.RowDefinitions[1].Height = new GridLength(0);
                _workspace.RowDefinitions[2].Height = new GridLength(0);
                Grid.SetColumn(_sidebarBorder, 0);
                Grid.SetRow(_sidebarBorder, 0);
                Grid.SetColumnSpan(_sidebarBorder, 1);
                Grid.SetColumn(_reviewBorder, 2);
                Grid.SetRow(_reviewBorder, 0);
                Grid.SetColumnSpan(_reviewBorder, 1);
            }
        }

        private void UpdateOptionalBadges()
        {
            foreach (ComboBox combo in new[]
            {
                _primaryActuation, _shiftPattern, _wheelShape, _wheelDisplay,
                _wheelShiftLights, _wheelOpenTop
            })
            {
                ClearFieldBadge(combo);
            }

            // Re-apply the gate badge the mechanism implies. Derived here rather
            // than remembered, so it cannot disagree with the current mechanism.
            string derivedPattern = DerivedShiftPattern(ChoiceValue(_primaryActuation));
            if (derivedPattern != null
                && string.Equals(
                    ChoiceValue(_shiftPattern), derivedPattern, StringComparison.Ordinal))
            {
                SetFieldBadge(_shiftPattern, "DERIVED", Brushes.Gray);
            }

            if (OpenTopIsNotApplicable())
            {
                SetFieldBadge(_wheelOpenTop, "NOT APPLICABLE", Brushes.Gray);
            }

            _visibleHardwareBadge.Text = string.Empty;
            _visibleHardwareBadge.Visibility = Visibility.Collapsed;
            HighlightNextReviewField();
        }

        private static string DerivedShiftPattern(string actuation)
        {
            return ShiftPatternRules.DerivedGate(actuation);
        }

        private static bool IsDerivedGateValue(string value)
        {
            return ShiftPatternRules.IsDerivedGate(value);
        }

        private void HighlightNextReviewField()
        {
            Brush normal = new SolidColorBrush(Color.FromArgb(80, 120, 150, 180));
            _visibleHardwareBorder.BorderBrush = normal;
            _visibleHardwareBorder.BorderThickness = new Thickness(1);
            foreach (ComboBox combo in new[]
            {
                _primaryActuation, _shiftPattern, _wheelShape, _wheelDisplay,
                _wheelShiftLights, _wheelOpenTop, _moveOff,
                _directGearSelection, _clutchlessUpshift, _automaticCut,
                _clutchlessDownshift, _automaticBlip
            })
            {
                combo.BorderBrush = normal;
                combo.BorderThickness = new Thickness(1);
            }

            GuidedDriveSnapshot guided = _plugin.GetGuidedDriveSnapshot();
            if (!_guidedDriveStarted || guided == null || !guided.Completed)
            {
                _reviewHint.Text = "Run the guided drive to populate driving results. Optional review fields will be highlighted here.";
                _reviewHint.Foreground = Brushes.Goldenrod;
                return;
            }

            if (_visiblePaddles.IsChecked != true
                && _visibleSequentialStick.IsChecked != true
                && _visibleHPattern.IsChecked != true
                && _visibleAutomaticLever.IsChecked != true)
            {
                _visibleHardwareBadge.Text = "NEXT";
                _visibleHardwareBadge.Foreground = Brushes.LightGreen;
                _visibleHardwareBadge.Visibility = Visibility.Visible;
                HighlightReviewTarget(
                    _visibleHardwareBorder,
                    "NEXT: Select the shift hardware visible in the cockpit.");
                return;
            }

            foreach (ComboBox combo in new[]
            {
                _primaryActuation, _shiftPattern, _wheelShape, _wheelDisplay,
                _wheelShiftLights, _wheelOpenTop
            })
            {
                if (combo == _wheelOpenTop && !OpenTopApplies())
                {
                    continue;
                }
                if (IsUnresolved(ChoiceValue(combo)))
                {
                    SetFieldBadge(combo, "NEXT", Brushes.LightGreen);
                    HighlightReviewTarget(
                        combo,
                        "NEXT: Review " + OptionalReviewLabel(combo) + ".");
                    return;
                }
            }

            foreach (ComboBox combo in new[]
            {
                _moveOff, _directGearSelection, _clutchlessUpshift,
                _automaticCut, _clutchlessDownshift, _automaticBlip
            })
            {
                if (combo == _directGearSelection && !DirectGearSelectionApplies())
                {
                    continue;
                }
                if (combo == _automaticCut && !AutomaticCutReviewApplies())
                {
                    continue;
                }
                if ((combo == _automaticBlip || combo == _clutchlessDownshift)
                    && !DownshiftReviewApplies())
                {
                    continue;
                }
                if (IsUnresolved(ChoiceValue(combo)))
                {
                    _drivingResultsExpander.IsExpanded = true;
                    HighlightReviewTarget(
                        combo,
                        "NEXT: Review the unresolved guided result for "
                            + ManualOverrideLabel(combo) + ".");
                    return;
                }
            }

            _reviewHint.Text = "\u2713 REVIEW COMPLETE: Save the draft, or add optional notes first.";
            _reviewHint.Foreground = Brushes.LightGreen;
        }

        private bool DirectGearSelectionApplies()
        {
            return VerificationReviewRules.DirectGearSelectionApplies(
                ChoiceValue(_primaryActuation));
        }

        private bool AutomaticCutReviewApplies()
        {
            return VerificationReviewRules.AutomaticCutIsMeasurable(
                _capture == null ? null : _capture.Simulator);
        }

        private bool DownshiftReviewApplies()
        {
            return VerificationReviewRules.DownshiftEngagementIsMeasurable(
                _capture == null ? null : _capture.Simulator);
        }

        private bool AutomaticBlipReviewApplies()
        {
            return DownshiftReviewApplies()
                && VerificationReviewRules.AutomaticBlipIsMeasurable(
                    _capture == null ? null : _capture.Simulator);
        }

        private void HighlightReviewTarget(FrameworkElement control, string message)
        {
            Control field = control as Control;
            Border panel = control as Border;
            if (field != null)
            {
                field.BorderBrush = Brushes.LightGreen;
                field.BorderThickness = new Thickness(2);
            }
            else if (panel != null)
            {
                panel.BorderBrush = Brushes.LightGreen;
                panel.BorderThickness = new Thickness(2);
            }
            _reviewHint.Text = message + " Incomplete drafts are still allowed.";
            _reviewHint.Foreground = Brushes.LightGreen;
            control.Dispatcher.BeginInvoke(
                System.Windows.Threading.DispatcherPriority.Background,
                new Action(delegate { control.BringIntoView(); }));
        }

        private string OptionalReviewLabel(ComboBox combo)
        {
            if (combo == _primaryActuation) return "the primary shift mechanism";
            if (combo == _wheelShape) return "the wheel shape";
            if (combo == _wheelDisplay) return "whether the wheel has a display";
            if (combo == _wheelShiftLights) return "whether the wheel has shift lights";
            if (combo == _wheelOpenTop) return "whether the wheel has an open top";
            return "this field";
        }

        private int OptionalUnresolvedCount()
        {
            int count = 0;
            foreach (ComboBox combo in new[]
            {
                _primaryActuation, _shiftPattern, _wheelShape, _wheelDisplay,
                _wheelShiftLights, _wheelOpenTop
            })
            {
                if (combo == _wheelOpenTop && !OpenTopApplies())
                {
                    continue;
                }
                if (IsUnresolved(ChoiceValue(combo)))
                {
                    count++;
                }
            }
            if (_visiblePaddles.IsChecked != true
                && _visibleSequentialStick.IsChecked != true
                && _visibleHPattern.IsChecked != true
                && _visibleAutomaticLever.IsChecked != true)
            {
                count++;
            }
            return count;
        }

        private void RefreshManualOverrideBadges()
        {
            foreach (ComboBox combo in _manualOverrides.ToArray())
            {
                UpdateManualOverrideBadge(combo);
            }
            bool missingEvidence = MissingManualOverrideEvidence().Length > 0;
            _evidenceNotes.BorderBrush = missingEvidence
                ? Brushes.Orange
                : new SolidColorBrush(Color.FromArgb(80, 120, 150, 180));
            _evidenceNotes.BorderThickness = missingEvidence
                ? new Thickness(2)
                : new Thickness(1);
        }

        private void UpdateManualOverrideBadge(ComboBox combo)
        {
            if (combo == _directGearSelection)
            {
                SetFieldBadge(combo, "MANUAL", Brushes.Gray);
                return;
            }
            bool hasEvidence = HasManualOverrideEvidence(combo);
            SetFieldBadge(
                combo,
                hasEvidence ? "MANUAL · EVIDENCE" : "EVIDENCE REQUIRED",
                hasEvidence ? Brushes.Gray : Brushes.Orange);
        }

        private string[] MissingManualOverrideEvidence()
        {
            return _manualOverrides
                .Where(combo => !HasManualOverrideEvidence(combo))
                .Select(ManualOverrideLabel)
                .OrderBy(label => label, StringComparer.Ordinal)
                .ToArray();
        }

        private bool HasManualOverrideEvidence(ComboBox combo)
        {
            // The explicit direct-selection choice is itself the observation.
            // Unlike cut/blip overrides, it does not need a second evidence note.
            if (combo == _directGearSelection)
            {
                return true;
            }
            string currentNotes = (_evidenceNotes.Text ?? string.Empty).Trim();
            string guidedNotes = (_guidedEvidenceNotes ?? string.Empty).Trim();
            bool reviewNotesChanged = !string.IsNullOrWhiteSpace(currentNotes)
                && !string.Equals(currentNotes, guidedNotes, StringComparison.Ordinal);
            if (reviewNotesChanged)
            {
                return true;
            }
            if (combo == _automaticCut)
            {
                string method = (_automaticCutMethod.Text ?? string.Empty).Trim();
                return !string.IsNullOrWhiteSpace(method)
                    && !string.Equals(
                        method,
                        (_guidedAutomaticCutMethod ?? string.Empty).Trim(),
                        StringComparison.Ordinal);
            }
            if (combo == _automaticBlip)
            {
                string method = (_automaticBlipMethod.Text ?? string.Empty).Trim();
                return !string.IsNullOrWhiteSpace(method)
                    && !string.Equals(
                        method,
                        (_guidedAutomaticBlipMethod ?? string.Empty).Trim(),
                        StringComparison.Ordinal);
            }
            return false;
        }

        private string ManualOverrideLabel(ComboBox combo)
        {
            if (combo == _moveOff) return "move-off result";
            if (combo == _directGearSelection) return "direct H-pattern result";
            if (combo == _clutchlessUpshift) return "clutchless upshift result";
            if (combo == _automaticCut) return "automatic throttle-cut result";
            if (combo == _clutchlessDownshift) return "clutchless downshift result";
            if (combo == _automaticBlip) return "automatic throttle-blip result";
            return "guided result";
        }

        private void SetStatus(string text, Brush foreground, bool emphasized)
        {
            _status.Text = text;
            _status.Foreground = foreground;
            _status.FontSize = emphasized ? 15.0 : 12.0;
            _status.FontWeight = emphasized ? FontWeights.Bold : FontWeights.Normal;
        }

        private string[] VisibleActuators()
        {
            var values = new List<string>();
            if (_visiblePaddles.IsChecked == true) values.Add("paddles");
            if (_visibleSequentialStick.IsChecked == true) values.Add("sequential-stick");
            if (_visibleHPattern.IsChecked == true) values.Add("h-pattern");
            if (_visibleAutomaticLever.IsChecked == true) values.Add("automatic-lever");
            if (values.Count == 0) values.Add("unknown");
            return values.ToArray();
        }

        private void OpenFolderClicked(object sender, RoutedEventArgs eventArgs)
        {
            try
            {
                _status.Text = "Opened drafts folder: " + _plugin.OpenVerificationFolder();
            }
            catch (Exception exception)
            {
                _status.Text = "Could not open the drafts folder: " + exception.Message;
            }
        }

        private void ShowSavedDraftClicked(object sender, RoutedEventArgs eventArgs)
        {
            try
            {
                _plugin.RevealVerificationDraft(_savedDraftPath);
                SetStatus("Selected the saved draft in File Explorer.", Brushes.LightGreen, false);
            }
            catch (Exception exception)
            {
                SetStatus("Could not show the saved draft: " + exception.Message, Brushes.IndianRed, false);
            }
        }

        private void RedactedCopyClicked(object sender, RoutedEventArgs eventArgs)
        {
            try
            {
                string path = VerificationObservationWriter.WriteRedactedCopy(
                    _savedDraftPath);
                _plugin.RevealVerificationDraft(path);
                SetStatus(
                    "Created and selected a redacted copy for public sharing. The original draft was not changed.\n" + path,
                    Brushes.Goldenrod,
                    true);
            }
            catch (Exception exception)
            {
                SetStatus("Could not create the redacted copy: " + exception.Message, Brushes.IndianRed, false);
            }
        }

        private void SubmitSavedDraftClicked(object sender, RoutedEventArgs eventArgs)
        {
            try
            {
                _plugin.RevealVerificationDraft(_savedDraftPath);
                _plugin.OpenObservationSubmissionForm(
                    _capture.SimulatorDisplayName,
                    _capture.TelemetryName);
                SetStatus(
                    "Opened the public simulator-observation form and selected the JSON to attach. Nothing was uploaded automatically.",
                    Brushes.LightGreen,
                    true);
            }
            catch (Exception exception)
            {
                SetStatus("Could not open the contribution form: " + exception.Message, Brushes.IndianRed, false);
            }
        }

        private void PrimaryActuationChanged(object sender, SelectionChangedEventArgs eventArgs)
        {
            string actuation = ChoiceValue(_primaryActuation);
            if (actuation == "sequential-paddles"
                || actuation == "sequential-stick"
                || actuation == "automatic-lever")
            {
                SelectChoice(_directGearSelection, "not-applicable");
                _manualOverrides.Remove(_directGearSelection);
                SetFieldBadge(_directGearSelection, "DERIVED", Brushes.Gray);
            }
            else if ((actuation == "h-pattern" || actuation == "direct-selection")
                && ChoiceValue(_directGearSelection) == "not-applicable")
            {
                SelectChoice(_directGearSelection, "not-tested");
            }
            SetGuidedResultBadge(
                _directGearSelection,
                ChoiceValue(_directGearSelection));

            string derivedPattern = DerivedShiftPattern(actuation);
            if (derivedPattern != null)
            {
                SelectChoice(_shiftPattern, derivedPattern);
            }
            else if (IsDerivedGateValue(ChoiceValue(_shiftPattern)))
            {
                // The mechanism no longer implies a gate, so drop the value it
                // implied rather than leaving the previous mechanism's answer.
                SelectChoice(_shiftPattern, "unknown");
            }
            UpdateOptionalBadges();
        }

        private void AssistSettingsConfirmationChanged(object sender, RoutedEventArgs eventArgs)
        {
            if (!_loadingAssistProfile
                && _capture != null
                && _assistSettingsConfirmed.IsChecked == true)
            {
                _plugin.SaveVerificationAssistProfile(
                    _capture.Simulator,
                    ChoiceValue(_automaticClutch),
                    ChoiceValue(_automaticShifting),
                    ChoiceValue(_automaticThrottleBlip));
            }
            UpdateAssistConfirmationStyle();
            _guidedStart.IsEnabled = _capture != null
                && _assistSettingsConfirmed.IsChecked == true;
            UpdateWorkflowGuidance(
                _plugin.CaptureVerificationContext(),
                _plugin.GetGuidedDriveSnapshot());
        }

        private void AssistChoiceChanged(object sender, SelectionChangedEventArgs eventArgs)
        {
            if (_loadingAssistProfile)
            {
                return;
            }
            if (_assistSettingsConfirmed.IsChecked == true)
            {
                _assistSettingsConfirmed.IsChecked = false;
            }
            UpdateAssistConfirmationStyle();
            UpdateWorkflowGuidance(
                _plugin.CaptureVerificationContext(),
                _plugin.GetGuidedDriveSnapshot());
        }

        private void UpdateAssistConfirmationStyle()
        {
            bool confirmed = _assistSettingsConfirmed.IsChecked == true;
            _assistSettingsConfirmed.BorderBrush = Brushes.LightGreen;
            _assistSettingsConfirmed.BorderThickness = new Thickness(confirmed ? 1 : 2);
            _assistSettingsConfirmed.Background = new SolidColorBrush(
                confirmed
                    ? Color.FromArgb(24, 70, 210, 125)
                    : Color.FromArgb(40, 70, 210, 125));
            _assistSettingsConfirmed.FontWeight = confirmed
                ? FontWeights.Normal
                : FontWeights.Bold;
            _assistEditorPanel.Visibility = confirmed
                ? Visibility.Collapsed
                : Visibility.Visible;
            _assistSummaryPanel.Visibility = confirmed
                ? Visibility.Visible
                : Visibility.Collapsed;
            if (confirmed)
            {
                _assistSummary.Text = "✓ "
                    + (_capture == null
                        ? "Simulator setup confirmed"
                        : _capture.SimulatorDisplayName + " setup confirmed")
                    + "\nAutomatic clutch: " + ChoiceLabel(_automaticClutch)
                    + " · Shifting: " + ChoiceLabel(_automaticShifting)
                    + " · Throttle-blip assist: " + ChoiceLabel(_automaticThrottleBlip);
            }
        }

        private void AssistEditClicked(object sender, RoutedEventArgs eventArgs)
        {
            _assistSettingsConfirmed.IsChecked = false;
            UpdateAssistConfirmationStyle();
            _automaticClutch.Focus();
        }

        private static string ChoiceLabel(ComboBox combo)
        {
            ComboBoxItem item = combo.SelectedItem as ComboBoxItem;
            return item == null ? "Unknown" : Convert.ToString(item.Content, CultureInfo.InvariantCulture);
        }

        private void GuidedChoiceEdited(object sender, SelectionChangedEventArgs eventArgs)
        {
            ComboBox combo = sender as ComboBox;
            if (combo == null || _applyingGuidedResults)
            {
                return;
            }
            string value = ChoiceValue(combo);
            string original;
            if (!_guidedOriginalChoices.TryGetValue(combo, out original))
            {
                if (IsUnresolved(value))
                {
                    SetGuidedResultBadge(combo, value);
                }
                else
                {
                    ClearFieldBadge(combo);
                }
                return;
            }
            if (string.Equals(value, original, StringComparison.Ordinal))
            {
                _manualOverrides.Remove(combo);
                SetGuidedResultBadge(combo, value);
            }
            else if (IsUnresolved(value))
            {
                _manualOverrides.Remove(combo);
                SetGuidedResultBadge(combo, value);
            }
            else
            {
                _manualOverrides.Add(combo);
                UpdateManualOverrideBadge(combo);
            }
        }

        private void GuidedTextEdited(object sender, TextChangedEventArgs eventArgs)
        {
            ClearFieldBadge(sender as Control);
            RefreshManualOverrideBadges();
        }

        private void ManualEvidenceChanged(object sender, TextChangedEventArgs eventArgs)
        {
            RefreshManualOverrideBadges();
        }

        private void OptionalChoiceChanged(object sender, SelectionChangedEventArgs eventArgs)
        {
            if (sender == _wheelShape)
            {
                UpdateWheelOpenTopApplicability();
            }
            UpdateOptionalBadges();
            UpdateWorkflowGuidance(
                _plugin.CaptureVerificationContext(),
                _plugin.GetGuidedDriveSnapshot());
        }

        private bool OpenTopApplies()
        {
            string shape = ChoiceValue(_wheelShape);
            return string.Equals(shape, "round", StringComparison.Ordinal)
                || string.Equals(shape, "d-shaped", StringComparison.Ordinal);
        }

        private bool OpenTopIsNotApplicable()
        {
            string shape = ChoiceValue(_wheelShape);
            return string.Equals(shape, "gt-formula", StringComparison.Ordinal)
                || string.Equals(shape, "gt-style", StringComparison.Ordinal)
                || string.Equals(shape, "prototype", StringComparison.Ordinal)
                || string.Equals(shape, "formula", StringComparison.Ordinal);
        }

        private void UpdateWheelOpenTopApplicability()
        {
            bool applies = OpenTopApplies();
            bool notApplicable = OpenTopIsNotApplicable();
            _wheelOpenTop.IsEnabled = applies;
            if (notApplicable)
            {
                SelectChoice(_wheelOpenTop, "not-applicable");
            }
            else if (!applies
                || string.Equals(ChoiceValue(_wheelOpenTop), "not-applicable", StringComparison.Ordinal))
            {
                SelectChoice(_wheelOpenTop, "not-tested");
            }
        }

        private void VisibleHardwareChanged(object sender, RoutedEventArgs eventArgs)
        {
            UpdateOptionalBadges();
            UpdateWorkflowGuidance(
                _plugin.CaptureVerificationContext(),
                _plugin.GetGuidedDriveSnapshot());
        }

        private void ApplyGuidedChoice(ComboBox combo, string value)
        {
            string normalized = string.IsNullOrWhiteSpace(value) ? "not-tested" : value;
            _guidedOriginalChoices[combo] = normalized;
            SelectChoice(combo, normalized);
            SetGuidedResultBadge(combo, normalized);
        }

        private void SetGuidedResultBadge(ComboBox combo, string value)
        {
            if (combo == _directGearSelection && !DirectGearSelectionApplies())
            {
                SetFieldBadge(
                    combo,
                    string.Equals(value, "not-applicable", StringComparison.Ordinal)
                        ? "DERIVED"
                        : "AFTER MECHANISM",
                    Brushes.Gray);
                return;
            }
            if (combo == _automaticCut
                && !AutomaticCutReviewApplies()
                && IsUnresolved(value))
            {
                SetFieldBadge(combo, "NOT EXPOSED", Brushes.Gray);
                return;
            }
            if ((combo == _automaticBlip || combo == _clutchlessDownshift)
                && !DownshiftReviewApplies())
            {
                SetFieldBadge(combo, "NOT DECIDABLE", Brushes.Gray);
                return;
            }
            if (IsUnresolved(value))
            {
                SetFieldBadge(combo, "REVIEW NEEDED", Brushes.Orange);
            }
            else
            {
                SetFieldBadge(combo, "AUTO-DETECTED", Brushes.Gray);
            }
        }

        private static bool IsUnresolved(string value)
        {
            return string.Equals(value, "unknown", StringComparison.Ordinal)
                || string.Equals(value, "not-tested", StringComparison.Ordinal);
        }

        private static void ClearFieldBadge(Control control)
        {
            SetFieldBadge(control, string.Empty, Brushes.Gray);
        }

        private static void SetFieldBadge(Control control, string text, Brush foreground)
        {
            TextBlock badge = control == null ? null : control.Tag as TextBlock;
            if (badge != null)
            {
                badge.Text = text ?? string.Empty;
                badge.Foreground = foreground ?? Brushes.LightGreen;
                badge.Visibility = string.IsNullOrWhiteSpace(text)
                    ? Visibility.Collapsed
                    : Visibility.Visible;
            }
        }

        private static void AttachBadge(Control control, TextBlock badge)
        {
            badge.FontSize = 12;
            badge.FontWeight = FontWeights.Bold;
            badge.Foreground = Brushes.LightGreen;
            badge.Margin = new Thickness(8, 1, 0, 5);
            badge.Visibility = Visibility.Collapsed;
            control.Tag = badge;
        }

        private static string ChoiceValue(ComboBox combo)
        {
            ComboBoxItem item = combo.SelectedItem as ComboBoxItem;
            return item == null ? string.Empty : Convert.ToString(item.Tag, CultureInfo.InvariantCulture);
        }

        private static void SelectChoice(ComboBox combo, string value)
        {
            foreach (object item in combo.Items)
            {
                ComboBoxItem comboItem = item as ComboBoxItem;
                if (comboItem != null
                    && string.Equals(
                        Convert.ToString(comboItem.Tag, CultureInfo.InvariantCulture),
                        value,
                        StringComparison.Ordinal))
                {
                    combo.SelectedItem = item;
                    return;
                }
            }
        }

    }
}
