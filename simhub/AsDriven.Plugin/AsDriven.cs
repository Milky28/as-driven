using System;
using System.Collections.ObjectModel;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using AsDriven.Core;
using GameReaderCommon;
using SimHub.Plugins;
using SimHub.Plugins.OutputPlugins.GraphicalDash;
using SimHub.Plugins.OutputPlugins.GraphicalDash.Overlays;

namespace AsDriven.Plugin
{
    [PluginDescription("Shows the authentic physical controls and shifting technique for the current car.")]
    [PluginAuthor("Jason Kinslow")]
    [PluginName("As Driven")]
    public sealed class AsDriven : IPlugin, IDataPlugin, IWPFSettings, IWPFSettingsV2
    {
        internal const double DefaultPopupDurationSeconds =
            PopupPreferences.DefaultDurationSeconds;
        internal const double MinimumPopupDurationSeconds =
            PopupPreferences.MinimumDurationSeconds;
        internal const double MaximumPopupDurationSeconds =
            PopupPreferences.MaximumDurationSeconds;
        internal const string DefaultPopupSize = PopupPreferences.DefaultSize;
        private const int ProcessQueryLimitedInformation = 0x1000;
        private static readonly System.Drawing.Bitmap MenuIcon =
            AsDrivenMenuIcon.Create();
        private static readonly System.Drawing.Bitmap HeaderIcon =
            AsDrivenMenuIcon.CreateHeader();

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr OpenProcess(
            int desiredAccess,
            bool inheritHandle,
            int processId);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool QueryFullProcessImageName(
            IntPtr processHandle,
            int flags,
            StringBuilder executablePath,
            ref int size);

        [DllImport("kernel32.dll")]
        private static extern bool CloseHandle(IntPtr handle);

        private GuidanceSnapshot _current = GuidanceSnapshot.Empty(
            "not-initialized", string.Empty, string.Empty, string.Empty);
        private readonly PopupState _popupState = new PopupState(
            TimeSpan.FromSeconds(DefaultPopupDurationSeconds));
        private readonly object _verificationTelemetryLock = new object();
        private readonly GuidedVerificationDrive _guidedVerificationDrive =
            new GuidedVerificationDrive();
        private volatile GuidedDriveSnapshot _guidedDriveSnapshot;
        private AsDrivenSettings _settings = new AsDrivenSettings();
        private AsDrivenDatabase _database;
        private SessionState _session;
        private bool _previewActive;
        private string _previewLiveCarIdentifier = string.Empty;
        private OverlayLayoutManager _previewOverlayManager;
        private string _previewOverlaySize = string.Empty;
        private UnmatchedIdentityLog _unmatchedLog;
        private string _databasePath = string.Empty;
        private string _unmatchedLogPath = string.Empty;
        private string _lastUnmatchedCarModel = string.Empty;
        private string _lastUnmatchedCarId = string.Empty;
        private string _lastUnmatchedCarClass = string.Empty;
        private string _lastUnmatchedGameVersion = string.Empty;
        private string _detectedVersionGame = string.Empty;
        private string _detectedGameVersion = string.Empty;
        private string _simHubVersion = string.Empty;
        private string _lastRuntimeError = string.Empty;
        private string _lastUnmatchedLogError = string.Empty;
        private int _databaseRecordCount;
        private VerificationCaptureContext _liveVerificationContext;
        private VerificationCaptureContext _guidedVerificationCapture;

        public AsDriven()
        {
            RefreshGuidedDriveSnapshot();
        }

        public PluginManager PluginManager { get; set; }

        public ImageSource PictureIcon { get { return this.ToIcon(MenuIcon); } }

        internal ImageSource HeaderPictureIcon
        {
            get { return this.ToIcon(HeaderIcon); }
        }

        public string LeftMenuTitle { get { return "As Driven"; } }

        internal double PopupDurationSeconds
        {
            get { return _popupState.AutomaticDurationSeconds; }
        }

        internal string PopupSize
        {
            get { return NormalizePopupSize(_settings.PopupSize); }
        }

        internal string UnmatchedLogPath
        {
            get { return _unmatchedLogPath; }
        }

        internal string PluginVersion
        {
            get
            {
                Version version = GetType().Assembly.GetName().Version;
                return version == null
                    ? "unknown"
                    : version.Major + "." + version.Minor + "." + version.Build;
            }
        }

        internal string CurrentMatchStatus
        {
            get { return _current == null ? "not-initialized" : _current.MatchStatus; }
        }

        internal string CurrentCarName
        {
            get
            {
                if (_current == null)
                {
                    return string.Empty;
                }
                return !string.IsNullOrWhiteSpace(_current.DisplayName)
                    ? _current.DisplayName
                    : _current.RawCarIdentifier;
            }
        }

        internal string CurrentCarClass
        {
            get { return _current == null ? string.Empty : _current.CarClass; }
        }

        internal string CurrentRecordId
        {
            get { return _current == null ? string.Empty : _current.RecordId; }
        }

        internal string CurrentDatasetVersion
        {
            get { return DatasetVersion(); }
        }

        internal int DatabaseRecordCount
        {
            get { return _databaseRecordCount; }
        }

        /// <summary>
        /// The simulators the installed dataset covers, so the settings page can
        /// answer "will this work in my game?" before the game is started.
        /// </summary>
        internal SimulatorCoverage[] SupportedSimulators
        {
            get
            {
                return _database == null
                    ? new SimulatorCoverage[0]
                    : _database.Simulators;
            }
        }

        internal bool CanShowPopup
        {
            get
            {
                string status = LiveMatchStatus;
                return _previewActive
                    || (status != "no-data"
                        && status != "no-car"
                        && status != "game-not-running"
                        && status != "not-initialized");
            }
        }

        internal string CurrentRuntimeError
        {
            get { return _lastRuntimeError; }
        }

        internal string LiveMatchStatus
        {
            get
            {
                return _session == null || _session.Current == null
                    ? "no-data"
                    : _session.Current.MatchStatus;
            }
        }

