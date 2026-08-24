using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using AsDriven.Core;
using SimHub.Plugins.Styles;

namespace AsDriven.Plugin
{
    /// <summary>
    /// SimHub settings entry point. The control deliberately uses standard WPF
    /// controls so it follows the host application's active theme rather than
    /// recreating a separate application inside SimHub.
    /// </summary>
    public sealed class AsDrivenSettingsControl : UserControl
    {
        private readonly AsDriven _plugin;
        private Slider _duration;
        private TextBlock _durationValue;
        private ComboBox _popupSize;
        private ComboBox _previewCar;
        private TextBlock _liveStatus;
        private TextBlock _recordStatus;
        private TextBlock _previewStatus;
        private TextBlock _errorStatus;
        private TextBlock _overlayFeedback;
        private TextBlock _browserFeedback;
        private TextBlock _contributionFeedback;
        private TextBlock _advancedFeedback;
        private TextBlock _installedDatasetStatus;
        private TextBlock _supportedSimulators;
        private VerificationControl _verification;
        private Button _contributeLiveButton;
        private Button _showPopupButton;
        private Button _closePreviewButton;
        private Button _savePopupSettingsButton;
        private readonly SHTabControl _tabs;
        private readonly ScrollViewer _scrollViewer;
        private readonly DispatcherTimer _statusTimer;
        private bool _popupSettingsDirty;

        public AsDrivenSettingsControl(AsDriven plugin)
        {
            _plugin = plugin;

            var panel = new StackPanel
            {
                Margin = new Thickness(24),
                MaxWidth = 1180,
                HorizontalAlignment = HorizontalAlignment.Stretch,
            };

            // SimHub supplies the page title and navigation icon. Keep the
            // client version near that header, while dataset details live in
            // the Advanced workspace.
            var introduction = new Grid { Margin = new Thickness(0, 0, 0, 16) };
            introduction.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            introduction.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            var purpose = new TextBlock
            {
                Text = "Choose authentic controls for the current car, preview the curated database, or contribute a local verification draft.",
                FontSize = 14,
                Opacity = 0.82,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 18, 0),
            };
            introduction.Children.Add(purpose);
            var pluginVersion = new TextBlock
            {
                Text = "Plugin " + _plugin.PluginVersion,
                Opacity = 0.72,
                VerticalAlignment = VerticalAlignment.Top,
            };
            Grid.SetColumn(pluginVersion, 1);
            introduction.Children.Add(pluginVersion);
            panel.Children.Add(introduction);

            _tabs = new SHTabControl
            {
                HorizontalAlignment = HorizontalAlignment.Stretch,
                TabsHorizontalAlignement = HorizontalAlignment.Left,
            };
            _tabs.Items.Add(CreateTab("Overlay", CreateOverlayTab()));
            _tabs.Items.Add(CreateTab("Car browser", CreateBrowserTab()));
            _tabs.Items.Add(CreateTab("Contribute data", CreateContributionTab()));
            _tabs.Items.Add(CreateTab("Advanced", CreateAdvancedTab()));
            panel.Children.Add(_tabs);

            _scrollViewer = new ScrollViewer
            {
                Content = panel,
                VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
                HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled,
            };
            Content = _scrollViewer;

            _statusTimer = new DispatcherTimer
            {
                Interval = TimeSpan.FromSeconds(1),
            };
            _statusTimer.Tick += StatusTimerTick;
            Loaded += ControlLoaded;
            Unloaded += ControlUnloaded;
            UpdateDurationLabel();
            ReloadPreviewCars();
            UpdateLiveStatus();
            UpdatePopupSettingsState();
        }

