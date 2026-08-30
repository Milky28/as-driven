using System;
using System.Collections.Generic;
using System.Globalization;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;
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
        private sealed class ThemePreviewPalette
        {
            public Brush Card { get; private set; }
            public Brush Panel { get; private set; }
            public Brush Note { get; private set; }
            public Brush Title { get; private set; }
            public Brush Text { get; private set; }
            public Brush BandText { get; private set; }
            public Brush BandMuted { get; private set; }
            public Brush Muted { get; private set; }
            public Brush Rule { get; private set; }
            public Brush Accent { get; private set; }
            public Brush Driver { get; private set; }
            public Brush Car { get; private set; }
            public Brush FitRail { get; private set; }
            public Brush DriverRail { get; private set; }
            public Brush CarRail { get; private set; }
            public Brush DriverCell { get; private set; }
            public Brush CarCell { get; private set; }
            public Brush PreviewFill { get; private set; }
            public Brush PreviewText { get; private set; }
            public Brush FitRailText { get; private set; }
            public Brush UseRailText { get; private set; }

            public ThemePreviewPalette(
                string card, string panel, string note, string title,
                string text, string bandText, string muted, string rule,
                string accent, string driver, string car, string fitRail,
                string driverRail, string carRail, string driverCell,
                string carCell, string previewFill, string previewText,
                string fitRailText, string useRailText, string bandMuted)
            {
                Card = PreviewBrush(card);
                Panel = PreviewBrush(panel);
                Note = PreviewBrush(note);
                Title = PreviewBrush(title);
                Text = PreviewBrush(text);
                BandText = PreviewBrush(bandText);
                Muted = PreviewBrush(muted);
                Rule = PreviewBrush(rule);
                Accent = PreviewBrush(accent);
                Driver = PreviewBrush(driver);
                Car = PreviewBrush(car);
                FitRail = PreviewBrush(fitRail);
                DriverRail = PreviewBrush(driverRail);
                CarRail = PreviewBrush(carRail);
                DriverCell = PreviewBrush(driverCell);
                CarCell = PreviewBrush(carCell);
                PreviewFill = PreviewBrush(previewFill);
                PreviewText = PreviewBrush(previewText);
                FitRailText = PreviewBrush(fitRailText);
                UseRailText = PreviewBrush(useRailText);
                BandMuted = PreviewBrush(bandMuted);
            }
        }

        private sealed class PopupPreviewVariant
        {
            public bool Compact { get; set; }
            public Viewbox View { get; set; }
            public Border Card { get; set; }
            public FrameworkElement WheelGlyph { get; set; }
            public FrameworkElement ShiftGlyph { get; set; }
            public Dictionary<string, TextBlock> Text { get; private set; }
            public Dictionary<string, Border> Box { get; private set; }
            public List<Shape> Glyphs { get; private set; }

            public PopupPreviewVariant()
            {
                Text = new Dictionary<string, TextBlock>(StringComparer.Ordinal);
                Box = new Dictionary<string, Border>(StringComparer.Ordinal);
                Glyphs = new List<Shape>();
            }
        }

        private readonly AsDriven _plugin;
        private Slider _duration;
        private TextBlock _durationValue;
        private ComboBox _popupSize;
        private WrapPanel _popupTheme;
        private ListBox _previewCar;
        private TextBox _catalogSearch;
        private ComboBox _catalogSimulator;
        private ComboBox _catalogDecade;
        private ComboBox _catalogWheel;
        private ComboBox _catalogShifter;
        private TextBlock _catalogCount;
        private TextBlock _catalogDetailName;
        private TextBlock _catalogDetailClass;
        private TextBlock _catalogWheelValue;
        private TextBlock _catalogWheelDetail;
        private TextBlock _catalogWheelHeading;
        private TextBlock _catalogShifterValue;
        private TextBlock _catalogShifterDetail;
        private TextBlock _catalogShifterHeading;
        private TextBlock _catalogLaunch;
        private TextBlock _catalogLaunchDetail;
        private TextBlock _catalogLaunchHeading;
        private TextBlock _catalogUpshift;
        private TextBlock _catalogUpshiftDetail;
        private TextBlock _catalogUpshiftHeading;
        private TextBlock _catalogDownshift;
        private TextBlock _catalogDownshiftDetail;
        private TextBlock _catalogDownshiftHeading;
        private TextBlock _catalogSummary;
        private Border _catalogFitPanel;
        private Border _catalogFitRail;
        private TextBlock _catalogFitRailText;
        private Border _catalogUsePanel;
        private Border _catalogUseRail;
        private TextBlock _catalogUseRailText;
        private Border _catalogLaunchCell;
        private Border _catalogUpshiftCell;
        private Border _catalogDownshiftCell;
        private bool _loadingCatalogFilters;
        private TextBlock _liveStatus;
        private TextBlock _recordStatus;
        private TextBlock _previewStatus;
        private TextBlock _errorStatus;
        private TextBlock _overlayFeedback;
        private TextBlock _browserFeedback;
        private TextBlock _contributionFeedback;
        private TextBlock _advancedFeedback;
        private TextBlock _installedDatasetStatus;
        private TextBox _updateEndpoint;
        private Button _checkUpdatesButton;
        private TextBlock _updateStatus;
        private TextBlock _supportedSimulators;
        private VerificationControl _verification;
        private Button _contributeLiveButton;
        private Button _showPopupButton;
        private Button _closePreviewButton;
        private Button _savePopupSettingsButton;
        private TextBlock _healthSimulator;
        private TextBlock _healthMatch;
        private TextBlock _healthDataset;
        private TextBlock _healthPopup;
        private TextBlock _garageEyebrow;
        private TextBlock _garageCarName;
        private TextBlock _garageCarClass;
        private TextBlock _garageWheel;
        private TextBlock _garageWheelDetail;
        private TextBlock _garageShifter;
        private TextBlock _garageShifterDetail;
        private TextBlock _garageLaunch;
        private TextBlock _garageUpshift;
        private TextBlock _garageDownshift;
        private TextBlock _garageSummary;
        private Border _popupPreview;
        private PopupPreviewVariant _detailedPopupPreview;
        private PopupPreviewVariant _compactPopupPreview;
        private readonly Dictionary<string, RadioButton> _themeChoices =
            new Dictionary<string, RadioButton>(StringComparer.OrdinalIgnoreCase);
        private readonly Dictionary<string, Border> _themeCards =
            new Dictionary<string, Border>(StringComparer.OrdinalIgnoreCase);
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
            panel.Children.Add(CreateHealthStrip());

            _tabs = new SHTabControl
            {
                HorizontalAlignment = HorizontalAlignment.Stretch,
                TabsHorizontalAlignement = HorizontalAlignment.Left,
            };
            _tabs.Items.Add(CreateTab("Garage", CreateOverlayTab()));
            _tabs.Items.Add(CreateTab("Car browser", CreateBrowserTab()));
            _tabs.Items.Add(CreateTab("Contribute data", CreateContributionTab()));
            _tabs.Items.Add(CreateTab("System", CreateAdvancedTab()));
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

        private UIElement CreateHealthStrip()
        {
            var strip = new Border
            {
                Name = "PluginHealthStrip",
                BorderBrush = new SolidColorBrush(Color.FromArgb(80, 120, 150, 180)),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(5),
                Padding = new Thickness(12, 8, 12, 8),
                Margin = new Thickness(0, 0, 0, 16),
            };
            var cells = new WrapPanel { Orientation = Orientation.Horizontal };
            cells.Children.Add(CreateHealthCell("SIMULATOR", out _healthSimulator));
            cells.Children.Add(CreateHealthCell("MATCH", out _healthMatch));
            cells.Children.Add(CreateHealthCell("DATASET", out _healthDataset));
            cells.Children.Add(CreateHealthCell("POPUP", out _healthPopup));
            strip.Child = cells;
            return strip;
        }

        private static UIElement CreateHealthCell(string label, out TextBlock value)
        {
            var cell = new StackPanel
            {
                Width = 205,
                Margin = new Thickness(0, 0, 12, 0),
            };
            cell.Children.Add(new TextBlock
            {
                Text = label,
                FontSize = 10,
                FontWeight = FontWeights.Bold,
                Opacity = 0.58,
            });
            value = new TextBlock
            {
                FontSize = 13,
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
            };
            cell.Children.Add(value);
            return cell;
        }

        private static Border CreateGarageBand(string label)
        {
            var band = new Border
            {
                BorderBrush = new SolidColorBrush(Color.FromArgb(70, 120, 150, 180)),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(4),
                Margin = new Thickness(0, 0, 0, 8),
            };
            AutomationProperties.SetName(band, label + " guidance");
            return band;
        }

        private static UIElement CreateGarageValue(
            string label,
            out TextBlock value,
            out TextBlock detail)
        {
            var cell = new StackPanel { Margin = new Thickness(12, 10, 12, 10) };
            cell.Children.Add(new TextBlock
            {
                Text = label,
                FontSize = 10,
                FontWeight = FontWeights.Bold,
                Foreground = new SolidColorBrush(Color.FromRgb(50, 190, 235)),
                Margin = new Thickness(0, 0, 0, 3),
            });
            value = new TextBlock
            {
                FontSize = 15,
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
            };
            detail = new TextBlock
            {
                FontSize = 12,
                Opacity = 0.72,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 2, 0, 0),
            };
            cell.Children.Add(value);
            cell.Children.Add(detail);
            return cell;
        }

        private static UIElement CreateGarageTechnique(string label, out TextBlock value)
        {
            var cell = new StackPanel { Margin = new Thickness(11, 9, 11, 10) };
            cell.Children.Add(new TextBlock
            {
                Text = label,
                FontSize = 10,
                FontWeight = FontWeights.Bold,
                Foreground = new SolidColorBrush(Color.FromRgb(50, 190, 235)),
                Margin = new Thickness(0, 0, 0, 3),
            });
            value = new TextBlock
            {
                FontSize = 13,
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
            };
            cell.Children.Add(value);
            return cell;
        }

        private UIElement CreatePopupPreview()
        {
            _popupPreview = new Border
            {
                Name = "PopupPreviewCard",
                Width = 500,
                Height = 297,
                HorizontalAlignment = HorizontalAlignment.Left,
            };
            _detailedPopupPreview = CreatePopupPreviewVariant(false);
            _compactPopupPreview = CreatePopupPreviewVariant(true);
            var layers = new Grid();
            layers.Children.Add(_detailedPopupPreview.View);
            layers.Children.Add(_compactPopupPreview.View);
            _popupPreview.Child = layers;
            return _popupPreview;
        }

        private PopupPreviewVariant CreatePopupPreviewVariant(bool compact)
        {
            double cardWidth = compact ? 520 : 720;
            double cardHeight = compact ? 360 : 428;
            double left = compact ? 16 : 22;
            double contentWidth = cardWidth - left * 2;
            double headerTop = compact ? 12 : 16;
            double markSize = compact ? 28 : 36;
            double headerRule = compact ? 55 : 68;
            double fitTop = compact ? 60 : 80;
            double fitHeight = compact ? 58 : 82;
            double useTop = compact ? 124 : 166;
            double useHeight = compact ? 78 : 92;
            double noteTop = compact ? 206 : 264;
            double noteHeight = compact ? 89 : 99;
            double footerRule = compact ? 303 : 371;
            double railWidth = compact ? 24 : 30;
            double fitIcon = compact ? 30 : 42;
            double fitHeadSize = compact ? 13 : 16;
            double fitSubSize = compact ? 10.5 : 12.5;
            double useHeadSize = compact ? 12 : 15;
            double useValueSize = compact ? 11 : 13;

            var variant = new PopupPreviewVariant { Compact = compact };
            var canvas = new Canvas { Width = cardWidth, Height = cardHeight };
            variant.Card = new Border
            {
                Width = cardWidth,
                Height = cardHeight,
                CornerRadius = new CornerRadius(compact ? 10 : 14),
                BorderThickness = new Thickness(2),
                Child = canvas,
            };
            variant.View = new Viewbox
            {
                Name = compact ? "CompactPopupPreview" : "DetailedPopupPreview",
                Stretch = Stretch.Fill,
                Child = variant.Card,
                Visibility = compact ? Visibility.Collapsed : Visibility.Visible,
            };

            double stripeWidth = compact ? 16 : 20;
            double stripeTop = 9;
            double stripeBottom = compact ? 55 : 68;
            double stripeHeight = stripeBottom - stripeTop;
            double stripeLeft = cardWidth - (compact ? 81 : 95);
            string[] stripeNames = {
                "HeaderStripeDriver", "HeaderStripeAccent", "HeaderStripeCar"
            };
            for (int index = 0; index < stripeNames.Length; index++)
            {
                Border stripe = AddPreviewBox(
                    variant, canvas, stripeNames[index],
                    stripeLeft + index * stripeWidth, stripeTop,
                    stripeWidth, stripeHeight, 0);
                stripe.RenderTransform = new SkewTransform(-24, 0);
                stripe.RenderTransformOrigin = new Point(0, 0);
                stripe.Visibility = Visibility.Visible;
            }

            var mark = new Image
            {
                Source = _plugin.HeaderPictureIcon,
                Stretch = Stretch.Uniform,
            };
            Place(canvas, mark, left, headerTop + 1, markSize, markSize);
            AddPreviewText(variant, canvas, "Car", left + markSize + 14, headerTop - 1,
                contentWidth - markSize - (compact ? 138 : 174), compact ? 26 : 32,
                compact ? 17 : 22, true);
            AddPreviewText(variant, canvas, "Class", left + markSize + 14,
                headerTop + (compact ? 23 : 28), contentWidth - markSize - 170,
                compact ? 16 : 20, compact ? 10.5 : 12, false);
            double badgeWidth = compact ? 110 : 140;
            Border badge = AddPreviewBox(variant, canvas, "Badge",
                (cardWidth - badgeWidth) / 2, compact ? 308 : 376,
                badgeWidth, 22, compact ? 5 : 7);
            var badgeText = new TextBlock
            {
                Text = "PREVIEW - NOT LIVE",
                FontSize = compact ? 9 : 10.5,
                FontWeight = FontWeights.Bold,
                TextAlignment = TextAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
            };
            variant.Text["BadgeText"] = badgeText;
            badge.Child = badgeText;
            AddPreviewBox(variant, canvas, "HeaderRule", left, headerRule,
                contentWidth, 1, 0);

            Border fitPanel = AddPreviewBox(variant, canvas, "FitPanel", left, fitTop,
                contentWidth, fitHeight, compact ? 5 : 7);
            fitPanel.BorderThickness = new Thickness(1);
            Border fitRail = AddPreviewBox(variant, canvas, "FitRail", left + 1,
                fitTop + 1, railWidth, fitHeight - 2, 0);
            fitRail.Child = RotatedRailLabel("FIT", compact ? 14 : 16);
            variant.Text["FitRail"] = (TextBlock)fitRail.Child;
            double fitCellLeft = left + railWidth + 1;
            double fitCellWidth = (contentWidth - railWidth - 2) / 2;
            double iconTop = fitTop + (fitHeight - fitIcon) / 2;
            Canvas wheelGlyph = CreateWheelGlyph(variant, fitIcon);
            variant.WheelGlyph = wheelGlyph;
            Place(canvas, wheelGlyph, fitCellLeft + 14, iconTop, fitIcon, fitIcon);
            Canvas shiftGlyph = CreateShifterGlyph(variant, fitIcon);
            variant.ShiftGlyph = shiftGlyph;
            Place(canvas, shiftGlyph, fitCellLeft + fitCellWidth + 14,
                iconTop, fitIcon, fitIcon);
            double fitTextLeft = fitCellLeft + fitIcon + 22;
            double secondTextLeft = fitCellLeft + fitCellWidth + fitIcon + 22;
            double fitTextWidth = fitCellWidth - fitIcon - 30;
            double fitHeadTop = compact ? fitTop + 7 : fitTop + fitHeight / 2 - fitHeadSize - 3;
            double fitSubTop = compact ? fitTop + 26 : fitTop + fitHeight / 2 + 2;
            double fitMarkerTop = compact ? fitTop + 44 : fitTop + fitHeight - 21;
            AddPreviewText(variant, canvas, "Wheel", fitTextLeft, fitHeadTop,
                fitTextWidth, fitHeadSize + 6, fitHeadSize, true);
            AddPreviewText(variant, canvas, "WheelDetail", fitTextLeft, fitSubTop,
                fitTextWidth, fitSubSize + 6, fitSubSize, false);
            AddPreviewText(variant, canvas, "WheelMarker", fitTextLeft, fitMarkerTop,
                fitTextWidth, fitSubSize + 4, compact ? 7.5 : fitSubSize - 1, false);
            AddPreviewBox(variant, canvas, "FitDivider", fitCellLeft + fitCellWidth,
                fitTop + 8, 1, fitHeight - 16, 0);
            AddPreviewText(variant, canvas, "Shifter", secondTextLeft, fitHeadTop,
                fitTextWidth, fitHeadSize + 6, fitHeadSize, true);
            AddPreviewText(variant, canvas, "ShifterDetail", secondTextLeft, fitSubTop,
                fitTextWidth, fitSubSize + 6, fitSubSize, false);
            AddPreviewText(variant, canvas, "ShifterMarker", secondTextLeft, fitMarkerTop,
                fitTextWidth, fitSubSize + 4, compact ? 7.5 : fitSubSize - 1, false);

            Border usePanel = AddPreviewBox(variant, canvas, "UsePanel", left, useTop,
                contentWidth, useHeight, compact ? 5 : 7);
            usePanel.BorderThickness = new Thickness(1);
            Border useRail = AddPreviewBox(variant, canvas, "UseRail", left + 1,
                useTop + 1, railWidth, useHeight - 2, 0);
            useRail.Child = RotatedRailLabel("USE", compact ? 14 : 16);
            variant.Text["UseRail"] = (TextBlock)useRail.Child;
            double useCellLeft = left + railWidth + 1;
            double useCellWidth = (contentWidth - railWidth - 2) / 3;
            string[] moments = { "Launch", "Upshift", "Downshift" };
            for (int index = 0; index < moments.Length; index++)
            {
                string moment = moments[index];
                double x = useCellLeft + useCellWidth * index;
                AddPreviewBox(variant, canvas, moment + "Cell", x + 1, useTop + 2,
                    useCellWidth - 2, useHeight - 4, 0);
                if (index > 0)
                {
                    AddPreviewBox(variant, canvas, "UseDivider" + moment, x,
                        useTop + 8, 1, useHeight - 16, 0);
                }
                AddPreviewText(variant, canvas, moment + "Head", x + 14,
                    useTop + 10, useCellWidth - 24, useHeadSize + 6,
                    useHeadSize, true).Text = moment;
                AddPreviewText(variant, canvas, moment + "Value", x + 14,
                    useTop + useHeadSize + 16, useCellWidth - 24, useValueSize + 6,
                    useValueSize, false);
                AddPreviewText(variant, canvas, moment + "Detail", x + 14,
                    useTop + useHeadSize + useValueSize + 21, useCellWidth - 24,
                    useValueSize + 5, useValueSize - 1.5, false);
                AddPreviewText(variant, canvas, moment + "Marker", x + 14,
                    useTop + useHeadSize + useValueSize * 2 + 25,
                    useCellWidth - 24, useValueSize + 2, useValueSize - 2, false);
            }

            Border note = AddPreviewBox(variant, canvas, "NotePanel", left, noteTop,
                contentWidth, noteHeight, compact ? 5 : 6);
            AddPreviewBox(variant, canvas, "NoteRail", left, noteTop, 2, noteHeight, 0);
            Border noteIcon = AddPreviewBox(variant, canvas, "NoteIconWell",
                left + 10, noteTop + 6, 22, 22, 11);
            var noteIconText = new TextBlock
            {
                Text = "i",
                FontSize = compact ? 26 : 30,
                FontWeight = FontWeights.Bold,
                FontStyle = FontStyles.Italic,
                TextAlignment = TextAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
            };
            variant.Text["NoteIcon"] = noteIconText;
            noteIcon.Child = noteIconText;
            AddPreviewText(variant, canvas, "Summary", left + 38, noteTop + 7,
                contentWidth - 50, noteHeight - 14, compact ? 11 : 12.5, false);
            AddPreviewBox(variant, canvas, "FooterRule", left, footerRule,
                contentWidth, 1, 0);
            AddPreviewText(variant, canvas, "Evidence", left, footerRule + 6,
                compact ? 176 : 250, compact ? 18 : 19,
                compact ? 10 : 11.5, false);
            TextBlock dataset = AddPreviewText(variant, canvas, "Dataset",
                cardWidth - left - (compact ? 140 : 180), footerRule + 6,
                compact ? 140 : 180, compact ? 18 : 19,
                compact ? 10 : 11.5, false);
            dataset.TextAlignment = TextAlignment.Right;
            return variant;
        }

        private static Border AddPreviewBox(
            PopupPreviewVariant variant, Canvas canvas, string name,
            double left, double top, double width, double height, double radius)
        {
            var box = new Border
            {
                Width = width,
                Height = height,
                CornerRadius = new CornerRadius(radius),
            };
            variant.Box[name] = box;
            Place(canvas, box, left, top, width, height);
            return box;
        }

        private static TextBlock AddPreviewText(
            PopupPreviewVariant variant, Panel parent, string name,
            double left, double top, double width, double height,
            double size, bool bold)
        {
            var text = new TextBlock
            {
                Width = width,
                Height = height,
                FontSize = size,
                FontWeight = bold ? FontWeights.Bold : FontWeights.Normal,
                TextTrimming = TextTrimming.CharacterEllipsis,
                TextWrapping = TextWrapping.Wrap,
            };
            variant.Text[name] = text;
            Canvas canvas = parent as Canvas;
            if (canvas != null)
            {
                Place(canvas, text, left, top, width, height);
            }
            else
            {
                parent.Children.Add(text);
            }
            return text;
        }

        private static TextBlock RotatedRailLabel(string label, double size)
        {
            return new TextBlock
            {
                Text = label,
                FontSize = size,
                FontWeight = FontWeights.Bold,
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
                LayoutTransform = new RotateTransform(270),
            };
        }

        private static Canvas CreateWheelGlyph(PopupPreviewVariant variant, double size)
        {
            var glyph = new Canvas { Width = size, Height = size };
            var ring = new Ellipse { Width = size - 4, Height = size - 4, StrokeThickness = 3 };
            Canvas.SetLeft(ring, 2);
            Canvas.SetTop(ring, 2);
            glyph.Children.Add(ring);
            variant.Glyphs.Add(ring);
            foreach (double angle in new[] { -90.0, 30.0, 150.0 })
            {
                var spoke = new Line
                {
                    X1 = size / 2,
                    Y1 = size / 2,
                    X2 = size / 2,
                    Y2 = 4,
                    StrokeThickness = 2,
                    RenderTransform = new RotateTransform(angle, size / 2, size / 2),
                };
                glyph.Children.Add(spoke);
                variant.Glyphs.Add(spoke);
            }
            return glyph;
        }

        private static Canvas CreateShifterGlyph(PopupPreviewVariant variant, double size)
        {
            var glyph = new Canvas { Width = size, Height = size };
            var knob = new Ellipse
            {
                Width = size * 0.3,
                Height = size * 0.3,
                StrokeThickness = 3,
            };
            Canvas.SetLeft(knob, size * 0.35);
            Canvas.SetTop(knob, size * 0.08);
            glyph.Children.Add(knob);
            variant.Glyphs.Add(knob);
            var shaft = new Line
            {
                X1 = size * 0.5,
                Y1 = size * 0.36,
                X2 = size * 0.5,
                Y2 = size * 0.78,
                StrokeThickness = 3,
            };
            glyph.Children.Add(shaft);
            variant.Glyphs.Add(shaft);
            var baseLine = new Line
            {
                X1 = size * 0.2,
                Y1 = size * 0.83,
                X2 = size * 0.8,
                Y2 = size * 0.83,
                StrokeThickness = 3,
            };
            glyph.Children.Add(baseLine);
            variant.Glyphs.Add(baseLine);
            return glyph;
        }

        private static void Place(
            Canvas canvas, FrameworkElement element,
            double left, double top, double width, double height)
        {
            element.Width = width;
            element.Height = height;
            Canvas.SetLeft(element, left);
            Canvas.SetTop(element, top);
            canvas.Children.Add(element);
        }

        private static void Move(
            FrameworkElement element,
            double left, double top, double width, double height)
        {
            element.Width = width;
            element.Height = height;
            Canvas.SetLeft(element, left);
            Canvas.SetTop(element, top);
        }

        private void AddThemeChoice(string label, string value)
        {
            ThemePreviewPalette palette = PreviewPalette(value);
            var card = new Border
            {
                Width = 226,
                Height = 58,
                BorderBrush = new SolidColorBrush(Color.FromArgb(90, 120, 150, 180)),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(4),
                Padding = new Thickness(7, 6, 7, 6),
                Margin = new Thickness(0, 0, 8, 8),
            };
            var content = new Grid();
            content.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(46) });
            content.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            var swatches = new Grid
            {
                Width = 38,
                Height = 38,
                HorizontalAlignment = HorizontalAlignment.Left,
            };
            swatches.RowDefinitions.Add(new RowDefinition());
            swatches.RowDefinitions.Add(new RowDefinition());
            swatches.RowDefinitions.Add(new RowDefinition());
            var first = new Border { Background = palette.Card };
            var second = new Border { Background = palette.Accent };
            var third = new Border { Background = palette.Car };
            Grid.SetRow(second, 1);
            Grid.SetRow(third, 2);
            swatches.Children.Add(first);
            swatches.Children.Add(second);
            swatches.Children.Add(third);
            content.Children.Add(swatches);
            var title = new TextBlock
            {
                Text = label,
                FontWeight = FontWeights.SemiBold,
                VerticalAlignment = VerticalAlignment.Center,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(4, 0, 0, 0),
            };
            Grid.SetColumn(title, 1);
            content.Children.Add(title);
            card.Child = content;

            var choice = new RadioButton
            {
                GroupName = "PopupTheme",
                Tag = value,
                Content = card,
                Margin = new Thickness(0),
                VerticalContentAlignment = VerticalAlignment.Center,
            };
            AutomationProperties.SetName(choice, label + " popup theme");
            choice.Checked += PopupThemeChecked;
            _themeChoices[value] = choice;
            _themeCards[value] = card;
            _popupTheme.Children.Add(choice);
        }

        private void SelectThemeChoice(string value)
        {
            RadioButton choice;
            if (!_themeChoices.TryGetValue(value ?? string.Empty, out choice))
            {
                choice = _themeChoices[PopupPreferences.DefaultTheme];
            }
            choice.IsChecked = true;
            UpdateThemeChoiceVisuals();
        }

        private string SelectedPopupTheme()
        {
            foreach (KeyValuePair<string, RadioButton> choice in _themeChoices)
            {
                if (choice.Value.IsChecked == true)
                {
                    return choice.Key;
                }
            }
            return PopupPreferences.DefaultTheme;
        }

        private void PopupThemeChecked(object sender, RoutedEventArgs eventArgs)
        {
            UpdateThemeChoiceVisuals();
            MarkPopupSettingsDirty();
        }

        private void UpdateThemeChoiceVisuals()
        {
            foreach (KeyValuePair<string, Border> card in _themeCards)
            {
                bool selected = _themeChoices[card.Key].IsChecked == true;
                card.Value.BorderBrush = selected
                    ? PreviewPalette(card.Key).Accent
                    : new SolidColorBrush(Color.FromArgb(90, 120, 150, 180));
                card.Value.BorderThickness = new Thickness(selected ? 2 : 1);
            }
        }

        private static ThemePreviewPalette PreviewPalette(string theme)
        {
            if (theme == PopupPreferences.SixtiesTheme)
            {
                return new ThemePreviewPalette(
                    "#FFF3E7CF", "#FF17324D", "#FFE4D3B5", "#FF17324D",
                    "#FF263849", "#FFFFFFFF", "#FF586775", "#FF779FC2",
                    "#FFE5662F", "#FFFF8C52", "#FF71A7C7", "#FF71A7C7",
                    "#FFE25D36", "#FF335E7C", "#22000000", "#12335E7C",
                    "#FFE5662F", "#FFFFFFFF", "#FF17324D", "#FFFFFFFF",
                    "#FFB9CCDA");
            }
            if (theme == PopupPreferences.SeventiesTheme)
            {
                return new ThemePreviewPalette(
                    "#FF031C18", "#FF0A2A24", "#FF0A3028", "#FFF2E6C5",
                    "#FFE4D9BD", "#FFF2E6C5", "#FF9EB6A6", "#FF35594C",
                    "#FFB89535", "#FFE65332", "#FF69B88D", "#33B89535",
                    "#3DE65332", "#3369B88D", "#2EE65332", "#2969B88D",
                    "#FFE65332", "#FFF2E6C5", "#FFF2E6C5", "#FFF2E6C5",
                    "#FF9EB6A6");
            }
            if (theme == PopupPreferences.EightiesTheme)
            {
                return new ThemePreviewPalette(
                    "#F5090909", "#FF171511", "#FF201B12", "#FFF3E8CC",
                    "#FFE9E1D1", "#FFF3E8CC", "#FFAA9F88", "#FF66552C",
                    "#FFD2AD4F", "#FFD43D32", "#FFD2AD4F", "#3DD2AD4F",
                    "#42D43D32", "#35D2AD4F", "#32D43D32", "#2BD2AD4F",
                    "#FFF4EFE2", "#FFB51F28", "#FFF3E8CC", "#FFF3E8CC",
                    "#FFAA9F88");
            }
            if (theme == PopupPreferences.NinetiesTheme)
            {
                return new ThemePreviewPalette(
                    "#FFF1F3F4", "#FF173C78", "#FFE1E5E8", "#FF20252A",
                    "#FF333A40", "#FFFFFFFF", "#FF66717A", "#FF7B8791",
                    "#FF164FA3", "#FFE12F31", "#FF14814B", "#FF2D75D5",
                    "#FFE12F31", "#FF14814B", "#22000000", "#11000000",
                    "#FFE12F31", "#FFFFFFFF", "#FFFFFFFF", "#FFFFFFFF",
                    "#FF9EB4CE");
            }
            if (theme == PopupPreferences.TwoThousandsTheme)
            {
                return new ThemePreviewPalette(
                    "#FF161A1E", "#FFC9CED1", "#FF20262B", "#FFF4F6F7",
                    "#FFD5DDE1", "#FF172027", "#FF8C9AA2", "#FF7B878D",
                    "#FFD22E32", "#FFE44B3B", "#FF167D72", "#FF5C6D78",
                    "#FFD22E32", "#FF167D72", "#35E44B3B", "#30167D72",
                    "#FFD22E32", "#FFFFFFFF", "#FFFFFFFF", "#FFFFFFFF",
                    "#FF52636C");
            }
            if (theme == PopupPreferences.TwentyTensTheme)
            {
                return new ThemePreviewPalette(
                    "#FFF1F2EF", "#FF171A1D", "#FFE3E6E4", "#FF181B1E",
                    "#FF30383D", "#FFF7F8F5", "#FF667178", "#FF899196",
                    "#FFD61F2C", "#FFFF5A42", "#FF00A69A", "#FF343A40",
                    "#FFD61F2C", "#FF008D85", "#38FF5A42", "#3300A69A",
                    "#FFD61F2C", "#FFFFFFFF", "#FFFFFFFF", "#FFFFFFFF",
                    "#FF9DA8AD");
            }
            if (theme == PopupPreferences.ModernLightTheme)
            {
                return new ThemePreviewPalette(
                    "#FFF5F6F4", "#FFF9FAFA", "#FFEEF1F2", "#FF20262B",
                    "#FF3C454C", "#FF20262B", "#FF69737B", "#FF8B9399",
                    "#FF246FDB", "#FFFF4B13", "#FF3E8747", "#FF2D78DD",
                    "#FFFF5A1F", "#FF3E8747", "#1FFF5A1F", "#1F3E8747",
                    "#FFFF4714", "#FFFFFFFF", "#FFFFFFFF", "#FFFFFFFF",
                    "#FF66717A");
            }
            if (theme == PopupPreferences.GPLClassicTheme)
            {
                return new ThemePreviewPalette(
                    "#F5121211", "#FF181716", "#FF1D1B17", "#FFF3E7CE",
                    "#FFF3E7CE", "#FFF5EBDD", "#FFB7A98E", "#FF8B7654",
                    "#FFD4A44D", "#FFD66A43", "#FF6F98C0", "#FFA43D29",
                    "#FF315675", "#FF315675", "#28D66A43", "#286F98C0",
                    "#FFA43D29", "#FFF3E7CE", "#FFF3E7CE", "#FFF3E7CE",
                    "#FFB7A98E");
            }
            return new ThemePreviewPalette(
                "#F2050D14", "#D9081722", "#B5091720", "#FFF4F7F9",
                "#FFC4D9E5", "#FFF4F7F9", "#FF7FA6B9", "#FF0E8DA7",
                "#FF08C7E8", "#FFF05235", "#FF3FB68D", "#FF07584E",
                "#D9F05235", "#C93FB68D", "#2EF05235", "#293FB68D",
                "#FFD93320", "#FFFFFFFF", "#FFFFFFFF", "#FFFFFFFF",
                "#FF7FA6B9");
        }

        private static Brush PreviewBrush(string color)
        {
            return new SolidColorBrush((Color)ColorConverter.ConvertFromString(color));
        }

        private UIElement CreateOverlayTab()
        {
            var panel = CreateTabPanel();
            var workspace = new WrapPanel
            {
                Orientation = Orientation.Horizontal,
            };

            var garage = new StackPanel
            {
                Name = "GarageLiveColumn",
                Width = 520,
                Margin = new Thickness(0, 0, 22, 18),
            };
            AddSectionHeading(garage, "Current car");
            var statusPanel = new StackPanel { Margin = new Thickness(16) };
            _garageEyebrow = new TextBlock
            {
                Text = "WAITING FOR TELEMETRY",
                FontSize = 11,
                FontWeight = FontWeights.Bold,
                Foreground = new SolidColorBrush(Color.FromRgb(50, 190, 235)),
                Margin = new Thickness(0, 0, 0, 4),
            };
            _liveStatus = new TextBlock
            {
                Visibility = Visibility.Collapsed,
            };
            _garageCarName = new TextBlock
            {
                FontSize = 22,
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
            };
            _garageCarClass = new TextBlock
            {
                Margin = new Thickness(0, 2, 0, 14),
                Opacity = 0.72,
                TextWrapping = TextWrapping.Wrap,
            };
            _recordStatus = new TextBlock
            {
                Margin = new Thickness(0, 8, 0, 0),
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.62,
                FontSize = 11,
            };
            _errorStatus = new TextBlock
            {
                Margin = new Thickness(0, 6, 0, 0),
                Foreground = Brushes.IndianRed,
                TextWrapping = TextWrapping.Wrap,
            };
            statusPanel.Children.Add(_garageEyebrow);
            statusPanel.Children.Add(_garageCarName);
            statusPanel.Children.Add(_garageCarClass);
            statusPanel.Children.Add(_liveStatus);

            var fitBand = CreateGarageBand("FIT");
            var fitGrid = new Grid();
            fitGrid.ColumnDefinitions.Add(new ColumnDefinition());
            fitGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1) });
            fitGrid.ColumnDefinitions.Add(new ColumnDefinition());
            var fitDivider = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(70, 120, 150, 180)),
            };
            Grid.SetColumn(fitDivider, 1);
            fitGrid.Children.Add(fitDivider);
            fitGrid.Children.Add(CreateGarageValue("WHEEL", out _garageWheel, out _garageWheelDetail));
            UIElement shifter = CreateGarageValue("SHIFTER", out _garageShifter, out _garageShifterDetail);
            Grid.SetColumn(shifter, 2);
            fitGrid.Children.Add(shifter);
            fitBand.Child = fitGrid;
            statusPanel.Children.Add(fitBand);

            var useBand = CreateGarageBand("USE");
            var useGrid = new Grid();
            useGrid.ColumnDefinitions.Add(new ColumnDefinition());
            useGrid.ColumnDefinitions.Add(new ColumnDefinition());
            useGrid.ColumnDefinitions.Add(new ColumnDefinition());
            useGrid.Children.Add(CreateGarageTechnique("LAUNCH", out _garageLaunch));
            UIElement upshift = CreateGarageTechnique("UPSHIFT", out _garageUpshift);
            Grid.SetColumn(upshift, 1);
            useGrid.Children.Add(upshift);
            UIElement downshift = CreateGarageTechnique("DOWNSHIFT", out _garageDownshift);
            Grid.SetColumn(downshift, 2);
            useGrid.Children.Add(downshift);
            useBand.Child = useGrid;
            statusPanel.Children.Add(useBand);

            _garageSummary = new TextBlock
            {
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(2, 12, 2, 0),
                Opacity = 0.82,
                MaxHeight = 74,
            };
            statusPanel.Children.Add(_garageSummary);
            statusPanel.Children.Add(_recordStatus);
            statusPanel.Children.Add(_errorStatus);
            Border garageCard = CreateGroupBorder(statusPanel, new Thickness(0, 0, 0, 12));
            garageCard.Name = "GarageGuidanceCard";
            garage.Children.Add(garageCard);

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
            garage.Children.Add(actionRow);
            _overlayFeedback = CreateFeedbackText(new Thickness(0, 0, 0, 22));
            garage.Children.Add(_overlayFeedback);
            workspace.Children.Add(garage);

            var popup = new StackPanel
            {
                Name = "GaragePopupColumn",
                Width = 520,
                Margin = new Thickness(0, 0, 0, 18),
            };
            AddSectionHeading(popup, "Popup preview");
            popup.Children.Add(CreatePopupPreview());
            popup.Children.Add(new TextBlock
            {
                Text = "This preview follows the selected size and theme. Auto resolves from the current car's curated year.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.72,
                Margin = new Thickness(0, 8, 0, 18),
            });

            workspace.Children.Add(popup);
            panel.Children.Add(workspace);

            // Popup behavior spans the page instead of sharing the preview's
            // 520-pixel column. A theme choice measures about 258 pixels, so
            // two could never fit that column and all nine stacked one per row,
            // putting the save button far below the fold.
            var behavior = new StackPanel
            {
                Name = "GaragePopupBehavior",
                Margin = new Thickness(0, 4, 0, 18),
            };
            AddSectionHeading(behavior, "Popup behavior");

            var behaviorRow = new WrapPanel { Orientation = Orientation.Horizontal };
            var durationBlock = new StackPanel
            {
                Width = 500,
                Margin = new Thickness(0, 0, 44, 16),
            };
            durationBlock.Children.Add(
                CreateFieldLabel("Automatic popup duration", new Thickness(0, 0, 0, 8)));
            var durationRow = new Grid
            {
                MaxWidth = 500,
                HorizontalAlignment = HorizontalAlignment.Left,
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
            durationBlock.Children.Add(durationRow);
            behaviorRow.Children.Add(durationBlock);

            var sizeBlock = new StackPanel
            {
                Width = 380,
                Margin = new Thickness(0, 0, 0, 16),
            };
            sizeBlock.Children.Add(CreateFieldLabel("Popup size", new Thickness(0, 0, 0, 8)));
            _popupSize = new ComboBox
            {
                Name = "PopupSizeSelector",
                Height = 32,
                MinWidth = 240,
                MaxWidth = 360,
                HorizontalAlignment = HorizontalAlignment.Left,
            };
            _popupSize.Items.Add(CreateChoiceItem("Detailed - 720 x 428", "detailed"));
            _popupSize.Items.Add(CreateChoiceItem("Compact - 520 x 360", "compact"));
            SelectChoice(_popupSize, _plugin.PopupSize, 0);
            _popupSize.SelectionChanged += PopupSizeChanged;
            sizeBlock.Children.Add(_popupSize);
            behaviorRow.Children.Add(sizeBlock);
            behavior.Children.Add(behaviorRow);

            behavior.Children.Add(CreateFieldLabel("Popup theme", new Thickness(0, 6, 0, 8)));
            _popupTheme = new WrapPanel
            {
                Name = "PopupThemeSelector",
                Orientation = Orientation.Horizontal,
                MaxWidth = 1084,
                HorizontalAlignment = HorizontalAlignment.Left,
            };
            AddThemeChoice("Auto by car era", PopupPreferences.DefaultTheme);
            AddThemeChoice("1960s Roadbook", PopupPreferences.SixtiesTheme);
            AddThemeChoice("1970s Works", PopupPreferences.SeventiesTheme);
            AddThemeChoice("1980s Black Gold", PopupPreferences.EightiesTheme);
            AddThemeChoice("1990s Touring", PopupPreferences.NinetiesTheme);
            AddThemeChoice("2000s Endurance Alloy", PopupPreferences.TwoThousandsTheme);
            AddThemeChoice("2010s Hybrid Vector", PopupPreferences.TwentyTensTheme);
            AddThemeChoice("Modern Night", PopupPreferences.ModernTheme);
            AddThemeChoice("Modern Light", PopupPreferences.ModernLightTheme);
            AddThemeChoice("GPL Classic", PopupPreferences.GPLClassicTheme);
            SelectThemeChoice(_plugin.PopupThemePreference);
            _popupSettingsDirty = false;
            _overlayFeedback.Text = string.Empty;
            behavior.Children.Add(_popupTheme);
            behavior.Children.Add(new TextBlock
            {
                Text = "Cars without an established year use Modern. Load and position the matching packaged layout once in Dash Studio.",
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.78,
                Margin = new Thickness(0, 10, 0, 14),
                MaxWidth = 700,
            });
            _savePopupSettingsButton = CreatePrimaryButton("Save changes", 150, SaveClicked);
            behavior.Children.Add(_savePopupSettingsButton);
            panel.Children.Add(behavior);
            return panel;
        }

        private UIElement CreateBrowserTab()
        {
            var panel = CreateTabPanel();
            AddSectionHeading(panel, "Curated car catalog");
            panel.Children.Add(new TextBlock
            {
                Text = "Find a car by simulator, era, wheel, or shifter. Selecting a row only opens its guidance here; the live car and popup stay untouched until you choose Show overlay.",
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 12),
                MaxWidth = 900,
            });
            _previewStatus = new TextBlock
            {
                FontSize = 14,
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 10),
            };
            panel.Children.Add(_previewStatus);

            var filters = new WrapPanel { Margin = new Thickness(0, 0, 0, 10) };
            _catalogSearch = new TextBox
            {
                Height = 34,
                Width = 245,
                Margin = new Thickness(0, 0, 8, 8),
                VerticalContentAlignment = VerticalAlignment.Center,
                ToolTip = "Search car name, class, or record id",
            };
            AutomationProperties.SetName(_catalogSearch, "Search curated cars");
            _catalogSearch.TextChanged += CatalogFilterChanged;
            filters.Children.Add(_catalogSearch);
            _catalogSimulator = CreateCatalogFilter("Simulator", 145);
            _catalogDecade = CreateCatalogFilter("Decade", 130);
            _catalogWheel = CreateCatalogFilter("Wheel", 155);
            _catalogShifter = CreateCatalogFilter("Shifter", 165);
            filters.Children.Add(_catalogSimulator);
            filters.Children.Add(_catalogDecade);
            filters.Children.Add(_catalogWheel);
            filters.Children.Add(_catalogShifter);
            panel.Children.Add(filters);

            var workspace = new Grid
            {
                Name = "CatalogWorkspace",
                Width = 1040,
                HorizontalAlignment = HorizontalAlignment.Left,
            };
            workspace.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(320) });
            workspace.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(18) });
            workspace.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(702) });
            var browserList = new StackPanel();
            _catalogCount = new TextBlock
            {
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 0, 0, 6),
            };
            browserList.Children.Add(_catalogCount);
            _previewCar = new ListBox
            {
                Name = "CatalogResults",
                MinHeight = 330,
                MaxHeight = 510,
                DisplayMemberPath = "DisplayLabel",
            };
            _previewCar.SelectionChanged += CatalogSelectionChanged;
            browserList.Children.Add(_previewCar);
            Grid.SetColumn(browserList, 0);
            workspace.Children.Add(browserList);

            var detail = new StackPanel { Margin = new Thickness(16) };
            detail.Children.Add(new TextBlock
            {
                Text = "CATALOG GUIDANCE",
                Foreground = Brushes.DeepSkyBlue,
                FontWeight = FontWeights.Bold,
                FontSize = 11,
                Margin = new Thickness(0, 0, 0, 5),
            });
            _catalogDetailName = new TextBlock
            {
                FontSize = 21,
                FontWeight = FontWeights.Bold,
                TextWrapping = TextWrapping.Wrap,
            };
            _catalogDetailClass = new TextBlock
            {
                Opacity = 0.75,
                Margin = new Thickness(0, 2, 0, 12),
                TextWrapping = TextWrapping.Wrap,
            };
            detail.Children.Add(_catalogDetailName);
            detail.Children.Add(_catalogDetailClass);

            var fit = new Grid { Margin = new Thickness(0, 0, 0, 10) };
            fit.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(34) });
            fit.ColumnDefinitions.Add(new ColumnDefinition());
            fit.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1) });
            fit.ColumnDefinitions.Add(new ColumnDefinition());
            _catalogFitRail = CreateCatalogRail("FIT", out _catalogFitRailText);
            _catalogFitRail.Name = "CatalogFitRail";
            var wheel = CreateCatalogGuidanceCell(
                "WHEEL", out _catalogWheelHeading, out _catalogWheelValue, out _catalogWheelDetail);
            var fitRule = new Border { Background = new SolidColorBrush(Color.FromArgb(80, 120, 150, 180)) };
            var shifter = CreateCatalogGuidanceCell(
                "SHIFTER", out _catalogShifterHeading, out _catalogShifterValue, out _catalogShifterDetail);
            Grid.SetColumn(_catalogFitRail, 0);
            Grid.SetColumn(wheel, 1);
            Grid.SetColumn(fitRule, 2);
            Grid.SetColumn(shifter, 3);
            fit.Children.Add(_catalogFitRail);
            fit.Children.Add(wheel);
            fit.Children.Add(fitRule);
            fit.Children.Add(shifter);
            _catalogFitPanel = CreateGroupBorder(fit, new Thickness(0));
            _catalogFitPanel.Name = "CatalogFitBand";
            detail.Children.Add(_catalogFitPanel);

            var use = new Grid { Margin = new Thickness(0, 0, 0, 10) };
            use.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(34) });
            use.ColumnDefinitions.Add(new ColumnDefinition());
            use.ColumnDefinitions.Add(new ColumnDefinition());
            use.ColumnDefinitions.Add(new ColumnDefinition());
            _catalogUseRail = CreateCatalogRail("USE", out _catalogUseRailText);
            _catalogUseRail.Name = "CatalogUseRail";
            Grid.SetColumn(_catalogUseRail, 0);
            use.Children.Add(_catalogUseRail);
            _catalogLaunch = CreateCatalogUseCell(
                use, 1, "LAUNCH", out _catalogLaunchHeading,
                out _catalogLaunchDetail, out _catalogLaunchCell);
            _catalogUpshift = CreateCatalogUseCell(
                use, 2, "UPSHIFT", out _catalogUpshiftHeading,
                out _catalogUpshiftDetail, out _catalogUpshiftCell);
            _catalogDownshift = CreateCatalogUseCell(
                use, 3, "DOWNSHIFT", out _catalogDownshiftHeading,
                out _catalogDownshiftDetail, out _catalogDownshiftCell);
            _catalogUsePanel = CreateGroupBorder(use, new Thickness(0));
            _catalogUsePanel.Name = "CatalogUseBand";
            detail.Children.Add(_catalogUsePanel);
            _catalogSummary = new TextBlock
            {
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.82,
                Margin = new Thickness(2, 2, 2, 12),
            };
            detail.Children.Add(_catalogSummary);
            var actions = CreateActionRow(new Thickness(0, 2, 0, 0));
            actions.Children.Add(CreatePrimaryButton("Show selected overlay", 185, PreviewCarClicked));
            _closePreviewButton = CreateSecondaryButton("Return to live car", 150, ReturnToLiveCarClicked);
            actions.Children.Add(_closePreviewButton);
            detail.Children.Add(actions);
            var detailBorder = CreateGroupBorder(detail, new Thickness(0));
            detailBorder.Name = "CatalogGuidanceCard";
            Grid.SetColumn(detailBorder, 2);
            workspace.Children.Add(detailBorder);
            panel.Children.Add(workspace);
            _browserFeedback = CreateFeedbackText(new Thickness(0, 0, 0, 8));
            panel.Children.Add(_browserFeedback);
            return panel;
        }

        private ComboBox CreateCatalogFilter(string name, double width)
        {
            var filter = new ComboBox
            {
                Width = width,
                Height = 34,
                Margin = new Thickness(0, 0, 8, 8),
                ToolTip = name,
            };
            AutomationProperties.SetName(filter, name + " filter");
            filter.SelectionChanged += CatalogFilterChanged;
            return filter;
        }

        private static Border CreateCatalogGuidanceCell(
            string heading,
            out TextBlock headingText,
            out TextBlock value,
            out TextBlock detail)
        {
            var panel = new StackPanel { Margin = new Thickness(12, 10, 12, 10) };
            headingText = new TextBlock
            {
                Text = heading,
                Foreground = Brushes.DeepSkyBlue,
                FontWeight = FontWeights.Bold,
                FontSize = 11,
                Margin = new Thickness(0, 0, 0, 4),
            };
            panel.Children.Add(headingText);
            value = new TextBlock
            {
                FontSize = 15,
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
            };
            detail = new TextBlock
            {
                Opacity = 0.72,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 2, 0, 0),
            };
            panel.Children.Add(value);
            panel.Children.Add(detail);
            return new Border { Child = panel };
        }

        private static Border CreateCatalogRail(string label, out TextBlock labelText)
        {
            labelText = new TextBlock
            {
                Text = label,
                FontWeight = FontWeights.Bold,
                FontSize = 11,
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
                LayoutTransform = new RotateTransform(270),
            };
            return new Border
            {
                Child = labelText,
                BorderThickness = new Thickness(0),
            };
        }

        private static TextBlock CreateCatalogUseCell(
            Grid parent,
            int column,
            string heading,
            out TextBlock headingText,
            out TextBlock detail,
            out Border border)
        {
            var panel = new StackPanel { Margin = new Thickness(12, 10, 12, 10) };
            headingText = new TextBlock
            {
                Text = heading,
                FontWeight = FontWeights.Bold,
                FontSize = 11,
                Margin = new Thickness(0, 0, 0, 4),
            };
            panel.Children.Add(headingText);
            var value = new TextBlock
            {
                FontSize = 14,
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
            };
            panel.Children.Add(value);
            detail = new TextBlock
            {
                Opacity = 0.78,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 2, 0, 0),
            };
            panel.Children.Add(detail);
            border = new Border
            {
                Child = panel,
                BorderBrush = new SolidColorBrush(Color.FromArgb(80, 120, 150, 180)),
                BorderThickness = column == 1 ? new Thickness(0) : new Thickness(1, 0, 0, 0),
            };
            Grid.SetColumn(border, column);
            parent.Children.Add(border);
            return value;
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
            var draftActions = new StackPanel
            {
                Orientation = Orientation.Horizontal,
            };
            draftActions.Children.Add(CreateSecondaryButton(
                "Open saved drafts folder", 190, OpenDraftsClicked));
            draftActions.Children.Add(CreateSecondaryButton(
                "Open submission form", 180, OpenSubmissionFormClicked));
            draftSharing.Children.Add(draftActions);
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
                Text = "As Driven never downloads or installs anything by itself. It can tell you that a newer dataset or plugin exists, and only when you press the button below: there is no timer, nothing at startup, and no request at all until an endpoint is set here. Installing an update stays a deliberate act, because a curated value changing under you mid-session is worse than a stale one you know about.",
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 12),
                MaxWidth = 860,
            });
            panel.Children.Add(new TextBlock
            {
                Text = "Update endpoint (https, blank for none)",
                FontWeight = FontWeights.SemiBold,
                Margin = new Thickness(0, 0, 0, 5),
            });
            _updateEndpoint = new TextBox
            {
                MinHeight = 30,
                MaxWidth = 640,
                HorizontalAlignment = HorizontalAlignment.Left,
                VerticalContentAlignment = VerticalAlignment.Center,
                Margin = new Thickness(0, 0, 0, 8),
                Text = _plugin.UpdateCheckUrl,
            };
            _updateEndpoint.LostFocus += UpdateEndpointChanged;
            panel.Children.Add(_updateEndpoint);
            _checkUpdatesButton = CreateSecondaryButton("Check for updates", 190, CheckUpdatesClicked);
            panel.Children.Add(_checkUpdatesButton);
            _updateStatus = new TextBlock
            {
                TextWrapping = TextWrapping.Wrap,
                Opacity = 0.82,
                MaxWidth = 860,
                Margin = new Thickness(0, 0, 0, 18),
                Text = "Not checked. As Driven has contacted nothing.",
            };
            panel.Children.Add(_updateStatus);

            AddSectionHeading(panel, "Supported simulators");
            panel.Children.Add(new TextBlock
            {
                Text = "As Driven only shows guidance for simulators covered by the installed dataset. In any other game the plugin stays quiet rather than guessing.",
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 10),
                MaxWidth = 760,
            });
            _supportedSimulators = new TextBlock
            {
                Name = "SupportedSimulatorsStatus",
                FontSize = 15,
                FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 24),
                MaxWidth = 760,
            };
            panel.Children.Add(_supportedSimulators);

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
            _recordStatus.Text = string.IsNullOrWhiteSpace(_plugin.CurrentRecordId)
                ? string.Empty
                : "Record: " + _plugin.CurrentRecordId;
            _errorStatus.Text = string.IsNullOrWhiteSpace(_plugin.CurrentRuntimeError)
                ? string.Empty
                : "Error: " + _plugin.CurrentRuntimeError;
            UpdateHealthStrip();
            UpdateGarageGuidance();
            UpdatePopupPreview();
            UpdatePreviewStatus();
            _verification.UpdateLiveAvailability();
        }

        private void UpdateHealthStrip()
        {
            GuidanceSnapshot guidance = _plugin.CurrentGuidance;
            string simulator = guidance == null ? string.Empty : guidance.SimulatorLabel;
            _healthSimulator.Text = string.IsNullOrWhiteSpace(simulator)
                ? "Waiting for simulator"
                : simulator;

            string status = _plugin.IsPreviewActive
                ? "Catalog preview"
                : _plugin.LiveMatchStatus;
            if (status == "matched")
            {
                _healthMatch.Text = "Exact match";
                _healthMatch.Foreground = Brushes.LightGreen;
            }
            else if (status == "Catalog preview")
            {
                _healthMatch.Text = status;
                _healthMatch.Foreground = new SolidColorBrush(Color.FromRgb(50, 190, 235));
            }
            else if (status == "unmatched")
            {
                _healthMatch.Text = "No exact match";
                _healthMatch.Foreground = Brushes.Goldenrod;
            }
            else if (status == "unsupported-game")
            {
                _healthMatch.Text = "Unsupported simulator";
                _healthMatch.Foreground = Brushes.Goldenrod;
            }
            else
            {
                _healthMatch.Text = "Waiting for car";
                _healthMatch.Foreground = Foreground;
            }

            _healthDataset.Text = EmptyAsUnknown(_plugin.CurrentDatasetVersion)
                + " / " + _plugin.DatabaseRecordCount + " cars";
            _healthPopup.Text = _plugin.CanShowPopup ? "Ready" : "Waiting for car";
            _healthPopup.Foreground = _plugin.CanShowPopup
                ? Brushes.LightGreen
                : Foreground;
        }

        private void UpdateGarageGuidance()
        {
            GuidanceSnapshot guidance = _plugin.CurrentGuidance;
            bool matched = guidance != null && guidance.HasMatch;
            string currentName = _plugin.CurrentCarName;
            _garageCarName.Text = string.IsNullOrWhiteSpace(currentName)
                ? "No car loaded"
                : currentName;
            _garageCarClass.Text = string.IsNullOrWhiteSpace(_plugin.CurrentCarClass)
                ? "Start a supported simulator or choose a catalog preview."
                : _plugin.CurrentCarClass;

            if (_plugin.IsPreviewActive)
            {
                _garageEyebrow.Text = "CATALOG PREVIEW - NOT LIVE";
            }
            else if (matched)
            {
                _garageEyebrow.Text = "LIVE EXACT MATCH";
            }
            else if (_plugin.LiveMatchStatus == "unmatched")
            {
                _garageEyebrow.Text = "LIVE CAR - NO EXACT RECORD";
            }
            else if (_plugin.LiveMatchStatus == "unsupported-game")
            {
                _garageEyebrow.Text = "UNSUPPORTED SIMULATOR";
            }
            else
            {
                _garageEyebrow.Text = "WAITING FOR TELEMETRY";
            }

            if (matched)
            {
                _garageWheel.Text = guidance.WheelRimLabel;
                _garageWheelDetail.Text = guidance.WheelFeatureLabel;
                _garageShifter.Text = guidance.ShifterLabel;
                _garageShifterDetail.Text = guidance.ShifterGateLabel;
                _garageLaunch.Text = guidance.LaunchLabel;
                _garageUpshift.Text = guidance.UpshiftLabel;
                _garageDownshift.Text = guidance.DownshiftLabel;
                _garageSummary.Text = guidance.DriverSummary;
                _garageSummary.Visibility = string.IsNullOrWhiteSpace(guidance.DriverSummary)
                    ? Visibility.Collapsed
                    : Visibility.Visible;
                _recordStatus.Text = string.IsNullOrWhiteSpace(guidance.RecordId)
                    ? string.Empty
                    : "Record: " + guidance.RecordId;
            }
            else
            {
                _garageWheel.Text = "Not available";
                _garageWheelDetail.Text = "No curated guidance loaded";
                _garageShifter.Text = "Not available";
                _garageShifterDetail.Text = "No curated guidance loaded";
                _garageLaunch.Text = "Not available";
                _garageUpshift.Text = "Not available";
                _garageDownshift.Text = "Not available";
                _garageSummary.Text = string.Empty;
                _garageSummary.Visibility = Visibility.Collapsed;
            }
        }

        private void UpdatePopupPreview()
        {
            if (_popupPreview == null || _popupSize == null || _popupTheme == null)
            {
                return;
            }
            GuidanceSnapshot guidance = _plugin.CurrentGuidance;
            string preference = SelectedPopupTheme();
            int year = guidance == null ? 0 : guidance.YearFrom;
            string resolved = PopupPreferences.ResolveTheme(preference, year);
            ThemePreviewPalette palette = PreviewPalette(resolved);
            ComboBoxItem selectedSize = _popupSize.SelectedItem as ComboBoxItem;
            bool compact = selectedSize != null
                && string.Equals(selectedSize.Tag as string, "compact", StringComparison.OrdinalIgnoreCase);
            _popupPreview.Background = palette.Card;
            _popupPreview.Width = compact ? 420 : 500;
            _popupPreview.Height = compact ? 291 : 297;
            _detailedPopupPreview.View.Visibility = compact
                ? Visibility.Collapsed
                : Visibility.Visible;
            _compactPopupPreview.View.Visibility = compact
                ? Visibility.Visible
                : Visibility.Collapsed;
            UpdatePopupPreviewVariant(_detailedPopupPreview, guidance, palette, resolved);
            UpdatePopupPreviewVariant(_compactPopupPreview, guidance, palette, resolved);
        }

        private void UpdatePopupPreviewVariant(
            PopupPreviewVariant variant,
            GuidanceSnapshot guidance,
            ThemePreviewPalette palette,
            string resolvedTheme)
        {
            bool matched = guidance != null && guidance.HasMatch;
            bool gplClassic = string.Equals(
                resolvedTheme, PopupPreferences.GPLClassicTheme,
                StringComparison.OrdinalIgnoreCase);
            UpdatePopupPreviewGeometry(variant);
            variant.Card.Background = palette.Card;
            variant.Card.BorderBrush = palette.Accent;
            string[] stripeNames = {
                "HeaderStripeDriver", "HeaderStripeAccent", "HeaderStripeCar"
            };
            Brush[] stripeBrushes = { palette.Driver, palette.Accent, palette.Car };
            for (int index = 0; index < stripeNames.Length; index++)
            {
                variant.Box[stripeNames[index]].Background = stripeBrushes[index];
                variant.Box[stripeNames[index]].Visibility = Visibility.Visible;
            }
            variant.Box["Badge"].Background = palette.PreviewFill;
            variant.Text["BadgeText"].Foreground = palette.PreviewText;
            variant.Text["Car"].Foreground = palette.Title;
            variant.Text["Class"].Foreground = palette.Muted;
            variant.Text["Car"].Text = matched
                ? _plugin.CurrentCarName
                : "Waiting for a matched car";
            variant.Text["Class"].Text = matched
                ? _plugin.CurrentCarClass
                : "No curated guidance loaded";

            variant.Box["HeaderRule"].Background = palette.Rule;
            variant.Box["FitPanel"].Background = palette.Panel;
            variant.Box["FitPanel"].BorderBrush = palette.Rule;
            variant.Box["FitRail"].Background = palette.FitRail;
            variant.Text["FitRail"].Foreground = palette.FitRailText;
            variant.Text["FitRail"].LayoutTransform = new RotateTransform(0);
            variant.Box["FitDivider"].Background = palette.Rule;
            foreach (Shape glyph in variant.Glyphs)
            {
                glyph.Stroke = palette.BandText;
            }
            variant.Text["Wheel"].Text = matched ? guidance.WheelRimLabel : "Not available";
            variant.Text["WheelDetail"].Text = matched ? guidance.WheelFeatureLabel : "No curated guidance";
            variant.Text["Shifter"].Text = matched ? guidance.ShifterLabel : "Not available";
            variant.Text["ShifterDetail"].Text = matched ? guidance.ShifterGateLabel : "No curated guidance";
            foreach (string name in new[] { "Wheel", "Shifter" })
            {
                variant.Text[name].Foreground = palette.BandText;
                variant.Text[name + "Detail"].Foreground = palette.BandMuted;
            }
            variant.Text["WheelMarker"].Text = matched
                ? MarkerText(guidance.WheelDiffers, guidance.WheelUnestablished)
                : string.Empty;
            variant.Text["ShifterMarker"].Text = matched
                ? MarkerText(guidance.ShifterDiffers, guidance.ShifterUnestablished)
                : string.Empty;
            ApplyMarkerTone(variant.Text["WheelMarker"], guidance == null || !guidance.WheelDiffers, palette);
            ApplyMarkerTone(variant.Text["ShifterMarker"], guidance == null || !guidance.ShifterDiffers, palette);

            variant.Box["UsePanel"].Background = palette.Panel;
            variant.Box["UsePanel"].BorderBrush = palette.Rule;
            string useTone = matched ? guidance.UseBandTone : "unknown";
            variant.Box["UseRail"].Background = gplClassic
                ? palette.CarRail
                : ToneBrush(useTone, palette, true);
            variant.Text["UseRail"].Foreground = palette.UseRailText;
            variant.Text["UseRail"].LayoutTransform = new RotateTransform(0);
            string[] moments = { "Launch", "Upshift", "Downshift" };
            string[] tones =
            {
                matched ? guidance.LaunchTone : "unknown",
                matched ? guidance.UpshiftTone : "unknown",
                matched ? guidance.DownshiftTone : "unknown",
            };
            string[] values =
            {
                matched ? guidance.LaunchLabel : "Not available",
                matched ? guidance.UpshiftLabel : "Not available",
                matched ? guidance.DownshiftLabel : "Not available",
            };
            string[] details =
            {
                matched ? guidance.LaunchDetailLabel : string.Empty,
                matched ? guidance.UpshiftClutchLabel : string.Empty,
                matched ? guidance.DownshiftClutchLabel : string.Empty,
            };
            bool[] differs =
            {
                matched && guidance.LaunchDiffers,
                matched && guidance.UpshiftDiffers,
                matched && guidance.DownshiftDiffers,
            };
            bool[] unestablished =
            {
                matched && guidance.LaunchUnestablished,
                matched && guidance.UpshiftUnestablished,
                matched && guidance.DownshiftUnestablished,
            };
            for (int index = 0; index < moments.Length; index++)
            {
                string moment = moments[index];
                variant.Box[moment + "Cell"].Background = ToneBrush(tones[index], palette, false);
                variant.Text[moment + "Head"].Foreground = ToneTextBrush(tones[index], palette);
                variant.Text[moment + "Value"].Text = values[index];
                variant.Text[moment + "Value"].Foreground = palette.BandText;
                variant.Text[moment + "Detail"].Text = details[index];
                variant.Text[moment + "Detail"].Foreground = palette.BandMuted;
                variant.Text[moment + "Marker"].Text = MarkerText(differs[index], unestablished[index]);
                ApplyMarkerTone(variant.Text[moment + "Marker"], !differs[index], palette);
                if (index > 0)
                {
                    variant.Box["UseDivider" + moment].Background = palette.Rule;
                }
            }

            string summary = matched ? guidance.DriverSummary : string.Empty;
            bool hasSummary = !string.IsNullOrWhiteSpace(summary);
            variant.Box["NotePanel"].Background = palette.Note;
            variant.Box["NotePanel"].Visibility = hasSummary ? Visibility.Visible : Visibility.Collapsed;
            variant.Box["NoteRail"].Background = palette.Accent;
            variant.Box["NoteRail"].Visibility = hasSummary ? Visibility.Visible : Visibility.Collapsed;
            variant.Box["NoteIconWell"].Background = Brushes.Transparent;
            variant.Box["NoteIconWell"].Visibility = hasSummary ? Visibility.Visible : Visibility.Collapsed;
            variant.Text["NoteIcon"].Foreground = Brushes.White;
            variant.Text["NoteIcon"].Visibility = hasSummary ? Visibility.Visible : Visibility.Collapsed;
            variant.Text["Summary"].Text = summary;
            variant.Text["Summary"].Foreground = palette.Text;
            variant.Text["Summary"].Visibility = hasSummary ? Visibility.Visible : Visibility.Collapsed;
            variant.Box["FooterRule"].Background = palette.Rule;
            string version = matched && !string.IsNullOrWhiteSpace(guidance.VerifiedGameVersion)
                ? guidance.VerifiedGameVersion
                : "unknown";
            string confidence = matched && !string.IsNullOrWhiteSpace(guidance.Confidence)
                ? guidance.Confidence
                : "Unknown";
            variant.Text["Evidence"].Text = matched
                ? guidance.SimulatorLabel + " " + version + (variant.Compact
                    ? " - " + confidence
                    : " - Confidence: " + confidence)
                : "Waiting for guidance";
            variant.Text["Dataset"].Text = "Dataset " + EmptyAsUnknown(_plugin.CurrentDatasetVersion);
            variant.Text["Evidence"].Foreground = palette.Muted;
            variant.Text["Dataset"].Foreground = palette.Muted;
        }

        private static void UpdatePopupPreviewGeometry(PopupPreviewVariant variant)
        {
            bool compact = variant.Compact;
            double cardWidth = compact ? 520 : 720;
            double left = compact ? 16 : 22;
            double contentWidth = cardWidth - left * 2;
            double railWidth = compact ? 44 : 56;
            double fitTop = compact ? 60 : 80;
            double fitHeight = compact ? 58 : 82;
            double fitIcon = compact ? 30 : 42;
            double fitHeadSize = compact ? 13 : 16;
            double fitSubSize = compact ? 10.5 : 12.5;
            double fitCellLeft = left + railWidth + 1;
            double fitCellWidth = (contentWidth - railWidth - 2) / 2;
            double iconTop = fitTop + (fitHeight - fitIcon) / 2;
            double fitTextLeft = fitCellLeft + fitIcon + 22;
            double secondTextLeft = fitCellLeft + fitCellWidth + fitIcon + 22;
            double fitTextWidth = fitCellWidth - fitIcon - 30;
            double fitHeadTop = compact
                ? fitTop + 7
                : fitTop + fitHeight / 2 - fitHeadSize - 3;
            double fitSubTop = compact ? fitTop + 26 : fitTop + fitHeight / 2 + 2;
            double fitMarkerTop = compact ? fitTop + 44 : fitTop + fitHeight - 21;

            variant.Box["FitPanel"].CornerRadius = new CornerRadius(0);
            Move(variant.Box["FitRail"], left + 1, fitTop + 1,
                railWidth, fitHeight - 2);
            Move(variant.WheelGlyph, fitCellLeft + 14, iconTop, fitIcon, fitIcon);
            Move(variant.ShiftGlyph, fitCellLeft + fitCellWidth + 14,
                iconTop, fitIcon, fitIcon);
            foreach (string name in new[] { "Wheel", "WheelDetail", "WheelMarker" })
            {
                double top = name == "Wheel"
                    ? fitHeadTop
                    : (name == "WheelDetail" ? fitSubTop : fitMarkerTop);
                double height = name == "Wheel"
                    ? fitHeadSize + 6
                    : (name == "WheelDetail" ? fitSubSize + 6 : fitSubSize + 4);
                Move(variant.Text[name], fitTextLeft, top, fitTextWidth, height);
            }
            foreach (string name in new[] { "Shifter", "ShifterDetail", "ShifterMarker" })
            {
                double top = name == "Shifter"
                    ? fitHeadTop
                    : (name == "ShifterDetail" ? fitSubTop : fitMarkerTop);
                double height = name == "Shifter"
                    ? fitHeadSize + 6
                    : (name == "ShifterDetail" ? fitSubSize + 6 : fitSubSize + 4);
                Move(variant.Text[name], secondTextLeft, top, fitTextWidth, height);
            }
            Move(variant.Box["FitDivider"], fitCellLeft + fitCellWidth,
                fitTop + 8, 1, fitHeight - 16);

            double useTop = compact ? 124 : 166;
            double useHeight = compact ? 78 : 92;
            double useHeadSize = compact ? 12 : 15;
            double useValueSize = compact ? 11 : 13;
            double useCellLeft = left + railWidth + 1;
            double useCellWidth = (contentWidth - railWidth - 2) / 3;
            variant.Box["UsePanel"].CornerRadius = new CornerRadius(0);
            Move(variant.Box["UseRail"], left + 1, useTop + 1,
                railWidth, useHeight - 2);
            string[] moments = { "Launch", "Upshift", "Downshift" };
            for (int index = 0; index < moments.Length; index++)
            {
                string moment = moments[index];
                double x = useCellLeft + useCellWidth * index;
                Move(variant.Box[moment + "Cell"], x + 1, useTop + 2,
                    useCellWidth - 2, useHeight - 4);
                if (index > 0)
                {
                    Move(variant.Box["UseDivider" + moment], x,
                        useTop + 8, 1, useHeight - 16);
                }
                Move(variant.Text[moment + "Head"], x + 14, useTop + 10,
                    useCellWidth - 24, useHeadSize + 6);
                Move(variant.Text[moment + "Value"], x + 14,
                    useTop + useHeadSize + 16, useCellWidth - 24,
                    useValueSize + 6);
                Move(variant.Text[moment + "Detail"], x + 14,
                    useTop + useHeadSize + useValueSize + 21,
                    useCellWidth - 24, useValueSize + 5);
                Move(variant.Text[moment + "Marker"], x + 14,
                    useTop + useHeadSize + useValueSize * 2 + 25,
                    useCellWidth - 24, useValueSize + 2);
            }

            double noteTop = compact ? 206 : 264;
            double noteHeight = compact ? 89 : 99;
            double noteRailWidth = railWidth;
            variant.Box["NotePanel"].CornerRadius = new CornerRadius(0);
            Move(variant.Box["NoteRail"], left, noteTop,
                noteRailWidth, noteHeight);
            Move(variant.Box["NoteIconWell"], left,
                noteTop, noteRailWidth, noteHeight);
            double summaryLeft = left + noteRailWidth + 12;
            Move(variant.Text["Summary"], summaryLeft, noteTop + 7,
                contentWidth - (summaryLeft - left) - 12,
                noteHeight - 14);
        }

        private static string MarkerText(bool differs, bool unestablished)
        {
            if (differs) { return "* not as the real car"; }
            if (unestablished) { return "* real car not established"; }
            return string.Empty;
        }

        private static void ApplyMarkerTone(
            TextBlock marker, bool muted, ThemePreviewPalette palette)
        {
            marker.Foreground = muted ? palette.BandMuted : palette.Accent;
        }

        private static Brush ToneBrush(
            string tone, ThemePreviewPalette palette, bool rail)
        {
            if (tone == PreflightLabels.ToneDriver) { return rail ? palette.DriverRail : palette.DriverCell; }
            if (tone == PreflightLabels.ToneCar) { return rail ? palette.CarRail : palette.CarCell; }
            return rail ? palette.FitRail : Brushes.Transparent;
        }

        private static Brush ToneTextBrush(string tone, ThemePreviewPalette palette)
        {
            if (tone == PreflightLabels.ToneDriver) { return palette.Driver; }
            if (tone == PreflightLabels.ToneCar) { return palette.Car; }
            if (tone == PreflightLabels.ToneOptional) { return palette.BandText; }
            return palette.Muted;
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
            CarCatalogEntry prior = _previewCar.SelectedItem as CarCatalogEntry;
            string selectedRecord = prior == null ? _plugin.CurrentRecordId : prior.RecordId;
            string selectedSimulator = prior == null ? string.Empty : prior.Simulator;
            string simulatorFilter = CatalogFilterValue(_catalogSimulator);
            string decadeFilter = CatalogFilterValue(_catalogDecade);
            string wheelFilter = CatalogFilterValue(_catalogWheel);
            string shifterFilter = CatalogFilterValue(_catalogShifter);
            var simulators = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            var decades = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            var wheels = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            var shifters = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (CarCatalogEntry car in _plugin.PreviewCars)
            {
                GuidanceSnapshot guidance = _plugin.ReadCatalogGuidance(car);
                if (!guidance.HasMatch)
                {
                    continue;
                }
                simulators[car.Simulator] = guidance.SimulatorLabel;
                string decade = CatalogDecade(guidance.YearFrom);
                decades[decade] = decade == "unknown" ? "Year unknown" : decade + "s";
                wheels[guidance.WheelRimShape] = guidance.WheelRimLabel;
                shifters[guidance.ShiftActuation] = CatalogShifterLabel(guidance.ShiftActuation);
            }

            _loadingCatalogFilters = true;
            PopulateCatalogFilter(_catalogSimulator, "All simulators", simulators, simulatorFilter);
            PopulateCatalogFilter(_catalogDecade, "All decades", decades, decadeFilter);
            PopulateCatalogFilter(_catalogWheel, "All wheels", wheels, wheelFilter);
            PopulateCatalogFilter(_catalogShifter, "All shifters", shifters, shifterFilter);
            _loadingCatalogFilters = false;
            ApplyCatalogFilters(selectedSimulator, selectedRecord);
        }

        private void CatalogFilterChanged(object sender, RoutedEventArgs eventArgs)
        {
            if (!_loadingCatalogFilters && _previewCar != null)
            {
                CarCatalogEntry selected = _previewCar.SelectedItem as CarCatalogEntry;
                ApplyCatalogFilters(
                    selected == null ? string.Empty : selected.Simulator,
                    selected == null ? string.Empty : selected.RecordId);
            }
        }

        private void ApplyCatalogFilters(string selectedSimulator, string selectedRecord)
        {
            string search = (_catalogSearch == null ? string.Empty : _catalogSearch.Text).Trim();
            string simulator = CatalogFilterValue(_catalogSimulator);
            string decade = CatalogFilterValue(_catalogDecade);
            string wheel = CatalogFilterValue(_catalogWheel);
            string shifter = CatalogFilterValue(_catalogShifter);
            _previewCar.Items.Clear();
            CarCatalogEntry selected = null;
            foreach (CarCatalogEntry car in _plugin.PreviewCars)
            {
                GuidanceSnapshot guidance = _plugin.ReadCatalogGuidance(car);
                if (!guidance.HasMatch
                    || (simulator.Length > 0 && car.Simulator != simulator)
                    || (decade.Length > 0 && CatalogDecade(guidance.YearFrom) != decade)
                    || (wheel.Length > 0 && guidance.WheelRimShape != wheel)
                    || (shifter.Length > 0 && guidance.ShiftActuation != shifter)
                    || (search.Length > 0
                        && car.DisplayLabel.IndexOf(search, StringComparison.OrdinalIgnoreCase) < 0
                        && car.RecordId.IndexOf(search, StringComparison.OrdinalIgnoreCase) < 0))
                {
                    continue;
                }
                _previewCar.Items.Add(car);
                if (car.RecordId == selectedRecord
                    && (selectedSimulator.Length == 0 || car.Simulator == selectedSimulator))
                {
                    selected = car;
                }
            }
            _catalogCount.Text = _previewCar.Items.Count == 1
                ? "1 curated car"
                : _previewCar.Items.Count + " curated cars";
            _previewCar.SelectedItem = selected;
            if (_previewCar.SelectedItem == null && _previewCar.Items.Count > 0)
            {
                _previewCar.SelectedIndex = 0;
            }
            if (_previewCar.Items.Count == 0)
            {
                UpdateCatalogDetail(null);
            }
        }

        private void CatalogSelectionChanged(object sender, SelectionChangedEventArgs eventArgs)
        {
            UpdateCatalogDetail(_previewCar.SelectedItem as CarCatalogEntry);
        }

        private void UpdateCatalogDetail(CarCatalogEntry car)
        {
            GuidanceSnapshot guidance = _plugin.ReadCatalogGuidance(car);
            bool available = car != null && guidance.HasMatch;
            int year = available ? guidance.YearFrom : 0;
            string resolvedTheme = PopupPreferences.ResolveTheme(
                _plugin.PopupThemePreference, year);
            ThemePreviewPalette palette = PreviewPalette(resolvedTheme);
            _catalogDetailName.Text = available ? guidance.DisplayName : "No matching cars";
            _catalogDetailClass.Text = available
                ? guidance.SimulatorLabel + (string.IsNullOrWhiteSpace(guidance.CarClass) ? string.Empty : " | " + guidance.CarClass)
                : "Change or clear a filter to continue.";
            _catalogWheelValue.Text = available ? guidance.WheelRimLabel : "-";
            _catalogWheelDetail.Text = available ? guidance.WheelFeatureLabel : string.Empty;
            _catalogShifterValue.Text = available ? guidance.ShifterLabel : "-";
            _catalogShifterDetail.Text = available ? guidance.ShifterGateLabel : string.Empty;
            _catalogLaunch.Text = available ? guidance.LaunchLabel : "-";
            _catalogLaunchDetail.Text = available ? guidance.LaunchDetailLabel : string.Empty;
            _catalogUpshift.Text = available ? guidance.UpshiftLabel : "-";
            _catalogUpshiftDetail.Text = available ? guidance.UpshiftClutchLabel : string.Empty;
            _catalogDownshift.Text = available ? guidance.DownshiftLabel : "-";
            _catalogDownshiftDetail.Text = available ? guidance.DownshiftClutchLabel : string.Empty;
            _catalogSummary.Text = available
                ? (string.IsNullOrWhiteSpace(guidance.DriverSummary)
                    ? "No driver summary note is recorded for this car."
                    : "ⓘ  " + guidance.DriverSummary)
                : string.Empty;

            _catalogFitPanel.Background = palette.Panel;
            _catalogFitPanel.BorderBrush = palette.Rule;
            _catalogFitRail.Background = palette.FitRail;
            _catalogFitRailText.Foreground = palette.FitRailText;
            // The accent is intentionally dark blue in the 1990s palette and
            // disappears against that palette's blue FIT panel. These are band
            // labels, so use the same high-contrast text colour as the popup's
            // wheel and shifter values.
            _catalogWheelHeading.Foreground = palette.BandText;
            _catalogShifterHeading.Foreground = palette.BandText;
            foreach (TextBlock value in new[] { _catalogWheelValue, _catalogShifterValue })
            {
                value.Foreground = palette.BandText;
            }
            foreach (TextBlock detail in new[] { _catalogWheelDetail, _catalogShifterDetail })
            {
                detail.Foreground = palette.BandMuted;
            }

            _catalogUsePanel.Background = palette.Panel;
            _catalogUsePanel.BorderBrush = palette.Rule;
            string useTone = available ? guidance.UseBandTone : "unknown";
            _catalogUseRail.Background = ToneBrush(useTone, palette, true);
            _catalogUseRailText.Foreground = palette.UseRailText;
            string[] tones =
            {
                available ? guidance.LaunchTone : "unknown",
                available ? guidance.UpshiftTone : "unknown",
                available ? guidance.DownshiftTone : "unknown",
            };
            TextBlock[] headings =
            {
                _catalogLaunchHeading, _catalogUpshiftHeading, _catalogDownshiftHeading,
            };
            TextBlock[] values =
            {
                _catalogLaunch, _catalogUpshift, _catalogDownshift,
            };
            TextBlock[] details =
            {
                _catalogLaunchDetail, _catalogUpshiftDetail, _catalogDownshiftDetail,
            };
            Border[] cells =
            {
                _catalogLaunchCell, _catalogUpshiftCell, _catalogDownshiftCell,
            };
            for (int index = 0; index < tones.Length; index++)
            {
                headings[index].Foreground = ToneTextBrush(tones[index], palette);
                values[index].Foreground = palette.BandText;
                details[index].Foreground = palette.BandMuted;
                cells[index].Background = ToneBrush(tones[index], palette, false);
                cells[index].BorderBrush = palette.Rule;
            }
        }

        private static string CatalogDecade(int year)
        {
            return year <= 0
                ? "unknown"
                : (year / 10 * 10).ToString(CultureInfo.InvariantCulture);
        }

        private static string CatalogShifterLabel(string value)
        {
            switch (value)
            {
                case "h-pattern": return "H-pattern";
                case "sequential-paddles": return "Paddles";
                case "sequential-stick": return "Sequential stick";
                case "automatic-lever": return "Automatic lever";
                case "direct-selection": return "Direct selection";
                default: return "Unknown shifter";
            }
        }

        private static string CatalogFilterValue(ComboBox filter)
        {
            ComboBoxItem item = filter == null ? null : filter.SelectedItem as ComboBoxItem;
            return item == null ? string.Empty : item.Tag as string ?? string.Empty;
        }

        private static void PopulateCatalogFilter(
            ComboBox filter,
            string allLabel,
            Dictionary<string, string> options,
            string selectedValue)
        {
            filter.Items.Clear();
            filter.Items.Add(CreateChoiceItem(allLabel, string.Empty));
            var entries = new List<KeyValuePair<string, string>>(options);
            entries.Sort(delegate(KeyValuePair<string, string> left, KeyValuePair<string, string> right)
            {
                return string.Compare(left.Value, right.Value, StringComparison.OrdinalIgnoreCase);
            });
            foreach (KeyValuePair<string, string> option in entries)
            {
                filter.Items.Add(CreateChoiceItem(option.Value, option.Key));
            }
            SelectChoice(filter, selectedValue, 0);
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

        private static ComboBoxItem CreateChoiceItem(string label, string value)
        {
            return new ComboBoxItem
            {
                Content = label,
                Tag = value,
            };
        }

        private static void SelectChoice(ComboBox comboBox, string value, int fallbackIndex)
        {
            foreach (object item in comboBox.Items)
            {
                ComboBoxItem sizeItem = item as ComboBoxItem;
                if (sizeItem != null && string.Equals(sizeItem.Tag as string, value, StringComparison.OrdinalIgnoreCase))
                {
                    comboBox.SelectedItem = sizeItem;
                    return;
                }
            }
            comboBox.SelectedIndex = fallbackIndex;
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
            UpdatePopupPreview();
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
            string popupTheme = SelectedPopupTheme();
            _plugin.SetPopupSettings(seconds, popupSize, popupTheme);
            _popupSettingsDirty = false;
            UpdatePopupSettingsState();
            SetOverlayFeedback(
                "Saved. New car changes use the " + popupSize + " popup with "
                    + popupTheme + " theme selection for " + seconds + " seconds.",
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

        private void OpenSubmissionFormClicked(object sender, RoutedEventArgs eventArgs)
        {
            try
            {
                _plugin.OpenObservationSubmissionForm();
                SetFeedback(
                    _contributionFeedback,
                    "Opened the public simulator-observation form. Choose a saved draft JSON to attach; nothing was uploaded automatically.",
                    Brushes.LightGreen);
            }
            catch (Exception exception)
            {
                SetFeedback(
                    _contributionFeedback,
                    "Could not open the submission form: " + exception.Message,
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

        private void UpdateEndpointChanged(object sender, RoutedEventArgs eventArgs)
        {
            _plugin.UpdateCheckUrl = _updateEndpoint.Text;
        }

        private void CheckUpdatesClicked(object sender, RoutedEventArgs eventArgs)
        {
            string endpoint = _updateEndpoint == null ? string.Empty : _updateEndpoint.Text;
            string dataset = _plugin.CurrentDatasetVersion;
            string plugin = _plugin.PluginVersion;
            _checkUpdatesButton.IsEnabled = false;
            _updateStatus.Text = "Checking...";
            // Off the UI thread: a slow or unreachable endpoint would otherwise
            // freeze SimHub's settings window for the whole timeout.
            var worker = new System.Threading.Thread(delegate()
            {
                UpdateAvailability result = UpdateCheck.Fetch(endpoint, dataset, plugin);
                Dispatcher.BeginInvoke(new Action(delegate()
                {
                    _updateStatus.Text = result.Summary(dataset, plugin);
                    _checkUpdatesButton.IsEnabled = true;
                }));
            });
            worker.IsBackground = true;
            worker.Start();
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