        internal string LiveCarName
        {
            get
            {
                GuidanceSnapshot live = _session == null ? null : _session.Current;
                if (live == null)
                {
                    return string.Empty;
                }
                return !string.IsNullOrWhiteSpace(live.DisplayName)
                    ? live.DisplayName
                    : live.RawCarIdentifier;
            }
        }

        internal string LiveCarClass
        {
            get
            {
                return _session == null || _session.Current == null
                    ? string.Empty
                    : _session.Current.CarClass;
            }
        }

        internal string LiveRecordId
        {
            get
            {
                return _session == null || _session.Current == null
                    ? string.Empty
                    : _session.Current.RecordId;
            }
        }

        internal CarCatalogEntry[] PreviewCars
        {
            get { return _database == null ? new CarCatalogEntry[0] : _database.Cars; }
        }

        internal bool IsPreviewActive
        {
            get { return _previewActive; }
        }

        internal string VerificationObserver
        {
            get { return _settings.VerificationObserver ?? string.Empty; }
        }

        internal string VerificationDraftDirectory
        {
            get { return ResolveVerificationDraftDirectory(); }
        }

        public void Init(PluginManager pluginManager)
        {
            PluginManager = pluginManager;
            LoadSettings();
            InitializeUnmatchedLog();
            AttachProperties();
            this.AddAction(
                "RefreshDatabase",
                delegate(PluginManager manager, string parameter) { LoadDatabase(); });
            this.AddAction(
                "ShowPopup",
                delegate(PluginManager manager, string parameter) { ShowPopup(); });
            this.AddAction(
                "HidePopup",
                delegate(PluginManager manager, string parameter) { HidePopup(); });
            this.AddAction(
                "TogglePopup",
                delegate(PluginManager manager, string parameter)
                {
                    TogglePopup();
                });
            this.AddAction(
                "OpenDiagnosticsFolder",
                delegate(PluginManager manager, string parameter)
                {
                    OpenDiagnosticsFolder();
                });
            this.AddAction(
                "ReturnToLiveCar",
                delegate(PluginManager manager, string parameter)
                {
                    ReturnToLiveCar();
                });
            this.AddAction(
                "OpenVerificationFolder",
                delegate(PluginManager manager, string parameter)
                {
                    OpenVerificationFolder();
                });
            this.AddAction(
                "VerificationDriveNext",
                delegate(PluginManager manager, string parameter)
                {
                    GuidedVerificationNext();
                });
            this.AddAction(
                "VerificationDriveRetry",
                delegate(PluginManager manager, string parameter)
                {
                    GuidedVerificationRetry();
                });
            this.AddAction(
                "VerificationDriveSkip",
                delegate(PluginManager manager, string parameter)
                {
                    GuidedVerificationSkip();
                });
            this.AddAction(
                "VerificationDriveCancel",
                delegate(PluginManager manager, string parameter)
                {
                    GuidedVerificationCancel();
                });
            LoadDatabase();
        }

        public Control GetWPFSettingsControl(PluginManager pluginManager)
        {
            return new AsDrivenSettingsControl(this);
        }

        public void DataUpdate(PluginManager pluginManager, ref GameData data)
        {
            try
            {
                UpdateLiveVerificationTelemetry(data);
                SessionState session = _session;
                if (session == null)
                {
                    return;
                }

                string carIdentifier = data.NewData == null
                    ? string.Empty
                    : data.NewData.CarModel ?? string.Empty;
                bool leavingPreview = ShouldLeavePreview(
                    _previewActive,
                    data.GameRunning,
                    _previewLiveCarIdentifier,
                    carIdentifier);
                if (_previewActive && !data.GameRunning)
                {
                    return;
                }
                if (_previewActive && !leavingPreview)
                {
                    session.Update(
                        data.GameRunning,
                        data.GameName ?? string.Empty,
                        carIdentifier);
                    return;
                }
                if (leavingPreview)
                {
                    _previewActive = false;
                    _previewLiveCarIdentifier = string.Empty;
                    StopPreviewOverlay();
                    _current = session.Current;
                    _popupState.OnIdentityChanged(
                        true,
                        carIdentifier,
                        DateTime.UtcNow);
                }
                if (session.Update(
                    data.GameRunning,
                    data.GameName ?? string.Empty,
                    carIdentifier))
                {
                    _current = session.Current;
                    if (_current.MatchStatus == "unmatched")
                    {
                        RecordUnmatchedIdentity(data);
                    }
                    _popupState.OnIdentityChanged(
                        data.GameRunning,
                        carIdentifier,
                        DateTime.UtcNow);
                }
                if (!data.GameRunning)
                {
                    _detectedVersionGame = string.Empty;
                    _detectedGameVersion = string.Empty;
                }
            }
            catch (Exception exception)
            {
                string message = exception.GetType().Name + ": " + exception.Message;
                _current = GuidanceSnapshot.Empty(
                    "runtime-error", data.GameName, string.Empty, DatasetVersion());
                _popupState.Hide();
                if (_lastRuntimeError != message)
                {
                    _lastRuntimeError = message;
                    SimHub.Logging.Current.Error(
                        "As Driven DataUpdate failed: " + message);
                }
            }
        }

        public void End(PluginManager pluginManager)
        {
            _previewActive = false;
            _previewLiveCarIdentifier = string.Empty;
            StopPreviewOverlay();
            _popupState.Hide();
            _guidedVerificationDrive.Cancel();
            RefreshGuidedDriveSnapshot();
        }