        private UIElement CreateOverlayTab()
        {
            var panel = CreateTabPanel();
            AddSectionHeading(panel, "Current car");
            var statusPanel = new StackPanel
            {
                Margin = new Thickness(14),
            };
            _liveStatus = new TextBlock
            {
                FontSize = 16,
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
            };
            _recordStatus = new TextBlock
            {
                Margin = new Thickness(0, 4, 0, 0),
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.78,
            };
            _errorStatus = new TextBlock
            {
                Margin = new Thickness(0, 6, 0, 0),
                Foreground = Brushes.IndianRed,
                TextWrapping = TextWrapping.Wrap,
            };
            statusPanel.Children.Add(_liveStatus);
            statusPanel.Children.Add(_recordStatus);
            statusPanel.Children.Add(_errorStatus);
            panel.Children.Add(CreateGroupBorder(statusPanel, new Thickness(0, 0, 0, 12)));

            var actionRow = CreateActionRow(new Thickness(0, 0, 0, 5));
            _showPopupButton = CreateSecondaryButton("Show popup", 122, ShowPopupClicked);
            _showPopupButton.ToolTip = "Available when a live car or catalog preview is active.";
            ToolTipService.SetShowOnDisabled(_showPopupButton, true);
            actionRow.Children.Add(_showPopupButton);
            actionRow.Children.Add(CreateSecondaryButton("Hide popup", 122, HidePopupClicked));
            _contributeLiveButton = CreatePrimaryButton("Contribute this car", 165, ContributeLiveCarClicked);
            _contributeLiveButton.Visibility = Visibility.Collapsed;
            _contributeLiveButton.BorderBrush = new SolidColorBrush(Color.FromRgb(50, 190, 235));
            _contributeLiveButton.BorderThickness = new Thickness(2);
            actionRow.Children.Add(_contributeLiveButton);
            panel.Children.Add(actionRow);
            _overlayFeedback = CreateFeedbackText(new Thickness(0, 0, 0, 22));
            panel.Children.Add(_overlayFeedback);

            AddSectionHeading(panel, "Supported simulators");
            panel.Children.Add(new TextBlock
            {
                Text = "As Driven only shows guidance for the simulators the installed dataset covers. In any other game the plugin stays quiet rather than guessing.",
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 10),
                MaxWidth = 720,
            });
            _supportedSimulators = new TextBlock
            {
                FontSize = 15,
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 22),
                MaxWidth = 720,
            };
            panel.Children.Add(_supportedSimulators);

            AddSectionHeading(panel, "Popup behavior");
            panel.Children.Add(new TextBlock
            {
                Text = "Choose the pre-flight popup size and how long it remains visible when SimHub detects a new car.",
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 16),
            });
            panel.Children.Add(CreateFieldLabel("Automatic popup duration", new Thickness(0, 0, 0, 8)));
            var durationRow = new Grid
            {
                MaxWidth = 540,
                HorizontalAlignment = HorizontalAlignment.Left,
                Margin = new Thickness(0, 0, 0, 18),
            };
            durationRow.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            durationRow.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            _duration = new Slider
            {
                Minimum = AsDriven.MinimumPopupDurationSeconds,
                Maximum = AsDriven.MaximumPopupDurationSeconds,
                TickFrequency = 1.0,
                IsSnapToTickEnabled = true,
                Value = _plugin.PopupDurationSeconds,
                MinWidth = 230,
            };
            _duration.ValueChanged += DurationValueChanged;
            _durationValue = new TextBlock
            {
                Width = 100,
                VerticalAlignment = VerticalAlignment.Center,
                Margin = new Thickness(16, 0, 0, 0),
            };
            durationRow.Children.Add(_duration);
            Grid.SetColumn(_durationValue, 1);
            durationRow.Children.Add(_durationValue);
            panel.Children.Add(durationRow);

            panel.Children.Add(CreateFieldLabel("Popup size", new Thickness(0, 0, 0, 8)));
            _popupSize = new ComboBox
            {
                Height = 32,
                MinWidth = 240,
                MaxWidth = 360,
                HorizontalAlignment = HorizontalAlignment.Left,
            };
            _popupSize.Items.Add(CreateSizeItem("Detailed - 840 x 360", "detailed"));
            _popupSize.Items.Add(CreateSizeItem("Compact - 520 x 300", "compact"));
            _popupSize.Items.Add(CreateSizeItem("Glance - 320 x 120", "glance"));
            SelectPopupSize(_plugin.PopupSize);
            _popupSize.SelectionChanged += PopupSizeChanged;
            panel.Children.Add(_popupSize);
            panel.Children.Add(new TextBlock
            {
                Text = "Load and position the matching packaged layout once in Dash Studio. The selected size is the only overlay surface made visible.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.78,
                Margin = new Thickness(0, 10, 0, 14),
                MaxWidth = 720,
            });
            _savePopupSettingsButton = CreatePrimaryButton("Save changes", 150, SaveClicked);
            panel.Children.Add(_savePopupSettingsButton);
            return panel;
        }

        private UIElement CreateBrowserTab()
        {
            var panel = CreateTabPanel();
            AddSectionHeading(panel, "Browse curated cars");
            panel.Children.Add(new TextBlock
            {
                Text = "Review a car's controls and driving technique before starting the simulator. Preview data is clearly marked and does not replace live telemetry.",
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 12),
                MaxWidth = 720,
            });
            _previewStatus = new TextBlock
            {
                FontSize = 15,
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 10),
            };
            panel.Children.Add(_previewStatus);
            _previewCar = new ComboBox
            {
                Height = 34,
                MinWidth = 300,
                MaxWidth = 640,
                HorizontalAlignment = HorizontalAlignment.Left,
                IsEditable = true,
                IsTextSearchEnabled = true,
                StaysOpenOnEdit = true,
                DisplayMemberPath = "DisplayLabel",
                Margin = new Thickness(0, 0, 0, 10),
            };
            TextSearch.SetTextPath(_previewCar, "DisplayLabel");
            panel.Children.Add(_previewCar);
            var actions = CreateActionRow(new Thickness(0, 0, 0, 5));
            actions.Children.Add(CreatePrimaryButton("Preview selected car", 170, PreviewCarClicked));
            _closePreviewButton = CreateSecondaryButton("Close preview", 145, ReturnToLiveCarClicked);
            actions.Children.Add(_closePreviewButton);
            panel.Children.Add(actions);
            _browserFeedback = CreateFeedbackText(new Thickness(0, 0, 0, 8));
            panel.Children.Add(_browserFeedback);
            return panel;
        }

        private UIElement CreateContributionTab()
        {
            var panel = CreateTabPanel();
            AddSectionHeading(panel, "Contribute a simulator observation");
            panel.Children.Add(new TextBlock
            {
                Text = "Test a loaded car and create a versioned simulator observation for maintainer review. A drive does not establish the real car's identity, nothing is uploaded automatically, and no draft enters the curated dataset without research and approval.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.82,
                Margin = new Thickness(0, 0, 0, 12),
                MaxWidth = 800,
            });
            var draftSharing = new StackPanel { Margin = new Thickness(14) };
            draftSharing.Children.Add(new TextBlock
            {
                Text = "Saved drafts and review",
                FontSize = 15,
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 0, 0, 5),
            });
            draftSharing.Children.Add(new TextBlock
            {
                Text = "Drafts remain on this PC until you explicitly share them. After saving, you can select the exact JSON, create a redacted research copy, or open the public GitHub observation form. You attach the file yourself; the plugin never uploads it. Every observation still requires validation, identity research, and reviewer approval before release.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.82,
                Margin = new Thickness(0, 0, 0, 10),
                MaxWidth = 900,
            });
            draftSharing.Children.Add(CreateSecondaryButton(
                "Open saved drafts folder", 190, OpenDraftsClicked));
            _contributionFeedback = CreateFeedbackText(new Thickness(0, 7, 0, 0));
            draftSharing.Children.Add(_contributionFeedback);
            _verification = new VerificationControl(_plugin);
            panel.Children.Add(_verification);
            panel.Children.Add(CreateGroupBorder(draftSharing, new Thickness(0, 16, 0, 0)));
            return panel;
        }

        private UIElement CreateAdvancedTab()
        {
            var panel = CreateTabPanel();
            AddSectionHeading(panel, "Installed dataset");
            _installedDatasetStatus = new TextBlock
            {
                FontSize = 16,
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 0, 0, 7),
                TextWrapping = TextWrapping.Wrap,
            };
            panel.Children.Add(_installedDatasetStatus);
            panel.Children.Add(new TextBlock
            {
                Text = "Online dataset updates are not implemented in this development build. The planned public-release flow will check the database's GitHub releases, ask before downloading, validate the package, and preserve a rollback copy. Dataset updates will remain separate from plugin updates.",
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 18),
                MaxWidth = 860,
            });

            var reload = new SHExpander
            {
                Header = "Troubleshooting and manually replaced files",
                IsExpanded = false,
                Margin = new Thickness(0, 0, 0, 24),
            };
            var reloadContent = new StackPanel { Margin = new Thickness(0, 10, 0, 0) };
            reloadContent.Children.Add(new TextBlock
            {
                Text = "Reload files from disk only after manually replacing the installed dataset, or if SimHub did not pick up an on-disk change. This action does not check GitHub, download an update, or modify a curated record.",
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 10),
                MaxWidth = 820,
            });
            reloadContent.Children.Add(CreateSecondaryButton("Reload files from disk", 190, RefreshDatabaseClicked));
            _advancedFeedback = CreateFeedbackText(new Thickness(0, 7, 0, 0));
            reloadContent.Children.Add(_advancedFeedback);
            reload.Content = reloadContent;
            panel.Children.Add(reload);

            AddSectionHeading(panel, "Unmatched-car diagnostics");
            var diagnostics = new SHExpander
            {
                Header = "View diagnostic storage details",
                IsExpanded = false,
            };
            var diagnosticsContent = new StackPanel { Margin = new Thickness(0, 10, 0, 0) };
            diagnosticsContent.Children.Add(new TextBlock
            {
                Text = "When no exact match is found, the plugin records the game version, CarModel, CarId, class, dataset version, and timestamp once per unique identity. The JSON Lines file is preserved across plugin upgrades.",
                TextWrapping = TextWrapping.Wrap,
                MaxWidth = 760,
            });
            diagnosticsContent.Children.Add(new TextBlock
            {
                Text = _plugin.UnmatchedLogPath,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 8, 0, 10),
                Opacity = 0.78,
                MaxWidth = 760,
            });
            diagnosticsContent.Children.Add(CreateSecondaryButton("Open diagnostics folder", 190, OpenDiagnosticsClicked));
            diagnostics.Content = diagnosticsContent;
            panel.Children.Add(diagnostics);
            return panel;
        }

        private static SHTabItem CreateTab(string header, UIElement content)
        {
            return new SHTabItem
            {
                Header = header,
                Content = content,
            };
        }

        private static StackPanel CreateTabPanel()
        {
            return new StackPanel
            {
                Margin = new Thickness(18),
                MaxWidth = 1120,
                HorizontalAlignment = HorizontalAlignment.Stretch,
            };
        }

        private static Border CreateGroupBorder(UIElement child, Thickness margin)
        {
            return new Border
            {
                BorderBrush = new SolidColorBrush(Color.FromArgb(80, 120, 150, 180)),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(5),
                Child = child,
                Margin = margin,
            };
        }

        private static WrapPanel CreateActionRow(Thickness margin)
        {
            return new WrapPanel
            {
                Margin = margin,
            };
        }

        private static TextBlock CreateFeedbackText(Thickness margin)
        {
            return new TextBlock
            {
                TextWrapping = TextWrapping.Wrap,
                Margin = margin,
                Opacity = 0.88,
                MaxWidth = 760,
            };
        }

        private static TextBlock CreateFieldLabel(string text, Thickness margin)
        {
            return new TextBlock
            {
                Text = text,
                FontSize = 16,
                FontWeight = FontWeights.SemiBold,
                Margin = margin,
            };
        }

        private static void AddSectionHeading(Panel panel, string text)
        {
            panel.Children.Add(new SHSectionTitle
            {
                Text = text,
                FontSize = 18,
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 0, 0, 8),
            });
        }

        private static Button CreatePrimaryButton(string label, double width, RoutedEventHandler handler)
        {
            var button = new SHButtonPrimary
            {
                Content = label,
                Width = width,
                Height = 32,
                HorizontalAlignment = HorizontalAlignment.Left,
                Margin = new Thickness(0, 0, 10, 8),
            };
            button.Click += handler;
            return button;
        }

        private static Button CreateSecondaryButton(string label, double width, RoutedEventHandler handler)
        {
            var button = new SHButtonSecondary
            {
                Content = label,
                Width = width,
                Height = 32,
                HorizontalAlignment = HorizontalAlignment.Left,
                Margin = new Thickness(0, 0, 10, 8),
                Foreground = new SolidColorBrush(Color.FromRgb(32, 32, 32)),
            };
            button.Click += handler;
            return button;
        }

        private void ControlLoaded(object sender, RoutedEventArgs eventArgs)
        {
            UpdateLiveStatus();
            _statusTimer.Start();
        }

        private void ControlUnloaded(object sender, RoutedEventArgs eventArgs)
        {
            _statusTimer.Stop();
        }

        private void StatusTimerTick(object sender, EventArgs eventArgs)
        {
            UpdateLiveStatus();
        }

        private void UpdateLiveStatus()
        {
            string state = _plugin.LiveMatchStatus;
            string car = _plugin.LiveCarName;
            string carClass = _plugin.LiveCarClass;
            if (state == "matched")
            {
                _liveStatus.Text = "Matched: " + car
                    + (string.IsNullOrWhiteSpace(carClass) ? string.Empty : " - " + carClass);
            }
            else if (state == "unmatched")
            {
                _liveStatus.Text = "Unmatched car: "
                    + (string.IsNullOrWhiteSpace(car) ? "Unknown" : car);
            }
            else if (state == "unsupported-game")
            {
                _liveStatus.Text = "Not a supported simulator - the installed dataset has no records for this game";
            }
            else if (state == "game-not-running" || state == "no-car" || state == "no-data")
            {
                _liveStatus.Text = "Waiting for car telemetry";
            }
            else
            {
                _liveStatus.Text = "Status: " + state;
            }

            _contributeLiveButton.Visibility = state == "unmatched"
                ? Visibility.Visible
                : Visibility.Collapsed;
            _showPopupButton.IsEnabled = _plugin.CanShowPopup;
            if (_installedDatasetStatus != null)
            {
                _installedDatasetStatus.Text = "Dataset "
                    + EmptyAsUnknown(_plugin.CurrentDatasetVersion)
                    + "  /  " + _plugin.DatabaseRecordCount + " car records";
            }
            if (_supportedSimulators != null)
            {
                _supportedSimulators.Text = DescribeSupportedSimulators();
            }
            _recordStatus.Text = string.IsNullOrWhiteSpace(_plugin.LiveRecordId)
                ? string.Empty
                : "Record: " + _plugin.LiveRecordId;
            _errorStatus.Text = string.IsNullOrWhiteSpace(_plugin.CurrentRuntimeError)
                ? string.Empty
                : "Error: " + _plugin.CurrentRuntimeError;
            UpdatePreviewStatus();
            _verification.UpdateLiveAvailability();
        }

        private void ContributeLiveCarClicked(object sender, RoutedEventArgs eventArgs)
        {
            VerificationCaptureContext capture = _plugin.CaptureVerificationContext();
            if (capture == null)
            {
                SetOverlayFeedback("No live car is available to contribute.", Brushes.IndianRed);
                return;
            }
            _tabs.SelectedIndex = 2;
            _verification.BeginFromCapture(capture);
            _verification.Dispatcher.BeginInvoke(
                DispatcherPriority.Background,
                new Action(delegate { _verification.BringIntoView(); }));
        }

        private void UpdatePreviewStatus()
        {
            if (_previewStatus == null)
            {
                return;
            }
            bool previewActive = _plugin.IsPreviewActive;
            _previewStatus.Text = previewActive
                ? "Previewing (not live): " + _plugin.CurrentCarName
                    + (string.IsNullOrWhiteSpace(_plugin.CurrentCarClass)
                        ? string.Empty
                        : " - " + _plugin.CurrentCarClass)
                : "Live telemetry remains active.";
            _closePreviewButton.IsEnabled = previewActive;
        }

        private static string EmptyAsUnknown(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? "unknown" : value;
        }

        /// <summary>
        /// Lists the simulators the installed dataset covers, one per line, with
        /// the number of curated cars behind each. The list comes from the
        /// loaded records, so it stays honest when a dataset is swapped.
        /// </summary>
        private string DescribeSupportedSimulators()
        {
            SimulatorCoverage[] simulators = _plugin.SupportedSimulators;
            if (simulators.Length == 0)
            {
                return "No dataset is loaded, so no simulator is covered right now.";
            }

            var lines = new List<string>();
            foreach (SimulatorCoverage simulator in simulators)
            {
                lines.Add(simulator.DisplayLabel);
            }
            return string.Join(Environment.NewLine, lines.ToArray());
        }

        private void ShowPopupClicked(object sender, RoutedEventArgs eventArgs)
        {
            if (!_plugin.ShowPopup())
            {
                SetOverlayFeedback(
                    "No car is available. Start the simulator or preview a car from Car browser first.",
                    Brushes.Goldenrod);
                return;
            }
            SetOverlayFeedback("Popup shown. It remains visible until you hide it.", Brushes.LightGreen);
        }

        private void HidePopupClicked(object sender, RoutedEventArgs eventArgs)
        {
            _plugin.HidePopup();
            SetOverlayFeedback("Popup hidden.", Brushes.LightGreen);
        }

        private void RefreshDatabaseClicked(object sender, RoutedEventArgs eventArgs)
        {
            _plugin.RefreshDatabase();
            ReloadPreviewCars();
            UpdateLiveStatus();
            SetAdvancedFeedback(
                string.IsNullOrWhiteSpace(_plugin.CurrentRuntimeError)
                    ? "Dataset files reloaded successfully."
                    : "Dataset reload failed: " + _plugin.CurrentRuntimeError,
                string.IsNullOrWhiteSpace(_plugin.CurrentRuntimeError)
                    ? Brushes.LightGreen
                    : Brushes.IndianRed);
        }

        private void ReloadPreviewCars()
        {
            if (_previewCar == null)
            {
                return;
            }
            string selectedRecord = (_previewCar.SelectedItem as CarCatalogEntry) == null
                ? _plugin.CurrentRecordId
                : ((CarCatalogEntry)_previewCar.SelectedItem).RecordId;
            _previewCar.Items.Clear();
            CarCatalogEntry selected = null;
            foreach (CarCatalogEntry car in _plugin.PreviewCars)
            {
                _previewCar.Items.Add(car);
                if (car.RecordId == selectedRecord)
                {
                    selected = car;
                }
            }
            _previewCar.SelectedItem = selected;
            if (_previewCar.SelectedItem == null && _previewCar.Items.Count > 0)
            {
                _previewCar.SelectedIndex = 0;
            }
        }

        private void PreviewCarClicked(object sender, RoutedEventArgs eventArgs)
        {
            CarCatalogEntry selected = _previewCar.SelectedItem as CarCatalogEntry;
            if (selected == null)
            {
                SetBrowserFeedback("Choose a car from the list first.", Brushes.IndianRed);
                return;
            }
            if (!_plugin.PreviewCar(selected))
            {
                UpdateLiveStatus();
                SetBrowserFeedback(
                    "Could not open the preview overlay. " + EmptyAsUnknown(_plugin.CurrentRuntimeError),
                    Brushes.IndianRed);
                return;
            }
            UpdateLiveStatus();
            SetBrowserFeedback("Preview is showing in the selected overlay layout. It is not live telemetry.", Brushes.LightGreen);
        }

        private void ReturnToLiveCarClicked(object sender, RoutedEventArgs eventArgs)
        {
            _plugin.ReturnToLiveCar();
            UpdateLiveStatus();
            SetBrowserFeedback("Preview closed. Live telemetry restored.", Brushes.LightGreen);
        }

        private void DurationValueChanged(object sender, RoutedPropertyChangedEventArgs<double> eventArgs)
        {
            UpdateDurationLabel();
            MarkPopupSettingsDirty();
        }

        private static ComboBoxItem CreateSizeItem(string label, string value)
        {
            return new ComboBoxItem
            {
                Content = label,
                Tag = value,
            };
        }

        private void SelectPopupSize(string value)
        {
            foreach (object item in _popupSize.Items)
            {
                ComboBoxItem sizeItem = item as ComboBoxItem;
                if (sizeItem != null && string.Equals(sizeItem.Tag as string, value, StringComparison.OrdinalIgnoreCase))
                {
                    _popupSize.SelectedItem = sizeItem;
                    return;
                }
            }
            _popupSize.SelectedIndex = 1;
        }

        private void PopupSizeChanged(object sender, SelectionChangedEventArgs eventArgs)
        {
            MarkPopupSettingsDirty();
        }

        private void UpdateDurationLabel()
        {
            if (_durationValue != null)
            {
                _durationValue.Text = Math.Round(_duration.Value) + " seconds";
            }
        }

        private void MarkPopupSettingsDirty()
        {
            _popupSettingsDirty = true;
            if (_overlayFeedback != null)
            {
                SetOverlayFeedback("Unsaved popup changes.", Brushes.Goldenrod);
            }
            UpdatePopupSettingsState();
        }

        private void UpdatePopupSettingsState()
        {
            if (_savePopupSettingsButton == null)
            {
                return;
            }
            _savePopupSettingsButton.IsEnabled = _popupSettingsDirty;
            _savePopupSettingsButton.Content = _popupSettingsDirty ? "Save changes" : "Changes saved";
        }

        private void SaveClicked(object sender, RoutedEventArgs eventArgs)
        {
            double seconds = Math.Round(_duration.Value);
            ComboBoxItem selected = _popupSize.SelectedItem as ComboBoxItem;
            string popupSize = selected == null
                ? AsDriven.DefaultPopupSize
                : selected.Tag as string;
            _plugin.SetPopupSettings(seconds, popupSize);
            _popupSettingsDirty = false;
            UpdatePopupSettingsState();
            SetOverlayFeedback(
                "Saved. New car changes use the " + popupSize + " popup for " + seconds + " seconds.",
                Brushes.LightGreen);
        }

        private void OpenDiagnosticsClicked(object sender, RoutedEventArgs eventArgs)
        {
            try
            {
                string folder = _plugin.OpenDiagnosticsFolder();
                SetAdvancedFeedback("Opened diagnostics folder: " + folder, Brushes.LightGreen);
            }
            catch (Exception exception)
            {
                SetAdvancedFeedback("Could not open diagnostics folder: " + exception.Message, Brushes.IndianRed);
            }
        }

        private void OpenDraftsClicked(object sender, RoutedEventArgs eventArgs)
        {
            try
            {
                string folder = _plugin.OpenVerificationFolder();
                SetFeedback(
                    _contributionFeedback,
                    "Opened saved drafts folder: " + folder,
                    Brushes.LightGreen);
            }
            catch (Exception exception)
            {
                SetFeedback(
                    _contributionFeedback,
                    "Could not open saved drafts folder: " + exception.Message,
                    Brushes.IndianRed);
            }
        }

        private void SetOverlayFeedback(string message, Brush foreground)
        {
            SetFeedback(_overlayFeedback, message, foreground);
        }

        private void SetBrowserFeedback(string message, Brush foreground)
        {
            SetFeedback(_browserFeedback, message, foreground);
        }

        private void SetAdvancedFeedback(string message, Brush foreground)
        {
            SetFeedback(_advancedFeedback, message, foreground);
        }

        private static void SetFeedback(TextBlock control, string message, Brush foreground)
        {
            if (control == null)
            {
                return;
            }
            control.Text = message ?? string.Empty;
            control.Foreground = foreground;
        }
    }
}
