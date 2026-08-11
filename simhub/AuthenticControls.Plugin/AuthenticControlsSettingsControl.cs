using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using AuthenticControls.Core;

namespace AuthenticControls.Plugin
{
    public sealed class AuthenticControlsSettingsControl : UserControl
    {
        private readonly AuthenticControls _plugin;
        private readonly Slider _duration;
        private readonly TextBlock _durationValue;
        private readonly ComboBox _popupSize;
        private readonly ComboBox _previewCar;
        private readonly TextBlock _status;
        private readonly TextBlock _liveStatus;
        private readonly TextBlock _versionStatus;
        private readonly TextBlock _recordStatus;
        private readonly TextBlock _previewStatus;
        private readonly TextBlock _errorStatus;
        private readonly DispatcherTimer _statusTimer;

        public AuthenticControlsSettingsControl(AuthenticControls plugin)
        {
            _plugin = plugin;

            var panel = new StackPanel
            {
                Margin = new Thickness(24),
                MaxWidth = 760,
                HorizontalAlignment = HorizontalAlignment.Left,
            };

            var header = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                Margin = new Thickness(0, 0, 0, 8),
            };
            var headerIcon = new Image
            {
                Source = plugin.HeaderPictureIcon,
                Width = 34,
                Height = 34,
                Stretch = Stretch.Uniform,
            };
            RenderOptions.SetBitmapScalingMode(
                headerIcon,
                BitmapScalingMode.HighQuality);
            header.Children.Add(new Border
            {
                Width = 42,
                Height = 42,
                CornerRadius = new CornerRadius(8),
                Background = new SolidColorBrush(Color.FromRgb(39, 151, 230)),
                Child = headerIcon,
                Margin = new Thickness(0, 0, 14, 0),
            });
            var heading = new StackPanel();
            heading.Children.Add(new TextBlock
            {
                Text = "Authentic Controls",
                FontSize = 26,
                FontWeight = FontWeights.Bold,
            });
            heading.Children.Add(new TextBlock
            {
                Text = "Authentic hardware and shifting guidance for the current car",
                FontSize = 14,
                Opacity = 0.76,
            });
            header.Children.Add(heading);
            panel.Children.Add(header);
            panel.Children.Add(new TextBlock
            {
                Text = "Pin this page from SimHub's Add and remove features menu for quick access. Overlay positioning remains under Dash Studio > Overlays.",
                FontSize = 14,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 22),
            });

            AddSectionHeading(panel, "Live telemetry");
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
            _versionStatus = new TextBlock
            {
                Margin = new Thickness(0, 6, 0, 0),
                Opacity = 0.78,
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
            statusPanel.Children.Add(_versionStatus);
            statusPanel.Children.Add(_recordStatus);
            statusPanel.Children.Add(_errorStatus);
            panel.Children.Add(new Border
            {
                BorderBrush = new SolidColorBrush(Color.FromArgb(80, 120, 150, 180)),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(5),
                Child = statusPanel,
                Margin = new Thickness(0, 0, 0, 12),
            });

            var actionRow = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                Margin = new Thickness(0, 0, 0, 8),
            };
            actionRow.Children.Add(CreateButton("Show popup", 122, ShowPopupClicked));
            actionRow.Children.Add(CreateButton("Hide popup", 122, HidePopupClicked));
            actionRow.Children.Add(CreateButton("Refresh database", 150, RefreshDatabaseClicked));
            panel.Children.Add(actionRow);

            _status = new TextBlock
            {
                Margin = new Thickness(0, 2, 0, 18),
                TextWrapping = TextWrapping.Wrap,
            };
            panel.Children.Add(_status);