        private void LoadDatabase()
        {
            try
            {
                string path = ResolveDatabasePath();
                AsDrivenDatabase database = AsDrivenDatabase.Load(path);
                _database = database;
                _databasePath = database.DataDirectory;
                _databaseRecordCount = database.RecordCount;
                _session = new SessionState(database);
                _previewActive = false;
                _previewLiveCarIdentifier = string.Empty;
                StopPreviewOverlay();
                _current = _session.Current;
                _lastRuntimeError = string.Empty;
                SimHub.Logging.Current.Info(
                    "As Driven loaded dataset " + database.DatasetVersion
                    + " with " + database.RecordCount + " records from " + path);
            }
            catch (Exception exception)
            {
                _session = null;
                _database = null;
                _previewActive = false;
                _previewLiveCarIdentifier = string.Empty;
                StopPreviewOverlay();
                _databaseRecordCount = 0;
                _current = GuidanceSnapshot.Empty(
                    "database-error", string.Empty, string.Empty, string.Empty);
                _databasePath = ResolveDatabasePath();
                _lastRuntimeError = exception.GetType().Name + ": " + exception.Message;
                SimHub.Logging.Current.Error(
                    "As Driven could not load its database from "
                    + _databasePath + ": " + exception.Message);
            }
        }

        private void LoadSettings()
        {
            try
            {
                _settings = this.ReadCommonSettings<AsDrivenSettings>(
                    "Settings",
                    delegate { return new AsDrivenSettings(); });
                double seconds = NormalizePopupDuration(
                    _settings.PopupDurationSeconds);
                _settings.PopupDurationSeconds = seconds;
                _settings.PopupSize = NormalizePopupSize(_settings.PopupSize);
                if (_settings.VerificationAssistProfiles == null)
                {
                    _settings.VerificationAssistProfiles =
                        new Dictionary<string, VerificationAssistProfile>();
                }
                _popupState.SetAutomaticDuration(TimeSpan.FromSeconds(seconds));
            }
            catch (Exception exception)
            {
                _settings = new AsDrivenSettings();
                _popupState.SetAutomaticDuration(
                    TimeSpan.FromSeconds(DefaultPopupDurationSeconds));
                SimHub.Logging.Current.Error(
                    "As Driven could not load settings: " + exception.Message);
            }
        }

        internal void SetPopupSettings(double seconds, string popupSize)
        {
            seconds = NormalizePopupDuration(seconds);
            string normalizedPopupSize = NormalizePopupSize(popupSize);
            bool previewSizeChanged = _previewActive
                && !string.Equals(
                    PopupSize,
                    normalizedPopupSize,
                    StringComparison.OrdinalIgnoreCase);
            _settings.PopupDurationSeconds = seconds;
            _settings.PopupSize = normalizedPopupSize;
            _popupState.SetAutomaticDuration(TimeSpan.FromSeconds(seconds));
            this.SaveCommonSettings("Settings", _settings);
            if (previewSizeChanged)
            {
                StopPreviewOverlay();
                StartPreviewOverlay();
            }
        }

        internal bool ShowPopup()
        {
            if (!CanShowPopup)
            {
                return false;
            }
            _popupState.Show();
            if (_previewActive)
            {
                StartPreviewOverlay();
            }
            return true;
        }

        internal void HidePopup()
        {
            _popupState.Hide();
        }

        internal bool TogglePopup()
        {
            if (_popupState.IsVisible(DateTime.UtcNow))
            {
                HidePopup();
                return false;
            }
            return ShowPopup();
        }

        internal void RefreshDatabase()
        {
            LoadDatabase();
        }

        internal VerificationCaptureContext CaptureVerificationContext()
        {
            lock (_verificationTelemetryLock)
            {
                if (_liveVerificationContext == null
                    || string.IsNullOrWhiteSpace(_liveVerificationContext.TelemetryName))
                {
                    return null;
                }
                return _liveVerificationContext.WithObservedAt(DateTime.UtcNow);
            }
        }

        internal VerificationAssistProfile GetVerificationAssistProfile(string simulator)
        {
            VerificationAssistProfile profile;
            if (_settings.VerificationAssistProfiles != null
                && _settings.VerificationAssistProfiles.TryGetValue(
                    simulator ?? string.Empty,
                    out profile))
            {
                return profile;
            }
            return null;
        }

        internal void SaveVerificationAssistProfile(
            string simulator,
            string automaticClutch,
            string automaticShifting,
            string automaticThrottleBlip)
        {
            if (_settings.VerificationAssistProfiles == null)
            {
                _settings.VerificationAssistProfiles =
                    new Dictionary<string, VerificationAssistProfile>();
            }
            _settings.VerificationAssistProfiles[simulator ?? string.Empty] =
                new VerificationAssistProfile
                {
                    AutomaticClutch = automaticClutch ?? "unknown",
                    AutomaticShifting = automaticShifting ?? "unknown",
                    AutomaticThrottleBlip = automaticThrottleBlip ?? "unknown",
                    Confirmed = true
                };
            this.SaveCommonSettings("Settings", _settings);
        }

        internal void StartGuidedVerificationDrive(VerificationCaptureContext capture)
        {
            if (capture == null)
            {
                throw new ArgumentNullException("capture");
            }
            _guidedVerificationCapture = capture;
            _popupState.Hide();
            _guidedVerificationDrive.Start(capture.SuggestedForwardGears);
            RefreshGuidedDriveSnapshot();
        }

        internal GuidedDriveSnapshot GetGuidedDriveSnapshot()
        {
            return _guidedDriveSnapshot;
        }

        internal GuidedDriveResults GetGuidedDriveResults()
        {
            return _guidedVerificationDrive.GetResults();
        }

        internal VerificationCaptureContext GetGuidedVerificationCapture()
        {
            return _guidedVerificationCapture;
        }

        internal void GuidedVerificationNext()
        {
            _guidedVerificationDrive.Next();
            RefreshGuidedDriveSnapshot();
        }

        internal void GuidedVerificationRetry()
        {
            _guidedVerificationDrive.Retry();
            RefreshGuidedDriveSnapshot();
        }

        internal void GuidedVerificationSkip()
        {
            _guidedVerificationDrive.Skip();
            RefreshGuidedDriveSnapshot();
        }

