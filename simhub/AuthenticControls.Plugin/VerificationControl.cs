using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using AuthenticControls.Core;

namespace AuthenticControls.Plugin
{
    internal sealed class VerificationControl : Border
    {
        private readonly AuthenticControls _plugin;
        private readonly TextBlock _liveAvailability;
        private readonly TextBlock _workflowStatus;
        private readonly TextBlock _capturedIdentity;
        private readonly TextBlock _status;
        private readonly TextBox _observer;
        private readonly TextBox _forwardGears;
        private readonly ComboBox _directGearSelection;
        private readonly ComboBox _automaticClutch;
        private readonly ComboBox _automaticShifting;
        private readonly ComboBox _automaticThrottleBlip;
        private readonly CheckBox _assistSettingsConfirmed;
        private readonly TextBlock _assistConfirmationHint;
        private readonly TextBox _assistNotes;
        private readonly ComboBox _moveOff;
        private readonly ComboBox _clutchlessUpshift;
        private readonly ComboBox _automaticCut;
        private readonly TextBox _automaticCutMethod;
        private readonly ComboBox _clutchlessDownshift;
        private readonly ComboBox _automaticBlip;
        private readonly TextBox _automaticBlipMethod;
        private readonly CheckBox _visiblePaddles;
        private readonly CheckBox _visibleSequentialStick;
        private readonly CheckBox _visibleHPattern;
        private readonly CheckBox _visibleAutomaticLever;
        private readonly TextBlock _visibleHardwareBadge;
        private readonly ComboBox _primaryActuation;
        private readonly TextBox _actuationBasis;
        private readonly ComboBox _wheelShape;
        private readonly ComboBox _wheelDisplay;
        private readonly ComboBox _wheelShiftLights;
        private readonly ComboBox _wheelOpenTop;
        private readonly TextBox _wheelNotes;
        private readonly TextBox _evidenceNotes;
        private readonly Button _save;
        private readonly Button _captureStart;
        private readonly Button _guidedStart;
        private readonly StackPanel _formPanel;
        private readonly TextBlock _reviewHint;
        private readonly Border _visibleHardwareBorder;
        private readonly Expander _drivingResultsExpander;
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

        public VerificationControl(AuthenticControls plugin)
        {
            _plugin = plugin;
            BorderBrush = new SolidColorBrush(Color.FromArgb(80, 120, 150, 180));
            BorderThickness = new Thickness(1);
            CornerRadius = new CornerRadius(5);
            Padding = new Thickness(14);

            var root = new StackPanel();
            root.Children.Add(new TextBlock
            {
                Text = "Capture a versioned draft while a car is loaded. The draft is saved locally for review and never edits the database.",
                FontSize = 15,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 10),
            });
            root.Children.Add(new TextBlock
            {
                Text = "Capture the car, confirm the saved simulator setup, run the in-sim drive, then review only the remaining cockpit details.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.78,
                Margin = new Thickness(0, 0, 0, 12),
            });

