using System;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using AuthenticControls.Core;
using GameReaderCommon;
using SimHub.Plugins;
using SimHub.Plugins.OutputPlugins.GraphicalDash;
using SimHub.Plugins.OutputPlugins.GraphicalDash.Overlays;

namespace AuthenticControls.Plugin
{
    [PluginDescription("Shows the authentic physical controls and shifting technique for the current car.")]
    [PluginAuthor("Jason Kinslow")]
    [PluginName("Authentic Controls")]
    public sealed class AuthenticControls : IPlugin, IDataPlugin, IWPFSettings, IWPFSettingsV2
    {
        internal const double DefaultPopupDurationSeconds = 10.0;
        internal const double MinimumPopupDurationSeconds = 1.0;
        internal const double MaximumPopupDurationSeconds = 60.0;
        internal const string DefaultPopupSize = "compact";
        private const int ProcessQueryLimitedInformation = 0x1000;
        private static readonly System.Drawing.Bitmap MenuIcon =
            AuthenticControlsMenuIcon.Create();
        private static readonly System.Drawing.Bitmap HeaderIcon =
            AuthenticControlsMenuIcon.CreateHeader();

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
        private AuthenticControlsSettings _settings = new AuthenticControlsSettings();
        private AuthenticControlsDatabase _database;
        private SessionState _session;
        private bool _previewActive;
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
        private bool _liveVerificationGameRunning;
        private string _liveVerificationGameName = string.Empty;
        private string _liveVerificationGameVersion = string.Empty;
        private string _liveVerificationCarModel = string.Empty;
        private string _liveVerificationCarId = string.Empty;
        private string _liveVerificationCarClass = string.Empty;
        private int _liveVerificationForwardGears;
        private string _guidedVerificationCarModel = string.Empty;
        private VerificationCaptureContext _guidedVerificationCapture;

        public PluginManager PluginManager { get; set; }

        public ImageSource PictureIcon { get { return this.ToIcon(MenuIcon); } }

        internal ImageSource HeaderPictureIcon
        {
            get { return this.ToIcon(HeaderIcon); }
        }