        internal void GuidedVerificationCancel()
        {
            bool completed = _guidedDriveSnapshot != null && _guidedDriveSnapshot.Completed;
            _guidedVerificationDrive.Cancel();
            RefreshGuidedDriveSnapshot();
            if (!completed)
            {
                _guidedVerificationCapture = null;
            }
        }

        internal string SaveVerificationDraft(
            VerificationObservationDraft draft,
            string observer)
        {
            if (draft == null)
            {
                throw new ArgumentNullException("draft");
            }
            draft.Observer = (observer ?? string.Empty).Trim();
            if (!string.IsNullOrWhiteSpace(draft.Observer)
                && !string.Equals(
                    _settings.VerificationObserver,
                    draft.Observer,
                    StringComparison.Ordinal))
            {
                _settings.VerificationObserver = draft.Observer;
                this.SaveCommonSettings("Settings", _settings);
            }
            return VerificationObservationWriter.WriteDraft(
                ResolveVerificationDraftDirectory(),
                draft);
        }

        internal string OpenVerificationFolder()
        {
            string directory = ResolveVerificationDraftDirectory();
            Directory.CreateDirectory(directory);
            Process.Start("explorer.exe", "\"" + directory + "\"");
            return directory;
        }

        internal bool PreviewCar(CarCatalogEntry car)
        {
            if (_database == null || car == null)
            {
                return false;
            }
            GuidanceSnapshot preview = _database.Preview(car.Simulator, car.RecordId);
            if (!preview.HasMatch)
            {
                return false;
            }
            _current = preview;
            _previewActive = true;
            VerificationCaptureContext live = CaptureVerificationContext();
            _previewLiveCarIdentifier = live == null
                ? string.Empty
                : live.TelemetryName ?? string.Empty;
            _popupState.Show();
            if (StartPreviewOverlay())
            {
                return true;
            }
            _previewActive = false;
            _previewLiveCarIdentifier = string.Empty;
            _current = _session == null ? preview : _session.Current;
            _popupState.Hide();
            return false;
        }

        internal static bool ShouldLeavePreview(
            bool previewActive,
            bool gameRunning,
            string previewLiveCarIdentifier,
            string currentLiveCarIdentifier)
        {
            return PreviewRules.ShouldLeavePreview(
                previewActive,
                gameRunning,
                previewLiveCarIdentifier,
                currentLiveCarIdentifier);
        }

        internal void ReturnToLiveCar()
        {
            _previewActive = false;
            _previewLiveCarIdentifier = string.Empty;
            StopPreviewOverlay();
            _current = _session == null
                ? GuidanceSnapshot.Empty(
                    "no-data", string.Empty, string.Empty, string.Empty)
                : _session.Current;
            if (_current.HasMatch)
            {
                _popupState.Show();
            }
            else
            {
                _popupState.Hide();
            }
        }

        private bool StartPreviewOverlay()
        {
            try
            {
                Application application = Application.Current;
                if (application != null && !application.Dispatcher.CheckAccess())
                {
                    return (bool)application.Dispatcher.Invoke(
                        new Func<bool>(StartPreviewOverlay));
                }

                if (_previewOverlayManager != null
                    && string.Equals(
                        _previewOverlaySize,
                        PopupSize,
                        StringComparison.OrdinalIgnoreCase))
                {
                    _previewOverlayManager.OverlayDisplayMode =
                        OverlayDisplayMode.ForceShow;
                    _previewOverlayManager.ForceShow = true;
                    return true;
                }
                if (_previewOverlayManager != null)
                {
                    StopPreviewOverlay();
                }

                GraphicalDashPluginListModel model =
                    GraphicalDashPluginListModel.Instance;
                if (model == null || model.OverlayLayouts == null)
                {
                    throw new InvalidOperationException(
                        "Dash Studio overlay layouts are not available.");
                }

                OverlayLayout layout = SelectPreviewLayout(model);
                if (layout == null)
                {
                    throw new InvalidOperationException(
                        "Load an As Driven overlay layout in Dash Studio first.");
                }

                OverlayLayout previewLayout = CreatePreviewLayout(layout, PopupSize);
                _previewOverlayManager = new OverlayLayoutManager(previewLayout, false);
                _previewOverlaySize = PopupSize;
                _previewOverlayManager.OverlayDisplayMode =
                    OverlayDisplayMode.ForceShow;
                _previewOverlayManager.ForceShow = true;
                _previewOverlayManager.Start();
                _lastRuntimeError = string.Empty;
                return true;
            }
            catch (Exception exception)
            {
                _previewOverlayManager = null;
                _previewOverlaySize = string.Empty;
                _lastRuntimeError = "Preview overlay: "
                    + exception.GetType().Name + ": " + exception.Message;
                SimHub.Logging.Current.Error(
                    "As Driven could not show its preview overlay: "
                    + exception.Message);
                return false;
            }
        }

        private static OverlayLayout SelectPreviewLayout(
            GraphicalDashPluginListModel model)
        {
            OverlayLayout[] candidates = model.OverlayLayouts
                .Where(IsAsDrivenLayout)
                .ToArray();
            if (candidates.Length == 0)
            {
                return null;
            }
            if (IsAsDrivenLayout(model.AutoStartLayoutCurrentGame))
            {
                return model.AutoStartLayoutCurrentGame;
            }
            if (IsAsDrivenLayout(model.AutoStartLayout))
            {
                return model.AutoStartLayout;
            }
            string preferredName = PreviewRules.PreferredLayoutName(
                SystemParameters.VirtualScreenWidth);
            return candidates.FirstOrDefault(delegate(OverlayLayout item)
            {
                return string.Equals(
                    item.Name,
                    preferredName,
                    StringComparison.OrdinalIgnoreCase);
            }) ?? candidates[0];
        }

        private static bool IsAsDrivenLayout(OverlayLayout layout)
        {
            return layout != null
                && PreviewRules.IsAsDrivenLayoutName(layout.Name);
        }