            var workspace = new Grid();
            workspace.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(320) });
            workspace.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(18) });
            workspace.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            var sidebar = new StackPanel();
            var form = new StackPanel { Visibility = Visibility.Collapsed };
            _formPanel = form;
            var sidebarBorder = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(18, 50, 190, 235)),
                BorderBrush = new SolidColorBrush(Color.FromArgb(90, 50, 190, 235)),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(6),
                Padding = new Thickness(14),
                Child = sidebar,
            };
            var reviewBorder = new Border
            {
                BorderBrush = new SolidColorBrush(Color.FromArgb(55, 120, 150, 180)),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(6),
                Padding = new Thickness(16),
                Child = form,
            };
            Grid.SetColumn(sidebarBorder, 0);
            Grid.SetColumn(reviewBorder, 2);
            workspace.Children.Add(sidebarBorder);
            workspace.Children.Add(reviewBorder);
            root.Children.Add(workspace);

            _liveAvailability = new TextBlock
            {
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 8),
            };
            sidebar.Children.Add(_liveAvailability);
            _workflowStatus = new TextBlock
            {
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
                Foreground = new SolidColorBrush(Color.FromRgb(50, 190, 235)),
                Margin = new Thickness(0, 0, 0, 8),
            };
            sidebar.Children.Add(_workflowStatus);
            _captureStart = CreateButton(
                "Start verification from live car",
                235,
                StartClicked,
                new Thickness(0, 0, 0, 10));
            sidebar.Children.Add(_captureStart);
            _capturedIdentity = new TextBlock
            {
                Text = "No verification started.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.78,
                Margin = new Thickness(0, 0, 0, 12),
            };
            sidebar.Children.Add(_capturedIdentity);

            _observer = CreateTextBox();
            _observer.Text = plugin.VerificationObserver;
            AddLabeledControl(
                sidebar,
                "Observer name",
                _observer,
                null);

            AddSubheading(sidebar, "Workflow");
            sidebar.Children.Add(new TextBlock
            {
                Text = "1  Capture\n2  Confirm setup\n3  Guided drive\n4  Review and save",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.82,
                Margin = new Thickness(0, 0, 0, 10),
            });

            AddSubheading(sidebar, "Simulator test setup");
            sidebar.Children.Add(new TextBlock
            {
                Text = "These are simulator assists, not systems built into the car. A confirmed profile is reused for this simulator.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.72,
                Margin = new Thickness(0, 0, 0, 10),
            });
            _automaticClutch = CreateAssistCombo();
            _automaticShifting = CreateAssistCombo();
            _automaticThrottleBlip = CreateAssistCombo();
            _automaticClutch.SelectionChanged += AssistChoiceChanged;
            _automaticShifting.SelectionChanged += AssistChoiceChanged;
            _automaticThrottleBlip.SelectionChanged += AssistChoiceChanged;
            AddLabeledControl(sidebar, "Automatic clutch", _automaticClutch, null);
            AddLabeledControl(sidebar, "Automatic shifting", _automaticShifting, null);
            AddLabeledControl(
                sidebar,
                "Automatic throttle-blip assist",
                _automaticThrottleBlip,
                null);
            _assistSettingsConfirmed = CreateCheckBox(
                "Use this verified setup");
            _assistSettingsConfirmed.Margin = new Thickness(0, 0, 0, 8);
            _assistSettingsConfirmed.Padding = new Thickness(8);
            sidebar.Children.Add(_assistSettingsConfirmed);
            _assistConfirmationHint = new TextBlock
            {
                TextWrapping = TextWrapping.Wrap,
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 0, 0, 10),
            };
            sidebar.Children.Add(_assistConfirmationHint);
            sidebar.Children.Add(new TextBlock
            {
                Text = "For AMS2 the recommended setup is Disabled / Disabled / Unavailable. Review it once; changing a value requires reconfirmation.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.68,
                Margin = new Thickness(0, 0, 0, 10),
            });
            _assistNotes = CreateMultilineTextBox(54);
            AddLabeledControl(sidebar, "Assist notes", _assistNotes, null);

            var guidedActions = new WrapPanel { Margin = new Thickness(0, 2, 0, 8) };
            _guidedStart = CreateButton(
                "Start in-sim guided drive",
                205,
                GuidedStartClicked,
                new Thickness(0, 0, 10, 6));
            _guidedStart.IsEnabled = false;
            _assistSettingsConfirmed.Checked += AssistSettingsConfirmationChanged;
            _assistSettingsConfirmed.Unchecked += AssistSettingsConfirmationChanged;
            guidedActions.Children.Add(_guidedStart);
            guidedActions.Children.Add(CreateButton(
                "Cancel",
                85,
                GuidedCancelClicked,
                new Thickness(0, 0, 0, 6)));
            sidebar.Children.Add(guidedActions);
            sidebar.Children.Add(new TextBlock
            {
                Text = "For in-car use, map AuthenticControls.VerificationDriveNext, AuthenticControls.VerificationDriveRetry, AuthenticControls.VerificationDriveSkip, and AuthenticControls.VerificationDriveCancel under SimHub Controls and events. Driving results are suggestions until you review and save the draft.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.65,
                Margin = new Thickness(0, 0, 0, 12),
            });

            _reviewHint = new TextBlock
            {
                Text = "Run the guided drive to populate driving results. Optional review fields will be highlighted here.",
                TextWrapping = TextWrapping.Wrap,
                FontWeight = FontWeights.SemiBold,
                Foreground = Brushes.Goldenrod,
                Margin = new Thickness(0, 0, 0, 10),
            };
            form.Children.Add(_reviewHint);

            var drivingPanel = new StackPanel();
            _drivingResultsExpander = new Expander
            {
                Header = "Guided driving results (expand to review)",
                IsExpanded = false,
                Content = drivingPanel,
                Margin = new Thickness(0, 4, 0, 10),
            };
            form.Children.Add(_drivingResultsExpander);
            _moveOff = CreateObservedCombo();
            _forwardGears = CreateTextBox();
            AddControlPair(
                drivingPanel,
                "Moves from rest without physical clutch",
                _moveOff,
                "Forward gears",
                _forwardGears);
            _directGearSelection = CreateDirectSelectionCombo();
            AddLabeledControl(
                drivingPanel,
                "Direct H-pattern selection confirmed",
                _directGearSelection,
                "For an H-pattern car, verify that a non-adjacent requested gear engages directly rather than stepping sequentially.");
            _clutchlessUpshift = CreateObservedCombo();
            _automaticCut = CreateObservedCombo();
            AddControlPair(
                drivingPanel,
                "Clutchless upshift accepted",
                _clutchlessUpshift,
                "Automatic throttle cut observed",
                _automaticCut);
            _automaticCutMethod = CreateTextBox();
            AddLabeledControl(
                drivingPanel,
                "How automatic cut was identified",
                _automaticCutMethod,
                "For example: full-throttle shift accepted with a visible power interruption.");
            _clutchlessDownshift = CreateObservedCombo();
            _automaticBlip = CreateObservedCombo();
            AddControlPair(
                drivingPanel,
                "Clutchless downshift accepted",
                _clutchlessDownshift,
                "Automatic throttle blip observed",
                _automaticBlip);
            _automaticBlipMethod = CreateTextBox();
            AddLabeledControl(
                drivingPanel,
                "How automatic blip was identified",
                _automaticBlipMethod,
                "For example: throttle telemetry spiked during a downshift without pedal input.");
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

            AddSubheading(form, "Cockpit controls");
            form.Children.Add(new TextBlock
            {
                Text = "A sequential gearbox may accept both paddle and stick bindings in AMS2. Use visible hardware and driver animation to identify the modeled primary mechanism.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.72,
                Margin = new Thickness(0, 0, 0, 10),
            });
            var visibleHardwareLabel = new StackPanel { Orientation = Orientation.Horizontal };
            visibleHardwareLabel.Children.Add(new TextBlock
            {
                Text = "Visible shift hardware",
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 0, 0, 6),
            });
            _visibleHardwareBadge = new TextBlock
            {
                FontSize = 10,
                FontWeight = FontWeights.Bold,
                Foreground = Brushes.Orange,
                Margin = new Thickness(8, 1, 0, 6),
            };
            visibleHardwareLabel.Children.Add(_visibleHardwareBadge);
            form.Children.Add(visibleHardwareLabel);
            var actuatorRow = new WrapPanel { Margin = new Thickness(0, 0, 0, 12) };
            _visiblePaddles = CreateCheckBox("Paddles");
            _visibleSequentialStick = CreateCheckBox("Sequential stick");
            _visibleHPattern = CreateCheckBox("H-pattern shifter");
            _visibleAutomaticLever = CreateCheckBox("Automatic lever");
            foreach (CheckBox visibleControl in new[]
            {
                _visiblePaddles, _visibleSequentialStick,
                _visibleHPattern, _visibleAutomaticLever
            })
            {
                visibleControl.Checked += VisibleHardwareChanged;
                visibleControl.Unchecked += VisibleHardwareChanged;
            }
            actuatorRow.Children.Add(_visiblePaddles);
            actuatorRow.Children.Add(_visibleSequentialStick);
            actuatorRow.Children.Add(_visibleHPattern);
            actuatorRow.Children.Add(_visibleAutomaticLever);
            _visibleHardwareBorder = new Border
            {
                BorderBrush = new SolidColorBrush(Color.FromArgb(80, 120, 150, 180)),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(4),
                Padding = new Thickness(6),
                Margin = new Thickness(0, 0, 0, 12),
                Child = actuatorRow,
            };
            form.Children.Add(_visibleHardwareBorder);
            _primaryActuation = CreateChoiceCombo(new[]
            {
                new Choice("Unknown", "unknown"),
                new Choice("Sequential paddles", "sequential-paddles"),
                new Choice("Sequential stick", "sequential-stick"),
                new Choice("H-pattern", "h-pattern"),
                new Choice("Automatic lever", "automatic-lever"),
                new Choice("Direct selection", "direct-selection"),
            });
            _primaryActuation.SelectionChanged += PrimaryActuationChanged;
            _actuationBasis = CreateTextBox();
            _actuationBasis.TextChanged += ManualEvidenceChanged;
            AddControlPair(
                form,
                "Primary shift mechanism",
                _primaryActuation,
                "How it was identified",
                _actuationBasis);

            AddSubheading(form, "Steering wheel");
            _wheelShape = CreateChoiceCombo(new[]
            {
                new Choice("Unknown", "unknown"),
                new Choice("Round", "round"),
                new Choice("D-shaped", "d-shaped"),
                new Choice("GT-style", "gt-style"),
                new Choice("Prototype", "prototype"),
                new Choice("Formula", "formula"),
                new Choice("Yoke", "yoke"),
                new Choice("Other", "other"),
            });
            _wheelDisplay = CreateObservedCombo();
            AddControlPair(
                form,
                "Wheel shape",
                _wheelShape,
                "Integrated display",
                _wheelDisplay);
            _wheelShiftLights = CreateObservedCombo();
            _wheelOpenTop = CreateObservedCombo();
            AddControlPair(
                form,
                "Shift lights on wheel",
                _wheelShiftLights,
                "Open-top wheel construction",
                _wheelOpenTop);
            _wheelNotes = CreateMultilineTextBox(54);
            AddLabeledControl(form, "Wheel notes", _wheelNotes, null);
            foreach (ComboBox optionalChoice in new[]
            {
                _primaryActuation, _wheelShape, _wheelDisplay,
                _wheelShiftLights, _wheelOpenTop
            })
            {
                optionalChoice.SelectionChanged += OptionalChoiceChanged;
            }

            AddSubheading(form, "Review notes");
            _evidenceNotes = CreateMultilineTextBox(72);
            AddLabeledControl(
                form,
                "Anything a reviewer should know",
                _evidenceNotes,
                "Include uncertainty, unusual hybrid starts, conflicting cockpit hardware, or tests that should be repeated.");
            _evidenceNotes.TextChanged += ManualEvidenceChanged;

            var actions = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                Margin = new Thickness(0, 4, 0, 8),
            };
            _save = CreateButton(
                "Save draft observation",
                190,
                SaveClicked,
                new Thickness(0, 0, 10, 0));
            _save.IsEnabled = false;
            actions.Children.Add(_save);
            actions.Children.Add(CreateButton(
                "Open drafts folder",
                160,
                OpenFolderClicked,
                new Thickness(0)));
            form.Children.Add(actions);
            form.Children.Add(new TextBlock
            {
                Text = plugin.VerificationDraftDirectory,
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.62,
                Margin = new Thickness(0, 0, 0, 6),
            });
            _status = new TextBlock
            {
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 4, 0, 0),
            };
            sidebar.Children.Add(_status);
            Child = root;
            UpdateAssistConfirmationStyle();
            UpdateLiveAvailability();
        }

        internal void UpdateLiveAvailability()
        {
            VerificationCaptureContext live = _plugin.CaptureVerificationContext();
            _liveAvailability.Text = live == null
                ? "Waiting for a live car. Start the simulator and load a car first."
                : "Ready to capture: " + live.TelemetryName + " - " + live.TelemetryClass
                    + " (" + live.SimulatorDisplayName + " " + live.GameVersion + ")";
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
                        _capturedIdentity.Text = "Captured: " + _capture.TelemetryName + " - "
                            + _capture.TelemetryClass + " | " + _capture.SimulatorDisplayName + " "
                            + _capture.GameVersion + " | " + _capture.ClientVersion;
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
                _formPanel.Visibility = Visibility.Visible;
                SetStatus("Guided drive complete. Suggested driving results were filled in; review the cockpit and wheel fields before saving.", Brushes.LightGreen, true);
            }
            UpdateWorkflowGuidance(live, guided);
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
            _formPanel.Visibility = Visibility.Visible;
            _capturedIdentity.Text = "Captured: " + live.TelemetryName + " - "
                + live.TelemetryClass + " | " + live.SimulatorDisplayName + " " + live.GameVersion + " | "
                + live.ClientVersion;
            _save.IsEnabled = true;
            SetStatus(live.SuggestedForwardGears.HasValue
                ? "Verification started. SimHub suggested " + live.SuggestedForwardGears.Value
                    + " forward gears; confirm it by selecting every gear."
                : "Verification started. Complete the form, then save a draft.", Brushes.LightGreen, false);
            UpdateWorkflowGuidance(_plugin.CaptureVerificationContext(), _plugin.GetGuidedDriveSnapshot());
        }

        private void ResetForm()
        {
            _loadingAssistProfile = true;
            foreach (ComboBox combo in new[]
            {
                _automaticClutch, _automaticShifting, _automaticThrottleBlip,
                _moveOff, _directGearSelection, _clutchlessUpshift, _automaticCut,
                _clutchlessDownshift, _automaticBlip, _primaryActuation,
                _wheelShape, _wheelDisplay, _wheelShiftLights, _wheelOpenTop
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
            _evidenceNotes.BorderThickness = new Thickness(1);
            _evidenceNotes.BorderBrush = new SolidColorBrush(Color.FromArgb(80, 120, 150, 180));
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
                    GameVersion = _capture.GameVersion,
                    ClientVersion = _capture.ClientVersion,
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
                    VisibleShiftActuators = visible,
                    PrimaryShiftActuation = ChoiceValue(_primaryActuation),
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
                _capturedIdentity.Text = "Completed: " + _capture.TelemetryName
                    + " - draft saved for review.";
                SetStatus("\u2713 DRAFT SAVED SUCCESSFULLY\n" + path, Brushes.LightGreen, true);
                _save.IsEnabled = false;
                _formPanel.Visibility = Visibility.Collapsed;
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
                if (results.ForwardGears.HasValue)
                {
                    _forwardGears.Text = results.ForwardGears.Value.ToString(CultureInfo.InvariantCulture);
                    SetFieldBadge(_forwardGears, "AUTO-DETECTED", Brushes.LightGreen);
                }
                _automaticCutMethod.Text = results.AutomaticCutMethod ?? string.Empty;
                _automaticBlipMethod.Text = results.AutomaticBlipMethod ?? string.Empty;
                _guidedAutomaticCutMethod = _automaticCutMethod.Text;
                _guidedAutomaticBlipMethod = _automaticBlipMethod.Text;
                SetFieldBadge(
                    _automaticCutMethod,
                    string.IsNullOrWhiteSpace(_automaticCutMethod.Text) ? string.Empty : "AUTO-FILLED",
                    Brushes.LightSkyBlue);
                SetFieldBadge(
                    _automaticBlipMethod,
                    string.IsNullOrWhiteSpace(_automaticBlipMethod.Text) ? string.Empty : "AUTO-FILLED",
                    Brushes.LightSkyBlue);
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
            UpdateOptionalBadges();
        }

        private void UpdateWorkflowGuidance(
            VerificationCaptureContext live,
            GuidedDriveSnapshot guided)
        {
            _captureStart.IsEnabled = live != null;
            SetNextStepButton(_captureStart, false);
            SetNextStepButton(_guidedStart, false);
            SetNextStepButton(_save, false);

            if (_capture == null)
            {
                _workflowStatus.Text = live == null
                    ? "STEP 1: Load a car in the simulator."
                    : "NEXT STEP: Start verification from the live car.";
                _assistConfirmationHint.Text = "Capture a live car before confirming the test setup.";
                _assistConfirmationHint.Foreground = Brushes.Goldenrod;
                SetNextStepButton(_captureStart, live != null);
                _guidedStart.IsEnabled = false;
                return;
            }

            if (!_save.IsEnabled
                && _capturedIdentity.Text.StartsWith("Completed:", StringComparison.Ordinal))
            {
                _workflowStatus.Text = "COMPLETE: The local draft was saved for review.";
                _assistConfirmationHint.Text = "Simulator assist settings were confirmed for this draft.";
                _assistConfirmationHint.Foreground = Brushes.LightGreen;
                _guidedStart.IsEnabled = false;
                return;
            }

            bool assistsConfirmed = _assistSettingsConfirmed.IsChecked == true;
            _guidedStart.IsEnabled = assistsConfirmed;
            if (!assistsConfirmed)
            {
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
                _workflowStatus.Text = "NEXT STEP: Start the in-sim guided drive and follow its overlay prompts.";
                SetNextStepButton(_guidedStart, true);
                return;
            }

            if (guided != null && !guided.Completed)
            {
                _workflowStatus.Text = "GUIDED DRIVE ACTIVE: Follow the current prompt inside the simulator.";
                return;
            }

            int unresolved = OptionalUnresolvedCount();
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
            button.BorderBrush = active
                ? Brushes.LightGreen
                : new SolidColorBrush(Color.FromArgb(80, 120, 150, 180));
            button.BorderThickness = active ? new Thickness(2) : new Thickness(1);
            button.FontWeight = active ? FontWeights.Bold : FontWeights.Normal;
        }

        private void UpdateOptionalBadges()
        {
            foreach (ComboBox combo in new[]
            {
                _primaryActuation, _wheelShape, _wheelDisplay,
                _wheelShiftLights, _wheelOpenTop
            })
            {
                bool unresolved = IsUnresolved(ChoiceValue(combo));
                SetFieldBadge(
                    combo,
                    unresolved ? "OPTIONAL · REVIEW" : "REVIEWED",
                    unresolved ? Brushes.Orange : Brushes.LightGreen);
            }

            bool hardwareSpecified = _visiblePaddles.IsChecked == true
                || _visibleSequentialStick.IsChecked == true
                || _visibleHPattern.IsChecked == true
                || _visibleAutomaticLever.IsChecked == true;
            _visibleHardwareBadge.Text = hardwareSpecified
                ? "REVIEWED"
                : "OPTIONAL · REVIEW";
            _visibleHardwareBadge.Foreground = hardwareSpecified
                ? Brushes.LightGreen
                : Brushes.Orange;
            HighlightNextReviewField();
        }

        private void HighlightNextReviewField()
        {
            Brush normal = new SolidColorBrush(Color.FromArgb(80, 120, 150, 180));
            _visibleHardwareBorder.BorderBrush = normal;
            _visibleHardwareBorder.BorderThickness = new Thickness(1);
            foreach (ComboBox combo in new[]
            {
                _primaryActuation, _wheelShape, _wheelDisplay,
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
                HighlightReviewTarget(
                    _visibleHardwareBorder,
                    "NEXT: Select the shift hardware visible in the cockpit.");
                return;
            }

            foreach (ComboBox combo in new[]
            {
                _primaryActuation, _wheelShape, _wheelDisplay,
                _wheelShiftLights, _wheelOpenTop
            })
            {
                if (IsUnresolved(ChoiceValue(combo)))
                {
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
                _primaryActuation, _wheelShape, _wheelDisplay,
                _wheelShiftLights, _wheelOpenTop
            })
            {
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
            bool hasEvidence = HasManualOverrideEvidence(combo);
            SetFieldBadge(
                combo,
                hasEvidence ? "MANUAL · EVIDENCE" : "EVIDENCE REQUIRED",
                hasEvidence ? Brushes.LightSkyBlue : Brushes.Orange);
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
            if (combo == _directGearSelection)
            {
                return !string.IsNullOrWhiteSpace(_actuationBasis.Text);
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

        private static void AddSubheading(Panel panel, string text)
        {
            panel.Children.Add(new TextBlock
            {
                Text = text,
                FontSize = 16,
                FontWeight = FontWeights.SemiBold,
                Foreground = new SolidColorBrush(Color.FromRgb(50, 190, 235)),
                Margin = new Thickness(0, 18, 0, 10),
            });
        }

        private static void AddControlPair(
            Panel panel,
            string leftLabel,
            Control left,
            string rightLabel,
            Control right)
        {
            var grid = new Grid { Margin = new Thickness(0, 0, 0, 12) };
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(16) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            StackPanel leftPanel = LabeledPanel(leftLabel, left);
            StackPanel rightPanel = LabeledPanel(rightLabel, right);
            Grid.SetColumn(leftPanel, 0);
            Grid.SetColumn(rightPanel, 2);
            grid.Children.Add(leftPanel);
            grid.Children.Add(rightPanel);
            panel.Children.Add(grid);
        }

        private static void AddLabeledControl(
            Panel panel,
            string label,
            Control control,
            string help)
        {
            StackPanel holder = LabeledPanel(label, control);
            if (!string.IsNullOrWhiteSpace(help))
            {
                holder.Children.Add(new TextBlock
                {
                    Text = help,
                    TextWrapping = TextWrapping.Wrap,
                    Opacity = 0.65,
                    Margin = new Thickness(0, 4, 0, 0),
                });
            }
            holder.Margin = new Thickness(0, 0, 0, 12);
            panel.Children.Add(holder);
        }

        private static StackPanel LabeledPanel(string label, Control control)
        {
            var holder = new StackPanel();
            var labelRow = new StackPanel { Orientation = Orientation.Horizontal };
            labelRow.Children.Add(new TextBlock
            {
                Text = label,
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 0, 0, 5),
            });
            var fieldBadge = new TextBlock
            {
                Text = string.Empty,
                FontSize = 10,
                FontWeight = FontWeights.Bold,
                Foreground = Brushes.LightGreen,
                Margin = new Thickness(8, 1, 0, 5),
                Visibility = Visibility.Collapsed,
            };
            labelRow.Children.Add(fieldBadge);
            control.Tag = fieldBadge;
            holder.Children.Add(labelRow);
            holder.Children.Add(control);
            return holder;
        }

        private static ComboBox CreateAssistCombo()
        {
            return CreateChoiceCombo(new[]
            {
                new Choice("Unknown", "unknown"),
                new Choice("Disabled", "disabled"),
                new Choice("Enabled", "enabled"),
                new Choice("Unavailable", "unavailable"),
            });
        }

        private static ComboBox CreateObservedCombo()
        {
            return CreateChoiceCombo(new[]
            {
                new Choice("Not tested", "not-tested"),
                new Choice("Yes", "yes"),
                new Choice("No", "no"),
                new Choice("Unknown", "unknown"),
            });
        }

        private static ComboBox CreateDirectSelectionCombo()
        {
            return CreateChoiceCombo(new[]
            {
                new Choice("Not tested", "not-tested"),
                new Choice("Not applicable", "not-applicable"),
                new Choice("Yes", "yes"),
                new Choice("No", "no"),
                new Choice("Unknown", "unknown"),
            });
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
                SetFieldBadge(_directGearSelection, "DERIVED", Brushes.LightSkyBlue);
            }
            else if ((actuation == "h-pattern" || actuation == "direct-selection")
                && ChoiceValue(_directGearSelection) == "not-applicable")
            {
                SelectChoice(_directGearSelection, "not-tested");
                SetFieldBadge(_directGearSelection, "REVIEW NEEDED", Brushes.Orange);
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
                    SetFieldBadge(combo, "REVIEW NEEDED", Brushes.Orange);
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
                SetFieldBadge(combo, "REVIEW NEEDED", Brushes.Orange);
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
            UpdateOptionalBadges();
            UpdateWorkflowGuidance(
                _plugin.CaptureVerificationContext(),
                _plugin.GetGuidedDriveSnapshot());
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

        private static void SetGuidedResultBadge(ComboBox combo, string value)
        {
            if (IsUnresolved(value))
            {
                SetFieldBadge(combo, "REVIEW NEEDED", Brushes.Orange);
            }
            else
            {
                SetFieldBadge(combo, "AUTO-DETECTED", Brushes.LightGreen);
            }
        }

        private static bool IsUnresolved(string value)
        {
            return string.Equals(value, "unknown", StringComparison.Ordinal)
                || string.Equals(value, "not-tested", StringComparison.Ordinal);
        }

        private static void ClearFieldBadge(Control control)
        {
            SetFieldBadge(control, string.Empty, Brushes.LightGreen);
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

        private static ComboBox CreateChoiceCombo(IEnumerable<Choice> choices)
        {
            var combo = new ComboBox
            {
                Height = 30,
                HorizontalAlignment = HorizontalAlignment.Stretch,
            };
            foreach (Choice choice in choices)
            {
                combo.Items.Add(choice);
            }
            combo.SelectedIndex = 0;
            return combo;
        }

        private static TextBox CreateTextBox()
        {
            return new TextBox
            {
                Height = 30,
                VerticalContentAlignment = VerticalAlignment.Center,
            };
        }

        private static TextBox CreateMultilineTextBox(double height)
        {
            return new TextBox
            {
                Height = height,
                AcceptsReturn = true,
                TextWrapping = TextWrapping.Wrap,
                VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            };
        }

        private static CheckBox CreateCheckBox(string label)
        {
            return new CheckBox
            {
                Content = label,
                Margin = new Thickness(0, 0, 20, 6),
            };
        }

        private static Button CreateButton(
            string label,
            double width,
            RoutedEventHandler handler,
            Thickness margin)
        {
            var button = new Button
            {
                Content = label,
                Width = width,
                Height = 32,
                HorizontalAlignment = HorizontalAlignment.Left,
                Margin = margin,
            };
            button.Click += handler;
            return button;
        }

        private static string ChoiceValue(ComboBox combo)
        {
            Choice choice = combo.SelectedItem as Choice;
            return choice == null ? string.Empty : choice.Value;
        }

        private static void SelectChoice(ComboBox combo, string value)
        {
            foreach (object item in combo.Items)
            {
                Choice choice = item as Choice;
                if (choice != null
                    && string.Equals(choice.Value, value, StringComparison.Ordinal))
                {
                    combo.SelectedItem = item;
                    return;
                }
            }
        }

        private sealed class Choice
        {
            public Choice(string label, string value)
            {
                Label = label;
                Value = value;
            }

            public string Label { get; private set; }
            public string Value { get; private set; }

            public override string ToString()
            {
                return Label;
            }
        }
    }
}