            AddSectionHeading(panel, "Browse and preview cars");
            panel.Children.Add(new TextBlock
            {
                Text = "Select any curated car to review its controls and driving technique before starting the simulator.",
                FontSize = 15,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 12),
            });
            _previewStatus = new TextBlock
            {
                FontSize = 16,
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 10),
            };
            panel.Children.Add(_previewStatus);
            _previewCar = new ComboBox
            {
                Width = 520,
                Height = 34,
                HorizontalAlignment = HorizontalAlignment.Left,
                IsEditable = true,
                IsTextSearchEnabled = true,
                StaysOpenOnEdit = true,
                DisplayMemberPath = "DisplayLabel",
                Margin = new Thickness(0, 0, 0, 10),
            };
            TextSearch.SetTextPath(_previewCar, "DisplayLabel");
            panel.Children.Add(_previewCar);
            var previewActions = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                Margin = new Thickness(0, 0, 0, 24),
            };
            previewActions.Children.Add(CreateButton(
                "Preview selected car", 170, PreviewCarClicked));
            previewActions.Children.Add(CreateButton(
                "Close preview", 145, ReturnToLiveCarClicked));
            panel.Children.Add(previewActions);

            AddSectionHeading(panel, "Popup behavior");
            panel.Children.Add(new TextBlock
            {
                Text = "Choose the pre-flight popup size and how long it stays visible after SimHub detects a new car.",
                FontSize = 15,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 18),
            });
            panel.Children.Add(new TextBlock
            {
                Text = "Automatic popup duration",
                FontSize = 16,
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 0, 0, 8),
            });

            var durationRow = new StackPanel
            {
                Orientation = Orientation.Horizontal,
            };
            _duration = new Slider
            {
                Minimum = AuthenticControls.MinimumPopupDurationSeconds,
                Maximum = AuthenticControls.MaximumPopupDurationSeconds,
                TickFrequency = 1.0,
                IsSnapToTickEnabled = true,
                Width = 420,
                Value = plugin.PopupDurationSeconds,
            };
            _duration.ValueChanged += DurationValueChanged;
            _durationValue = new TextBlock
            {
                Width = 100,
                FontSize = 16,
                VerticalAlignment = VerticalAlignment.Center,
                Margin = new Thickness(16, 0, 0, 0),
            };
            durationRow.Children.Add(_duration);
            durationRow.Children.Add(_durationValue);
            panel.Children.Add(durationRow);
            panel.Children.Add(new TextBlock
            {
                Text = "Popup size",
                FontSize = 16,
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 22, 0, 8),
            });
            _popupSize = new ComboBox
            {
                Width = 300,
                Height = 32,
                HorizontalAlignment = HorizontalAlignment.Left,
            };
            _popupSize.Items.Add(CreateSizeItem("Detailed — 840 × 360", "detailed"));
            _popupSize.Items.Add(CreateSizeItem("Compact — 520 × 300", "compact"));
            _popupSize.Items.Add(CreateSizeItem("Glance — 320 × 120", "glance"));
            SelectPopupSize(plugin.PopupSize);
            _popupSize.SelectionChanged += PopupSizeChanged;
            panel.Children.Add(_popupSize);
            panel.Children.Add(new TextBlock
            {
                Text = "Load and position the packaged Authentic Controls layout once in Dash Studio. The selected size is the only surface SimHub makes visible. Manual Show or Toggle recall remains visible until hidden.",
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 10, 0, 14),
            });

            panel.Children.Add(CreateButton("Save popup settings", 170, SaveClicked));

            AddSectionHeading(panel, "Unmatched car diagnostics", new Thickness(0, 30, 0, 8));
            panel.Children.Add(new TextBlock
            {
                Text = "When an exact match is not found, Authentic Controls records the game version, CarModel, CarId, class, dataset version, and timestamp once per unique identity. The JSON Lines file is preserved across plugin upgrades.",
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 8),
            });
            panel.Children.Add(new TextBlock
            {
                Text = plugin.UnmatchedLogPath,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 10),
                Opacity = 0.78,
            });
            panel.Children.Add(CreateButton("Open diagnostics folder", 190, OpenDiagnosticsClicked));

            Content = new ScrollViewer
            {
                Content = panel,
                VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
                HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled,
            };

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
        }

        private static void AddSectionHeading(
            Panel panel,
            string text,
            Thickness? margin = null)
        {
            panel.Children.Add(new TextBlock
            {
                Text = text,
                FontSize = 18,
                FontWeight = FontWeights.SemiBold,
                Margin = margin ?? new Thickness(0, 0, 0, 8),
            });
        }

        private static Button CreateButton(
            string label,
            double width,
            RoutedEventHandler handler)
        {
            var button = new Button
            {
                Content = label,
                Width = width,
                Height = 32,
                HorizontalAlignment = HorizontalAlignment.Left,
                Margin = new Thickness(0, 0, 10, 0),
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
                    + (string.IsNullOrWhiteSpace(carClass) ? string.Empty : " — " + carClass);
            }
            else if (state == "unmatched")
            {
                _liveStatus.Text = "Unmatched car: "
                    + (string.IsNullOrWhiteSpace(car) ? "Unknown" : car);
            }
            else if (state == "game-not-running" || state == "no-car" || state == "no-data")
            {
                _liveStatus.Text = "Waiting for car telemetry";
            }
            else
            {
                _liveStatus.Text = "Status: " + state;
            }

            _versionStatus.Text = "Plugin " + _plugin.PluginVersion
                + "  •  Dataset " + EmptyAsUnknown(_plugin.CurrentDatasetVersion)
                + "  •  " + _plugin.DatabaseRecordCount + " records";
            _recordStatus.Text = string.IsNullOrWhiteSpace(_plugin.LiveRecordId)
                ? string.Empty
                : "Record: " + _plugin.LiveRecordId;
            _errorStatus.Text = string.IsNullOrWhiteSpace(_plugin.CurrentRuntimeError)
                ? string.Empty
                : "Error: " + _plugin.CurrentRuntimeError;
            UpdatePreviewStatus();
        }

        private void UpdatePreviewStatus()
        {
            if (_previewStatus == null)
            {
                return;
            }
            _previewStatus.Text = _plugin.IsPreviewActive
                ? "PREVIEW — NOT LIVE: " + _plugin.CurrentCarName
                    + (string.IsNullOrWhiteSpace(_plugin.CurrentCarClass)
                        ? string.Empty
                        : " — " + _plugin.CurrentCarClass)
                    + ". Click Close preview when finished."
                : "No preview active.";
        }

        private static string EmptyAsUnknown(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? "unknown" : value;
        }

        private void ShowPopupClicked(object sender, RoutedEventArgs eventArgs)
        {
            _plugin.ShowPopup();
            _status.Text = "Popup shown. It will remain visible until hidden.";
        }

        private void HidePopupClicked(object sender, RoutedEventArgs eventArgs)
        {
            _plugin.HidePopup();
            _status.Text = "Popup hidden.";
        }

        private void RefreshDatabaseClicked(object sender, RoutedEventArgs eventArgs)
        {
            _plugin.RefreshDatabase();
            ReloadPreviewCars();
            UpdateLiveStatus();
            _status.Text = string.IsNullOrWhiteSpace(_plugin.CurrentRuntimeError)
                ? "Database refreshed successfully."
                : "Database refresh failed: " + _plugin.CurrentRuntimeError;
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
                _status.Text = "Choose a car from the list first.";
                return;
            }
            if (!_plugin.PreviewCar(selected))
            {
                UpdateLiveStatus();
                _status.Text = "Could not open the preview overlay. "
                    + EmptyAsUnknown(_plugin.CurrentRuntimeError);
                return;
            }
            UpdateLiveStatus();
            _status.Text = string.Empty;
        }

        private void ReturnToLiveCarClicked(object sender, RoutedEventArgs eventArgs)
        {
            _plugin.ReturnToLiveCar();
            UpdateLiveStatus();
            _status.Text = "Preview closed. Live telemetry restored.";
        }

        private void DurationValueChanged(
            object sender,
            RoutedPropertyChangedEventArgs<double> eventArgs)
        {
            UpdateDurationLabel();
            _status.Text = string.Empty;
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
                if (sizeItem != null && string.Equals(
                    sizeItem.Tag as string,
                    value,
                    StringComparison.OrdinalIgnoreCase))
                {
                    _popupSize.SelectedItem = sizeItem;
                    return;
                }
            }
            _popupSize.SelectedIndex = 1;
        }

        private void PopupSizeChanged(object sender, SelectionChangedEventArgs eventArgs)
        {
            _status.Text = string.Empty;
        }

        private void UpdateDurationLabel()
        {
            if (_durationValue != null)
            {
                _durationValue.Text = Math.Round(_duration.Value) + " seconds";
            }
        }

        private void SaveClicked(object sender, RoutedEventArgs eventArgs)
        {
            double seconds = Math.Round(_duration.Value);
            ComboBoxItem selected = _popupSize.SelectedItem as ComboBoxItem;
            string popupSize = selected == null
                ? AuthenticControls.DefaultPopupSize
                : selected.Tag as string;
            _plugin.SetPopupSettings(seconds, popupSize);
            _status.Text = "Saved. New car changes will use the " + popupSize
                + " popup for " + seconds + " seconds.";
        }

        private void OpenDiagnosticsClicked(object sender, RoutedEventArgs eventArgs)
        {
            try
            {
                string folder = _plugin.OpenDiagnosticsFolder();
                _status.Text = "Opened diagnostics folder: " + folder;
            }
            catch (Exception exception)
            {
                _status.Text = "Could not open diagnostics folder: " + exception.Message;
            }
        }
    }
}