        private static OverlayLayout CreatePreviewLayout(
            OverlayLayout sourceLayout,
            string popupSize)
        {
            string dashboardStem;
            switch (NormalizePopupSize(popupSize))
            {
                case "detailed":
                    dashboardStem = "As Driven Preflight Overlay";
                    break;
                case "glance":
                    dashboardStem = "As Driven Preflight Glance";
                    break;
                default:
                    dashboardStem = "As Driven Preflight Compact";
                    break;
            }

            OverlayLayoutPart sourcePart = sourceLayout.OverlayLayoutParts
                .FirstOrDefault(delegate(OverlayLayoutPart part)
                {
                    return part != null
                        && string.Equals(
                            Path.GetFileNameWithoutExtension(part.DashboardName),
                            dashboardStem,
                            StringComparison.OrdinalIgnoreCase);
                });
            if (sourcePart == null)
            {
                throw new InvalidOperationException(
                    "The selected " + popupSize
                    + " surface is missing from the As Driven layout.");
            }

            OverlayLayout previewLayout = (OverlayLayout)Activator.CreateInstance(
                typeof(OverlayLayout),
                true);
            previewLayout.OverlayLayoutParts =
                new ObservableCollection<OverlayLayoutPart>();
            previewLayout.AutoMode = sourceLayout.AutoMode;
            previewLayout.ShowWhenPausedOrInMenu = true;
            previewLayout.Name = sourceLayout.Name + " Preview";
            previewLayout.UniqueId = Guid.NewGuid();
            previewLayout.Version = sourceLayout.Version;
            previewLayout.SaveLastScreens = false;
            previewLayout.OverlayLayoutParts.Add(new OverlayLayoutPart
            {
                DashboardName = sourcePart.DashboardName,
                Top = sourcePart.Top,
                Left = sourcePart.Left,
                Width = sourcePart.Width,
                Height = sourcePart.Height,
                Version = sourcePart.Version,
                PartId = Guid.NewGuid(),
                Placed = sourcePart.Placed,
                Transparent = sourcePart.Transparent,
            });
            return previewLayout;
        }

        private void StopPreviewOverlay()
        {
            OverlayLayoutManager manager = _previewOverlayManager;
            _previewOverlayManager = null;
            _previewOverlaySize = string.Empty;
            if (manager == null)
            {
                return;
            }
            Action stop = delegate
            {
                try
                {
                    manager.Stop();
                }
                catch (Exception exception)
                {
                    SimHub.Logging.Current.Error(
                        "As Driven could not stop its preview overlay: "
                        + exception.Message);
                }
            };
            Application application = Application.Current;
            if (application != null && !application.Dispatcher.CheckAccess())
            {
                application.Dispatcher.BeginInvoke(stop);
            }
            else
            {
                stop();
            }
        }

        internal string OpenDiagnosticsFolder()
        {
            string directory = Path.GetDirectoryName(_unmatchedLogPath);
            Directory.CreateDirectory(directory);
            Process.Start("explorer.exe", "\"" + directory + "\"");
            return directory;
        }

        private void InitializeUnmatchedLog()
        {
            _unmatchedLogPath = ResolveUnmatchedLogPath();
            _simHubVersion = DetectSimHubVersion();
            try
            {
                _unmatchedLog = new UnmatchedIdentityLog(_unmatchedLogPath);
                SimHub.Logging.Current.Info(
                    "As Driven unmatched identity diagnostics: "
                    + _unmatchedLogPath);
            }
            catch (Exception exception)
            {
                _unmatchedLog = null;
                _lastUnmatchedLogError = exception.GetType().Name + ": " + exception.Message;
                SimHub.Logging.Current.Error(
                    "As Driven could not initialize unmatched identity diagnostics: "
                    + _lastUnmatchedLogError);
            }
        }

        private void RecordUnmatchedIdentity(GameData data)
        {
            if (_unmatchedLog == null || data.NewData == null)
            {
                return;
            }

            string carModel = data.NewData.CarModel ?? string.Empty;
            string carId = data.NewData.CarId ?? string.Empty;
            string carClass = data.NewData.CarClass ?? string.Empty;
            string gameVersion = DetectGameVersion(data.GameName ?? string.Empty);
            _lastUnmatchedCarModel = carModel;
            _lastUnmatchedCarId = carId;
            _lastUnmatchedCarClass = carClass;
            _lastUnmatchedGameVersion = gameVersion;

            try
            {
                bool added = _unmatchedLog.Record(new UnmatchedIdentityObservation
                {
                    ObservedAtUtc = DateTime.UtcNow,
                    GameName = data.GameName ?? string.Empty,
                    GameVersion = gameVersion,
                    CarModel = carModel,
                    CarId = carId,
                    CarClass = carClass,
                    DatasetVersion = DatasetVersion(),
                    SimHubVersion = _simHubVersion
                });
                _lastUnmatchedLogError = string.Empty;
                if (added)
                {
                    SimHub.Logging.Current.Info(
                        "As Driven recorded unmatched identity '"
                        + carModel + "' in " + _unmatchedLogPath);
                }
            }
            catch (Exception exception)
            {
                string message = exception.GetType().Name + ": " + exception.Message;
                if (_lastUnmatchedLogError != message)
                {
                    _lastUnmatchedLogError = message;
                    SimHub.Logging.Current.Error(
                        "As Driven could not record unmatched identity: " + message);
                }
            }
        }

