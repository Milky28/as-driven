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
        private readonly TextBlock _capturedIdentity;
        private readonly TextBlock _status;
        private readonly TextBox _observer;
        private readonly TextBox _forwardGears;
        private readonly ComboBox _directGearSelection;
        private readonly ComboBox _automaticClutch;
        private readonly ComboBox _automaticShifting;
        private readonly ComboBox _automaticThrottleBlip;
        private readonly CheckBox _assistSettingsConfirmed;
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
        private readonly ComboBox _primaryActuation;
        private readonly TextBox _actuationBasis;
        private readonly ComboBox _wheelShape;
        private readonly ComboBox _wheelDisplay;
        private readonly ComboBox _wheelShiftLights;
        private readonly ComboBox _wheelOpenTop;
        private readonly TextBox _wheelNotes;
        private readonly TextBox _evidenceNotes;
        private readonly Button _save;
        private readonly Expander _formExpander;
        private VerificationCaptureContext _capture;
        private bool _guidedDriveApplied;

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
                Text = "Before testing, disable automatic clutch and automatic shifting where available. Leave anything uncertain as Unknown or Not tested.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.78,
                Margin = new Thickness(0, 0, 0, 12),
            });
            _liveAvailability = new TextBlock
            {
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 8),
            };
            root.Children.Add(_liveAvailability);
            root.Children.Add(CreateButton(
                "Start verification from live car",
                235,
                StartClicked,
                new Thickness(0, 0, 0, 10)));
            _capturedIdentity = new TextBlock
            {
                Text = "No verification started.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.78,
                Margin = new Thickness(0, 0, 0, 12),
            };
            root.Children.Add(_capturedIdentity);

            var form = new StackPanel();
            _formExpander = new Expander
            {
                Header = "Verification form",
                IsExpanded = false,
                Content = form,
                Margin = new Thickness(0, 0, 0, 10),
            };
            root.Children.Add(_formExpander);

            _observer = CreateTextBox();
            _observer.Text = plugin.VerificationObserver;
            AddLabeledControl(
                form,
                "Observer name",
                _observer,
                "Saved with the draft so a later reviewer knows who performed the test.");

            AddSubheading(form, "Tester workflow");
            form.Children.Add(new TextBlock
            {
                Text = "1. Capture the live car.\n2. Verify the simulator assist settings below.\n3. Start the in-sim guided drive.\n4. Prepare and perform each prompted maneuver; accept, retry, or skip its result.\n5. Return here to identify cockpit controls and wheel details.\n6. Review the suggestions and save the draft.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.82,
                Margin = new Thickness(0, 0, 0, 10),
            });

            AddSubheading(form, "Simulator assist settings");
            form.Children.Add(new TextBlock
            {
                Text = "Confirm the assist settings currently selected inside the simulator. These describe the test setup, not systems built into the car.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.72,
                Margin = new Thickness(0, 0, 0, 10),
            });
            _automaticClutch = CreateAssistCombo();
            _automaticShifting = CreateAssistCombo();
            _automaticThrottleBlip = CreateAssistCombo();
            AddControlPair(
                form,
                "Automatic clutch",
                _automaticClutch,
                "Automatic shifting",
                _automaticShifting);
            AddLabeledControl(
                form,
                "Automatic throttle-blip assist",
                _automaticThrottleBlip,
                "Choose Unavailable if the simulator has no separate assist setting.");
            _assistSettingsConfirmed = CreateCheckBox(
                "I verified these values against the simulator's current settings.");
            _assistSettingsConfirmed.Margin = new Thickness(0, 0, 0, 8);
            form.Children.Add(_assistSettingsConfirmed);
            form.Children.Add(new TextBlock
            {
                Text = "AMS2 starts with the recommended test values: automatic clutch Disabled, automatic shifting Disabled, and throttle-blip assist Unavailable. Change a value to the actual state if you cannot use the recommendation, and explain the limitation below.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.68,
                Margin = new Thickness(0, 0, 0, 10),
            });
            _assistNotes = CreateMultilineTextBox(54);
            AddLabeledControl(form, "Assist notes", _assistNotes, null);

            var guidedActions = new WrapPanel { Margin = new Thickness(0, 2, 0, 8) };
            guidedActions.Children.Add(CreateButton(
                "Start in-sim guided drive",
                205,
                GuidedStartClicked,
                new Thickness(0, 0, 10, 6)));
            guidedActions.Children.Add(CreateButton(
                "Next / accept",
                125,
                GuidedNextClicked,
                new Thickness(0, 0, 10, 6)));
            guidedActions.Children.Add(CreateButton(
                "Retry",
                85,
                GuidedRetryClicked,
                new Thickness(0, 0, 10, 6)));
            guidedActions.Children.Add(CreateButton(
                "Skip",
                80,
                GuidedSkipClicked,
                new Thickness(0, 0, 10, 6)));
            guidedActions.Children.Add(CreateButton(
                "Cancel",
                85,
                GuidedCancelClicked,
                new Thickness(0, 0, 0, 6)));
            form.Children.Add(guidedActions);
            form.Children.Add(new TextBlock
            {
                Text = "For in-car use, map AuthenticControls.VerificationDriveNext, AuthenticControls.VerificationDriveRetry, AuthenticControls.VerificationDriveSkip, and AuthenticControls.VerificationDriveCancel under SimHub Controls and events. Driving results are suggestions until you review and save the draft.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.65,
                Margin = new Thickness(0, 0, 0, 12),
            });

            AddSubheading(form, "Driving tests");
            _moveOff = CreateObservedCombo();
            _forwardGears = CreateTextBox();
            AddControlPair(
                form,
                "Moves from rest without physical clutch",
                _moveOff,
                "Forward gears",
                _forwardGears);
            _directGearSelection = CreateDirectSelectionCombo();
            AddLabeledControl(
                form,
                "Direct H-pattern selection confirmed",
                _directGearSelection,
                "For an H-pattern car, verify that a non-adjacent requested gear engages directly rather than stepping sequentially.");
            _clutchlessUpshift = CreateObservedCombo();
            _automaticCut = CreateObservedCombo();
            AddControlPair(
                form,
                "Clutchless upshift accepted",
                _clutchlessUpshift,
                "Automatic throttle cut observed",
                _automaticCut);
            _automaticCutMethod = CreateTextBox();
            AddLabeledControl(
                form,
                "How automatic cut was identified",
                _automaticCutMethod,
                "For example: full-throttle shift accepted with a visible power interruption.");
            _clutchlessDownshift = CreateObservedCombo();
            _automaticBlip = CreateObservedCombo();
            AddControlPair(
                form,
                "Clutchless downshift accepted",
                _clutchlessDownshift,
                "Automatic throttle blip observed",
                _automaticBlip);
            _automaticBlipMethod = CreateTextBox();
            AddLabeledControl(
                form,
                "How automatic blip was identified",
                _automaticBlipMethod,
                "For example: throttle telemetry spiked during a downshift without pedal input.");

            AddSubheading(form, "Cockpit controls");
            form.Children.Add(new TextBlock
            {
                Text = "A sequential gearbox may accept both paddle and stick bindings in AMS2. Use visible hardware and driver animation to identify the modeled primary mechanism.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.72,
                Margin = new Thickness(0, 0, 0, 10),
            });
            form.Children.Add(new TextBlock
            {
                Text = "Visible shift hardware",
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 0, 0, 6),
            });
            var actuatorRow = new WrapPanel { Margin = new Thickness(0, 0, 0, 12) };
            _visiblePaddles = CreateCheckBox("Paddles");
            _visibleSequentialStick = CreateCheckBox("Sequential stick");
            _visibleHPattern = CreateCheckBox("H-pattern shifter");
            _visibleAutomaticLever = CreateCheckBox("Automatic lever");
            actuatorRow.Children.Add(_visiblePaddles);
            actuatorRow.Children.Add(_visibleSequentialStick);
            actuatorRow.Children.Add(_visibleHPattern);
            actuatorRow.Children.Add(_visibleAutomaticLever);
            form.Children.Add(actuatorRow);
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

            AddSubheading(form, "Review notes");
            _evidenceNotes = CreateMultilineTextBox(72);
            AddLabeledControl(
                form,
                "Anything a reviewer should know",
                _evidenceNotes,
                "Include uncertainty, unusual hybrid starts, conflicting cockpit hardware, or tests that should be repeated.");

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
            root.Children.Add(actions);
            root.Children.Add(new TextBlock
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
            root.Children.Add(_status);
            Child = root;
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
                    return;
                }
                ApplyGuidedResults(_plugin.GetGuidedDriveResults());
                _guidedDriveApplied = true;
                _formExpander.IsExpanded = true;
                SetStatus("Guided drive complete. Suggested driving results were filled in; review the cockpit and wheel fields before saving.", Brushes.LightGreen, true);
            }
        }

        private void StartClicked(object sender, RoutedEventArgs eventArgs)
        {
            VerificationCaptureContext live = _plugin.CaptureVerificationContext();
            if (live == null)
            {
                _status.Text = "No live car telemetry is available. Load a car in the simulator, then try again.";
                return;
            }
            _capture = live;
            _guidedDriveApplied = true;
            ResetForm();
            _formExpander.IsExpanded = true;
            _capturedIdentity.Text = "Captured: " + live.TelemetryName + " - "
                + live.TelemetryClass + " | " + live.SimulatorDisplayName + " " + live.GameVersion + " | "
                + live.ClientVersion;
            _save.IsEnabled = true;
            SetStatus(live.SuggestedForwardGears.HasValue
                ? "Verification started. SimHub suggested " + live.SuggestedForwardGears.Value
                    + " forward gears; confirm it by selecting every gear."
                : "Verification started. Complete the form, then save a draft.", Brushes.LightGreen, false);
        }

        private void ResetForm()
        {
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
            if (string.Equals(_capture.Simulator, "ams2", StringComparison.Ordinal))
            {
                SelectChoice(_automaticClutch, "disabled");
                SelectChoice(_automaticShifting, "disabled");
                SelectChoice(_automaticThrottleBlip, "unavailable");
            }
            _assistSettingsConfirmed.IsChecked = false;
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
                SetStatus("✓ DRAFT SAVED SUCCESSFULLY\n" + path, Brushes.LightGreen, true);
                _save.IsEnabled = false;
                _formExpander.IsExpanded = false;
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
            _plugin.StartGuidedVerificationDrive(_capture);
            SetStatus("In-sim guided drive started. Follow the verification overlay prompts.", Brushes.LightGreen, true);
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
            SetStatus("Guided drive cancelled. Existing form entries were preserved.", Brushes.Goldenrod, false);
        }

        private void ApplyGuidedResults(GuidedDriveResults results)
        {
            if (results == null)
            {
                return;
            }
            SelectChoice(_moveOff, results.MoveOffWithoutPhysicalClutch);
            SelectChoice(_directGearSelection, results.DirectGearSelection);
            SelectChoice(_clutchlessUpshift, results.ClutchlessUpshift);
            SelectChoice(_automaticCut, results.AutomaticCut);
            SelectChoice(_clutchlessDownshift, results.ClutchlessDownshift);
            SelectChoice(_automaticBlip, results.AutomaticBlip);
            if (results.ForwardGears.HasValue)
            {
                _forwardGears.Text = results.ForwardGears.Value.ToString(CultureInfo.InvariantCulture);
            }
            _automaticCutMethod.Text = results.AutomaticCutMethod ?? string.Empty;
            _automaticBlipMethod.Text = results.AutomaticBlipMethod ?? string.Empty;
            if (!string.IsNullOrWhiteSpace(results.EvidenceNote))
            {
                _evidenceNotes.Text = string.IsNullOrWhiteSpace(_evidenceNotes.Text)
                    ? results.EvidenceNote
                    : _evidenceNotes.Text.Trim() + Environment.NewLine + results.EvidenceNote;
            }
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
            holder.Children.Add(new TextBlock
            {
                Text = label,
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 0, 0, 5),
            });
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
            }
            else if ((actuation == "h-pattern" || actuation == "direct-selection")
                && ChoiceValue(_directGearSelection) == "not-applicable")
            {
                SelectChoice(_directGearSelection, "not-tested");
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
