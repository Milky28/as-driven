using System;
using System.IO;
using AuthenticControls.Core;
using GameReaderCommon;
using SimHub.Plugins;

namespace AuthenticControls.Plugin
{
    [PluginDescription("Shows the authentic physical controls and shifting technique for the current car.")]
    [PluginAuthor("Authentic Controls Database contributors")]
    [PluginName("Authentic Controls")]
    public sealed class AuthenticControls : IPlugin, IDataPlugin
    {
        private GuidanceSnapshot _current = GuidanceSnapshot.Empty(
            "not-initialized", string.Empty, string.Empty, string.Empty);
        private SessionState _session;
        private string _databasePath = string.Empty;
        private string _lastRuntimeError = string.Empty;

        public PluginManager PluginManager { get; set; }

        public void Init(PluginManager pluginManager)
        {
            PluginManager = pluginManager;
            AttachProperties();
            this.AddAction(
                "RefreshDatabase",
                delegate(PluginManager manager, string parameter) { LoadDatabase(); });
            LoadDatabase();
        }

        public void DataUpdate(PluginManager pluginManager, ref GameData data)
        {
            try
            {
                SessionState session = _session;
                if (session == null)
                {
                    return;
                }

                string carIdentifier = data.NewData == null
                    ? string.Empty
                    : data.NewData.CarModel ?? string.Empty;
                if (session.Update(
                    data.GameRunning,
                    data.GameName ?? string.Empty,
                    carIdentifier))
                {
                    _current = session.Current;
                }
            }
            catch (Exception exception)
            {
                string message = exception.GetType().Name + ": " + exception.Message;
                _current = GuidanceSnapshot.Empty(
                    "runtime-error", data.GameName, string.Empty, DatasetVersion());
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
        }

        private void LoadDatabase()
        {
            try
            {
                string path = ResolveDatabasePath();
                AuthenticControlsDatabase database = AuthenticControlsDatabase.Load(path);
                _databasePath = database.DataDirectory;
                _session = new SessionState(database);
                _current = _session.Current;
                _lastRuntimeError = string.Empty;
                SimHub.Logging.Current.Info(
                    "Authentic Controls loaded dataset " + database.DatasetVersion
                    + " with " + database.RecordCount + " records from " + path);
            }
            catch (Exception exception)
            {
                _session = null;
                _current = GuidanceSnapshot.Empty(
                    "database-error", string.Empty, string.Empty, string.Empty);
                _databasePath = ResolveDatabasePath();
                SimHub.Logging.Current.Error(
                    "Authentic Controls could not load its database from "
                    + _databasePath + ": " + exception.Message);
            }
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
            this.AttachDelegate("DatasetVersion", delegate { return _current.DatasetVersion; });
            this.AttachDelegate("RecordId", delegate { return _current.RecordId; });
            this.AttachDelegate("DisplayName", delegate { return _current.DisplayName; });
            this.AttachDelegate("CarClass", delegate { return _current.CarClass; });
            this.AttachDelegate("ShiftType", delegate { return _current.ShiftType; });
            this.AttachDelegate("ShiftActuation", delegate { return _current.ShiftActuation; });
            this.AttachDelegate("GearCount", delegate { return _current.GearCount; });
            this.AttachDelegate("UpshiftGuidance", delegate { return _current.UpshiftGuidance; });
            this.AttachDelegate("DownshiftGuidance", delegate { return _current.DownshiftGuidance; });
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
            this.AttachDelegate("PopupRevision", delegate { return _current.PopupRevision; });
        }
    }
}