        private void UpdateLiveVerificationTelemetry(GameData data)
        {
            bool running = data.GameRunning && data.NewData != null;
            if (!running)
            {
                lock (_verificationTelemetryLock)
                {
                    _liveVerificationContext = null;
                }
                return;
            }

            string gameName = data.GameName ?? string.Empty;
            string gameVersion = DetectGameVersion(gameName);
            string carModel = data.NewData.CarModel ?? string.Empty;
            string carId = data.NewData.CarId ?? string.Empty;
            string carClass = data.NewData.CarClass ?? string.Empty;
            int forwardGears = data.NewData.CarSettings_MaxGears;
            int currentGear;
            if (int.TryParse(data.NewData.Gear, out currentGear)
                && currentGear > forwardGears)
            {
                forwardGears = currentGear;
            }
            lock (_verificationTelemetryLock)
            {
                string simulator = AsDrivenDatabase.CanonicalizeSimulator(gameName);
                _liveVerificationContext = new VerificationCaptureContext
                {
                    Simulator = string.IsNullOrWhiteSpace(simulator) ? "other" : simulator,
                    SimulatorDisplayName = SimulatorDisplayName(simulator, gameName),
                    GameVersion = string.IsNullOrWhiteSpace(gameVersion) ? "unknown" : gameVersion,
                    ClientVersion = "SimHub "
                        + (string.IsNullOrWhiteSpace(_simHubVersion) ? "unknown" : _simHubVersion)
                        + "; As Driven " + PluginVersion,
                    ObservedAtUtc = DateTime.UtcNow,
                    TelemetryName = carModel,
                    TelemetryClass = string.IsNullOrWhiteSpace(carClass) ? "unknown" : carClass,
                    InternalId = carId,
                    SuggestedForwardGears = forwardGears > 0 ? (int?)forwardGears : null
                };
            }
            GuidedDriveSnapshot guided = _guidedDriveSnapshot;
            if (guided.Visible
                && !string.Equals(
                    _guidedVerificationCapture == null
                        ? string.Empty
                        : _guidedVerificationCapture.TelemetryName,
                    carModel,
                    StringComparison.Ordinal))
            {
                GuidedVerificationCancel();
                return;
            }
            if (guided.Visible)
            {
                _guidedVerificationDrive.AddSample(new GuidedTelemetrySample
                {
                    TimestampUtc = DateTime.UtcNow,
                    Gear = currentGear,
                    Clutch = data.NewData.Clutch,
                    Throttle = data.NewData.Throttle,
                    Brake = data.NewData.Brake,
                    Rpm = data.NewData.Rpms,
                    SpeedKmh = data.NewData.SpeedKmh,
                    EngineTorque = data.NewData.EngineTorque,
                    EngineStarted = data.NewData.EngineStarted > 0
                });
                RefreshGuidedDriveSnapshot();
            }
        }

        private void RefreshGuidedDriveSnapshot()
        {
            _guidedDriveSnapshot = _guidedVerificationDrive.GetSnapshot();
        }

        private static string SimulatorDisplayName(string simulator, string rawGameName)
        {
            if (string.Equals(simulator, "ams2", StringComparison.Ordinal)) return "AMS2";
            if (string.Equals(simulator, "iracing", StringComparison.Ordinal)) return "iRacing";
            if (string.Equals(simulator, "ac-evo", StringComparison.Ordinal)) return "Assetto Corsa EVO";
            if (string.Equals(simulator, "ac-rally", StringComparison.Ordinal)) return "Assetto Corsa Rally";
            return string.IsNullOrWhiteSpace(rawGameName) ? "Simulator" : rawGameName;
        }

        private string DetectGameVersion(string gameName)
        {
            if (string.Equals(_detectedVersionGame, gameName, StringComparison.Ordinal)
                && !string.IsNullOrEmpty(_detectedGameVersion))
            {
                return _detectedGameVersion;
            }

            _detectedVersionGame = gameName;
            _detectedGameVersion = "unknown";
            if (AsDrivenDatabase.CanonicalizeSimulator(gameName) != "ams2")
            {
                return _detectedGameVersion;
            }

            foreach (string processName in new[] { "AMS2AVX", "AMS2" })
            {
                Process[] processes = null;
                try
                {
                    processes = Process.GetProcessesByName(processName);
                    foreach (Process process in processes)
                    {
                        string version = DetectFileVersion(ResolveProcessPath(process));
                        if (version != "unknown")
                        {
                            _detectedGameVersion = version;
                            return version;
                        }
                    }
                }
                catch
                {
                    // Access to process metadata can be restricted; preserve unknown.
                }
                finally
                {
                    if (processes != null)
                    {
                        foreach (Process process in processes)
                        {
                            process.Dispose();
                        }
                    }
                }
            }
            return _detectedGameVersion;
        }

        private static string DetectFileVersion(string path)
        {
            try
            {
                if (!File.Exists(path))
                {
                    return "unknown";
                }
                string version = FileVersionInfo.GetVersionInfo(path).FileVersion;
                return VersionText.Normalize(version);
            }
            catch
            {
                return "unknown";
            }
        }

        private static string DetectSimHubVersion()
        {
            string logPath = Path.Combine(
                AppDomain.CurrentDomain.BaseDirectory, "Logs", "SimHub.txt");
            try
            {
                using (var stream = new FileStream(
                    logPath,
                    FileMode.Open,
                    FileAccess.Read,
                    FileShare.ReadWrite))
                using (var reader = new StreamReader(stream))
                {
                    for (int index = 0; index < 20 && !reader.EndOfStream; index++)
                    {
                        string version = VersionText.ParseSimHubStartupLine(reader.ReadLine());
                        if (version != "unknown")
                        {
                            return version;
                        }
                    }
                }
            }
            catch
            {
                // The log may not be available during very early startup.
            }
            return "unknown";
        }

        private static string ResolveProcessPath(Process process)
        {
            try
            {
                return process.MainModule.FileName;
            }
            catch
            {
                IntPtr handle = OpenProcess(
                    ProcessQueryLimitedInformation,
                    false,
                    process.Id);
                if (handle == IntPtr.Zero)
                {
                    return string.Empty;
                }
                try
                {
                    var path = new StringBuilder(32768);
                    int size = path.Capacity;
                    return QueryFullProcessImageName(handle, 0, path, ref size)
                        ? path.ToString()
                        : string.Empty;
                }
                finally
                {
                    CloseHandle(handle);
                }
            }
        }

        private static double NormalizePopupDuration(double seconds)
        {
            return PopupPreferences.NormalizeDuration(seconds);
        }

        private static string NormalizePopupSize(string popupSize)
        {
            return PopupPreferences.NormalizeSize(popupSize);
        }