        public string LeftMenuTitle { get { return "Authentic Controls"; } }

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
                delegate(PluginManager manager, string parameter) { _popupState.Show(); });
            this.AddAction(
                "HidePopup",
                delegate(PluginManager manager, string parameter) { _popupState.Hide(); });
            this.AddAction(
                "TogglePopup",
                delegate(PluginManager manager, string parameter)
                {
                    _popupState.Toggle(DateTime.UtcNow);
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
            return new AuthenticControlsSettingsControl(this);
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
                bool leavingPreview = _previewActive && data.GameRunning;
                if (_previewActive && !data.GameRunning)
                {
                    return;
                }
                if (leavingPreview)
                {
                    _previewActive = false;
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
                        "Authentic Controls DataUpdate failed: " + message);
                }
            }
        }

        public void End(PluginManager pluginManager)
        {
            _previewActive = false;
            StopPreviewOverlay();
            _popupState.Hide();
            _guidedVerificationDrive.Cancel();
        }

        private void LoadDatabase()
        {
            try
            {
                string path = ResolveDatabasePath();
                AuthenticControlsDatabase database = AuthenticControlsDatabase.Load(path);
                _database = database;
                _databasePath = database.DataDirectory;
                _databaseRecordCount = database.RecordCount;
                _session = new SessionState(database);
                _previewActive = false;
                StopPreviewOverlay();
                _current = _session.Current;
                _lastRuntimeError = string.Empty;
                SimHub.Logging.Current.Info(
                    "Authentic Controls loaded dataset " + database.DatasetVersion
                    + " with " + database.RecordCount + " records from " + path);
            }
            catch (Exception exception)
            {
                _session = null;
                _database = null;
                _previewActive = false;
                StopPreviewOverlay();
                _databaseRecordCount = 0;
                _current = GuidanceSnapshot.Empty(
                    "database-error", string.Empty, string.Empty, string.Empty);
                _databasePath = ResolveDatabasePath();
                _lastRuntimeError = exception.GetType().Name + ": " + exception.Message;
                SimHub.Logging.Current.Error(
                    "Authentic Controls could not load its database from "
                    + _databasePath + ": " + exception.Message);
            }
        }

        private void LoadSettings()
        {
            try
            {
                _settings = this.ReadCommonSettings<AuthenticControlsSettings>(
                    "Settings",
                    delegate { return new AuthenticControlsSettings(); });
                double seconds = NormalizePopupDuration(
                    _settings.PopupDurationSeconds);
                _settings.PopupDurationSeconds = seconds;
                _settings.PopupSize = NormalizePopupSize(_settings.PopupSize);
                _popupState.SetAutomaticDuration(TimeSpan.FromSeconds(seconds));
            }
            catch (Exception exception)
            {
                _settings = new AuthenticControlsSettings();
                _popupState.SetAutomaticDuration(
                    TimeSpan.FromSeconds(DefaultPopupDurationSeconds));
                SimHub.Logging.Current.Error(
                    "Authentic Controls could not load settings: " + exception.Message);
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

        internal void ShowPopup()
        {
            _popupState.Show();
            if (_previewActive)
            {
                StartPreviewOverlay();
            }
        }

        internal void HidePopup()
        {
            _popupState.Hide();
        }

        internal void RefreshDatabase()
        {
            LoadDatabase();
        }

        internal VerificationCaptureContext CaptureVerificationContext()
        {
            lock (_verificationTelemetryLock)
            {
                if (!_liveVerificationGameRunning
                    || string.IsNullOrWhiteSpace(_liveVerificationCarModel))
                {
                    return null;
                }
                string simulator = AuthenticControlsDatabase.CanonicalizeSimulator(
                    _liveVerificationGameName);
                return new VerificationCaptureContext
                {
                    Simulator = string.IsNullOrWhiteSpace(simulator) ? "other" : simulator,
                    SimulatorDisplayName = SimulatorDisplayName(simulator, _liveVerificationGameName),
                    GameVersion = string.IsNullOrWhiteSpace(_liveVerificationGameVersion)
                        ? "unknown"
                        : _liveVerificationGameVersion,
                    ClientVersion = "SimHub "
                        + (string.IsNullOrWhiteSpace(_simHubVersion) ? "unknown" : _simHubVersion)
                        + "; Authentic Controls " + PluginVersion,
                    ObservedAtUtc = DateTime.UtcNow,
                    TelemetryName = _liveVerificationCarModel,
                    TelemetryClass = string.IsNullOrWhiteSpace(_liveVerificationCarClass)
                        ? "unknown"
                        : _liveVerificationCarClass,
                    InternalId = _liveVerificationCarId,
                    SuggestedForwardGears = _liveVerificationForwardGears > 0
                        ? (int?)_liveVerificationForwardGears
                        : null
                };
            }
        }

        internal void StartGuidedVerificationDrive(VerificationCaptureContext capture)
        {
            if (capture == null)
            {
                throw new ArgumentNullException("capture");
            }
            _guidedVerificationCarModel = capture.TelemetryName ?? string.Empty;
            _guidedVerificationCapture = capture;
            _popupState.Hide();
            _guidedVerificationDrive.Start(capture.SuggestedForwardGears);
        }

        internal GuidedDriveSnapshot GetGuidedDriveSnapshot()
        {
            return _guidedVerificationDrive.GetSnapshot();
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
        }

        internal void GuidedVerificationRetry()
        {
            _guidedVerificationDrive.Retry();
        }

        internal void GuidedVerificationSkip()
        {
            _guidedVerificationDrive.Skip();
        }

        internal void GuidedVerificationCancel()
        {
            bool completed = _guidedVerificationDrive.GetSnapshot().Completed;
            _guidedVerificationDrive.Cancel();
            _guidedVerificationCarModel = string.Empty;
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
            _popupState.Show();
            if (StartPreviewOverlay())
            {
                return true;
            }
            _previewActive = false;
            _current = _session == null ? preview : _session.Current;
            _popupState.Hide();
            return false;
        }

        internal void ReturnToLiveCar()
        {
            _previewActive = false;
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
                        "Load an Authentic Controls overlay layout in Dash Studio first.");
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
                    "Authentic Controls could not show its preview overlay: "
                    + exception.Message);
                return false;
            }
        }

        private static OverlayLayout SelectPreviewLayout(
            GraphicalDashPluginListModel model)
        {
            OverlayLayout[] candidates = model.OverlayLayouts
                .Where(IsAuthenticControlsLayout)
                .ToArray();
            if (candidates.Length == 0)
            {
                return null;
            }
            if (IsAuthenticControlsLayout(model.AutoStartLayoutCurrentGame))
            {
                return model.AutoStartLayoutCurrentGame;
            }
            if (IsAuthenticControlsLayout(model.AutoStartLayout))
            {
                return model.AutoStartLayout;
            }
            string preferredName = SystemParameters.VirtualScreenWidth >= 3840
                ? "Authentic Controls 5120x1440"
                : "Authentic Controls";
            return candidates.FirstOrDefault(delegate(OverlayLayout item)
            {
                return string.Equals(
                    item.Name,
                    preferredName,
                    StringComparison.OrdinalIgnoreCase);
            }) ?? candidates[0];
        }

        private static bool IsAuthenticControlsLayout(OverlayLayout layout)
        {
            return layout != null
                && !string.IsNullOrWhiteSpace(layout.Name)
                && layout.Name.StartsWith(
                    "Authentic Controls",
                    StringComparison.OrdinalIgnoreCase);
        }

        private static OverlayLayout CreatePreviewLayout(
            OverlayLayout sourceLayout,
            string popupSize)
        {
            string dashboardStem;
            switch (NormalizePopupSize(popupSize))
            {
                case "detailed":
                    dashboardStem = "Authentic Controls Preflight Overlay";
                    break;
                case "glance":
                    dashboardStem = "Authentic Controls Preflight Glance";
                    break;
                default:
                    dashboardStem = "Authentic Controls Preflight Compact";
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
                    + " surface is missing from the Authentic Controls layout.");
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
                        "Authentic Controls could not stop its preview overlay: "
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
                    "Authentic Controls unmatched identity diagnostics: "
                    + _unmatchedLogPath);
            }
            catch (Exception exception)
            {
                _unmatchedLog = null;
                _lastUnmatchedLogError = exception.GetType().Name + ": " + exception.Message;
                SimHub.Logging.Current.Error(
                    "Authentic Controls could not initialize unmatched identity diagnostics: "
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
                        "Authentic Controls recorded unmatched identity '"
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
                        "Authentic Controls could not record unmatched identity: " + message);
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
                    _liveVerificationGameRunning = false;
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
                _liveVerificationGameRunning = true;
                _liveVerificationGameName = gameName;
                _liveVerificationGameVersion = gameVersion;
                _liveVerificationCarModel = carModel;
                _liveVerificationCarId = carId;
                _liveVerificationCarClass = carClass;
                _liveVerificationForwardGears = forwardGears;
            }
            GuidedDriveSnapshot guided = _guidedVerificationDrive.GetSnapshot();
            if (guided.Visible
                && !string.Equals(
                    _guidedVerificationCarModel,
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
                    Rpm = data.NewData.Rpms,
                    SpeedKmh = data.NewData.SpeedKmh,
                    EngineTorque = data.NewData.EngineTorque,
                    EngineStarted = data.NewData.EngineStarted > 0
                });
            }
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
            if (AuthenticControlsDatabase.CanonicalizeSimulator(gameName) != "ams2")
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
            if (double.IsNaN(seconds) || double.IsInfinity(seconds))
            {
                return DefaultPopupDurationSeconds;
            }
            return Math.Max(
                MinimumPopupDurationSeconds,
                Math.Min(MaximumPopupDurationSeconds, Math.Round(seconds)));
        }

        private static string NormalizePopupSize(string popupSize)
        {
            string normalized = (popupSize ?? string.Empty).Trim().ToLowerInvariant();
            if (normalized == "detailed" || normalized == "compact" || normalized == "glance")
            {
                return normalized;
            }
            return DefaultPopupSize;
        }

        private static string ResolveDatabasePath()
        {
            string configured = Environment.GetEnvironmentVariable(
                "AUTHENTIC_CONTROLS_DATA");
            if (!string.IsNullOrWhiteSpace(configured))
            {
                return Path.GetFullPath(configured);
            }
            return Path.Combine(
                AppDomain.CurrentDomain.BaseDirectory,
                "PluginsData",
                "AuthenticControls",
                "Database",
                "data",
                "v1");
        }

        private static string ResolveUnmatchedLogPath()
        {
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "SimHub",
                "AuthenticControls",
                "Diagnostics",
                "unmatched-identities.jsonl");
        }

        private static string ResolveVerificationDraftDirectory()
        {
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "SimHub",
                "AuthenticControls",
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
            this.AttachDelegate("ShiftType", delegate { return _current.ShiftType; });
            this.AttachDelegate("ShiftActuation", delegate { return _current.ShiftActuation; });
            this.AttachDelegate("ShiftPattern", delegate { return _current.ShiftPattern; });
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
            this.AttachDelegate("WheelRimShape", delegate { return _current.WheelRimShape; });
            this.AttachDelegate("WheelRimSourceLabel", delegate { return _current.WheelRimSourceLabel; });
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
                delegate { return _guidedVerificationDrive.GetSnapshot().Visible; });
            this.AttachDelegate(
                "VerificationDriveCompleted",
                delegate { return _guidedVerificationDrive.GetSnapshot().Completed; });
            this.AttachDelegate(
                "VerificationDriveResultReady",
                delegate { return _guidedVerificationDrive.GetSnapshot().ResultReady; });
            this.AttachDelegate(
                "VerificationDriveResultSuccessful",
                delegate { return _guidedVerificationDrive.GetSnapshot().ResultSuccessful; });
            this.AttachDelegate(
                "VerificationDriveStepNumber",
                delegate { return _guidedVerificationDrive.GetSnapshot().StepNumber; });
            this.AttachDelegate(
                "VerificationDriveStepCount",
                delegate { return _guidedVerificationDrive.GetSnapshot().StepCount; });
            this.AttachDelegate(
                "VerificationDriveTitle",
                delegate { return _guidedVerificationDrive.GetSnapshot().Title; });
            this.AttachDelegate(
                "VerificationDrivePrompt",
                delegate { return _guidedVerificationDrive.GetSnapshot().Prompt; });
            this.AttachDelegate(
                "VerificationDrivePromptLine1",
                delegate { return _guidedVerificationDrive.GetSnapshot().PromptLine1; });
            this.AttachDelegate(
                "VerificationDrivePromptLine2",
                delegate { return _guidedVerificationDrive.GetSnapshot().PromptLine2; });
            this.AttachDelegate(
                "VerificationDriveStatus",
                delegate { return _guidedVerificationDrive.GetSnapshot().Status; });
            this.AttachDelegate(
                "VerificationDriveResult",
                delegate { return _guidedVerificationDrive.GetSnapshot().ResultSummary; });
            this.AttachDelegate(
                "VerificationDriveResultDetail",
                delegate { return _guidedVerificationDrive.GetSnapshot().Result; });
            this.AttachDelegate(
                "VerificationDriveLiveValues",
                delegate { return _guidedVerificationDrive.GetSnapshot().LiveValues; });
        }
    }
}