        private static string ResolveDatabasePath()
        {
            string configured = Environment.GetEnvironmentVariable(
                "AS_DRIVEN_DATA");
            if (!string.IsNullOrWhiteSpace(configured))
            {
                return Path.GetFullPath(configured);
            }
            return Path.Combine(
                AppDomain.CurrentDomain.BaseDirectory,
                "PluginsData",
                "AsDriven",
                "Database",
                "data",
                "v1");
        }

        private static string ResolveUnmatchedLogPath()
        {
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "SimHub",
                "AsDriven",
                "Diagnostics",
                "unmatched-identities.jsonl");
        }

        private static string ResolveVerificationDraftDirectory()
        {
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "SimHub",
                "AsDriven",
                "Verification",
                "Drafts");
        }

        private string DatasetVersion()
        {
            return _current == null ? string.Empty : _current.DatasetVersion;
        }

        private void AttachProperties()
        {
            this.AttachDelegate("HasMatch", delegate { return _current.HasMatch; });
            this.AttachDelegate("MatchStatus", delegate { return _current.MatchStatus; });
            this.AttachDelegate("RawGameName", delegate { return _current.RawGameName; });
            this.AttachDelegate("RawCarIdentifier", delegate { return _current.RawCarIdentifier; });
            this.AttachDelegate("DatabasePath", delegate { return _databasePath; });
            this.AttachDelegate("UnmatchedLogPath", delegate { return _unmatchedLogPath; });
            this.AttachDelegate(
                "UnmatchedLogCount",
                delegate { return _unmatchedLog == null ? 0 : _unmatchedLog.Count; });
            this.AttachDelegate("LastUnmatchedCarModel", delegate { return _lastUnmatchedCarModel; });
            this.AttachDelegate("LastUnmatchedCarId", delegate { return _lastUnmatchedCarId; });
            this.AttachDelegate("LastUnmatchedCarClass", delegate { return _lastUnmatchedCarClass; });
            this.AttachDelegate("LastUnmatchedGameVersion", delegate { return _lastUnmatchedGameVersion; });
            this.AttachDelegate("UnmatchedLogError", delegate { return _lastUnmatchedLogError; });
            this.AttachDelegate("DatasetVersion", delegate { return _current.DatasetVersion; });
            this.AttachDelegate("RecordId", delegate { return _current.RecordId; });
            this.AttachDelegate("DisplayName", delegate { return _current.DisplayName; });
            this.AttachDelegate("CarClass", delegate { return _current.CarClass; });
            this.AttachDelegate("OverlayCarNameDetailed", delegate { return _current.OverlayCarNameDetailed; });
            this.AttachDelegate("OverlayCarClassDetailed", delegate { return _current.OverlayCarClassDetailed; });
            this.AttachDelegate("OverlayCarNameCompact", delegate { return _current.OverlayCarNameCompact; });
            this.AttachDelegate("OverlayCarClassCompact", delegate { return _current.OverlayCarClassCompact; });
            this.AttachDelegate("OverlayCarNameGlance", delegate { return _current.OverlayCarNameGlance; });
            this.AttachDelegate("ShiftType", delegate { return _current.ShiftType; });
            this.AttachDelegate("ShiftActuation", delegate { return _current.ShiftActuation; });
            this.AttachDelegate("ShiftPattern", delegate { return _current.ShiftPattern; });
            this.AttachDelegate("FirstGearPosition", delegate { return _current.FirstGearPosition; });
            this.AttachDelegate("GearCount", delegate { return _current.GearCount; });
            this.AttachDelegate("UpshiftGuidance", delegate { return _current.UpshiftGuidance; });
            this.AttachDelegate("DownshiftGuidance", delegate { return _current.DownshiftGuidance; });
            this.AttachDelegate("TechniqueSummary", delegate { return _current.TechniqueSummary; });
            this.AttachDelegate("TechniqueSummaryLine1", delegate { return _current.TechniqueSummaryLine1; });
            this.AttachDelegate("TechniqueSummaryLine2", delegate { return _current.TechniqueSummaryLine2; });
            this.AttachDelegate("TechniqueSummaryCompactLine1", delegate { return _current.TechniqueSummaryCompactLine1; });
            this.AttachDelegate("TechniqueSummaryCompactLine2", delegate { return _current.TechniqueSummaryCompactLine2; });
            this.AttachDelegate("StandingStartClutch", delegate { return _current.StandingStartClutch; });
            this.AttachDelegate("AutoBlip", delegate { return _current.AutoBlip; });
            this.AttachDelegate("ShiftCut", delegate { return _current.ShiftCut; });
            this.AttachDelegate("ManualBlip", delegate { return _current.ManualBlip; });
            this.AttachDelegate("ThrottleLift", delegate { return _current.ThrottleLift; });
            this.AttachDelegate("WheelRimShape", delegate { return _current.WheelRimShape; });
            this.AttachDelegate("WheelRimSourceLabel", delegate { return _current.WheelRimSourceLabel; });
            this.AttachDelegate("WheelIntegratedDisplay", delegate { return _current.WheelIntegratedDisplay; });
            this.AttachDelegate("WheelShiftLights", delegate { return _current.WheelShiftLights; });
            this.AttachDelegate("WheelRimLabel", delegate { return _current.WheelRimLabel; });
            this.AttachDelegate("WheelFeatureLabel", delegate { return _current.WheelFeatureLabel; });
            this.AttachDelegate("ShifterLabel", delegate { return _current.ShifterLabel; });
            this.AttachDelegate("ShifterGateLabel", delegate { return _current.ShifterGateLabel; });
            this.AttachDelegate("LaunchLabel", delegate { return _current.LaunchLabel; });
            this.AttachDelegate("UpshiftLabel", delegate { return _current.UpshiftLabel; });
            this.AttachDelegate("DownshiftLabel", delegate { return _current.DownshiftLabel; });
            this.AttachDelegate("LaunchTone", delegate { return _current.LaunchTone; });
            this.AttachDelegate("UpshiftTone", delegate { return _current.UpshiftTone; });
            this.AttachDelegate("DownshiftTone", delegate { return _current.DownshiftTone; });
            this.AttachDelegate("UseBandTone", delegate { return _current.UseBandTone; });
            this.AttachDelegate("DriverSummary", delegate { return _current.DriverSummary; });
            this.AttachDelegate("DriverSummaryLine1", delegate { return _current.DriverSummaryLine1; });
            this.AttachDelegate("DriverSummaryLine2", delegate { return _current.DriverSummaryLine2; });
            this.AttachDelegate("DriverSummaryLine3", delegate { return _current.DriverSummaryLine3; });
            this.AttachDelegate("DriverSummaryCompactLine1", delegate { return _current.DriverSummaryCompactLine1; });
            this.AttachDelegate("DriverSummaryCompactLine2", delegate { return _current.DriverSummaryCompactLine2; });
            this.AttachDelegate("DriverSummaryCompactLine3", delegate { return _current.DriverSummaryCompactLine3; });
            this.AttachDelegate("SimulatorDiffers", delegate { return _current.SimulatorDiffers; });
            this.AttachDelegate("SimulatorDifference", delegate { return _current.SimulatorDifference; });
            this.AttachDelegate("ShifterDiffers", delegate { return _current.ShifterDiffers; });
            this.AttachDelegate("LaunchDiffers", delegate { return _current.LaunchDiffers; });
            this.AttachDelegate("UpshiftDiffers", delegate { return _current.UpshiftDiffers; });
            this.AttachDelegate("DownshiftDiffers", delegate { return _current.DownshiftDiffers; });
            this.AttachDelegate("WheelDiffers", delegate { return _current.WheelDiffers; });
            this.AttachDelegate("UpshiftClutch", delegate { return _current.UpshiftClutch; });
            this.AttachDelegate("DownshiftClutch", delegate { return _current.DownshiftClutch; });
            this.AttachDelegate("UpshiftClutchLabel", delegate { return _current.UpshiftClutchLabel; });
            this.AttachDelegate("DownshiftClutchLabel", delegate { return _current.DownshiftClutchLabel; });
            this.AttachDelegate("LaunchDetailLabel", delegate { return _current.LaunchDetailLabel; });
            this.AttachDelegate("HasSteeringDOR", delegate { return _current.HasSteeringDOR; });
            this.AttachDelegate("SteeringDOR", delegate { return _current.SteeringDOR; });
            this.AttachDelegate("VerifiedGameVersion", delegate { return _current.VerifiedGameVersion; });
            this.AttachDelegate("Confidence", delegate { return _current.Confidence; });
            this.AttachDelegate("SourceSummary", delegate { return _current.SourceSummary; });
            this.AttachDelegate("MatchKind", delegate { return _current.MatchKind; });
            this.AttachDelegate("GuidanceSummary", delegate { return _current.GuidanceSummary; });
            this.AttachDelegate("PreviewActive", delegate { return _previewActive; });
            this.AttachDelegate("PopupRevision", delegate { return _current.PopupRevision; });
            this.AttachDelegate(
                "PopupVisible",
                delegate { return _popupState.IsVisible(DateTime.UtcNow); });
            this.AttachDelegate(
                "PopupDurationSeconds",
                delegate { return _popupState.AutomaticDurationSeconds; });
            this.AttachDelegate(
                "PopupSize",
                delegate { return PopupSize; });
            this.AttachDelegate(
                "PopupDetailedVisible",
                delegate
                {
                    return PopupSize == "detailed"
                        && _popupState.IsVisible(DateTime.UtcNow);
                });
            this.AttachDelegate(
                "PopupCompactVisible",
                delegate
                {
                    return PopupSize == "compact"
                        && _popupState.IsVisible(DateTime.UtcNow);
                });
            this.AttachDelegate(
                "PopupGlanceVisible",
                delegate
                {
                    return PopupSize == "glance"
                        && _popupState.IsVisible(DateTime.UtcNow);
                });
            this.AttachDelegate(
                "VerificationDriveVisible",
                delegate { return _guidedDriveSnapshot.Visible; });
            this.AttachDelegate(
                "VerificationDriveCompleted",
                delegate { return _guidedDriveSnapshot.Completed; });
            this.AttachDelegate(
                "VerificationDriveResultReady",
                delegate { return _guidedDriveSnapshot.ResultReady; });
            this.AttachDelegate(
                "VerificationDriveResultSuccessful",
                delegate { return _guidedDriveSnapshot.ResultSuccessful; });
            this.AttachDelegate(
                "VerificationDriveStepNumber",
                delegate { return _guidedDriveSnapshot.StepNumber; });
            this.AttachDelegate(
                "VerificationDriveStepCount",
                delegate { return _guidedDriveSnapshot.StepCount; });
            this.AttachDelegate(
                "VerificationDriveTitle",
                delegate { return _guidedDriveSnapshot.Title; });
            this.AttachDelegate(
                "VerificationDrivePrompt",
                delegate { return _guidedDriveSnapshot.Prompt; });
            this.AttachDelegate(
                "VerificationDrivePromptLine1",
                delegate { return _guidedDriveSnapshot.PromptLine1; });
            this.AttachDelegate(
                "VerificationDrivePromptLine2",
                delegate { return _guidedDriveSnapshot.PromptLine2; });
            this.AttachDelegate(
                "VerificationDriveStatus",
                delegate { return _guidedDriveSnapshot.Status; });
            this.AttachDelegate(
                "VerificationDriveResult",
                delegate { return _guidedDriveSnapshot.ResultSummary; });
            this.AttachDelegate(
                "VerificationDriveResultDetail",
                delegate { return _guidedDriveSnapshot.Result; });
            this.AttachDelegate(
                "VerificationDriveLiveValues",
                delegate { return _guidedDriveSnapshot.LiveValues; });
        }
    }
}
