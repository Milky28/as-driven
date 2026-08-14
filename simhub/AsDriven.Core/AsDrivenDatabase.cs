using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;

namespace AsDriven.Core
{
    public sealed class AsDrivenDatabase
    {
        private static readonly string[] MatchPriority =
        {
            "telemetry-name",
            "display-name",
            "alias",
            "internal-id",
            "car-path"
        };

        private readonly Dictionary<string, MatchEntry> _identities;
        private readonly Dictionary<string, MatchEntry> _records;

        private AsDrivenDatabase(
            string dataDirectory,
            string datasetVersion,
            int recordCount,
            Dictionary<string, MatchEntry> identities,
            Dictionary<string, MatchEntry> records,
            CarCatalogEntry[] cars)
        {
            DataDirectory = dataDirectory;
            DatasetVersion = datasetVersion;
            RecordCount = recordCount;
            _identities = identities;
            _records = records;
            Cars = cars;
        }

        public string DataDirectory { get; private set; }
        public string DatasetVersion { get; private set; }
        public int RecordCount { get; private set; }
        public CarCatalogEntry[] Cars { get; private set; }

        public static AsDrivenDatabase Load(string dataDirectory)
        {
            if (string.IsNullOrWhiteSpace(dataDirectory))
            {
                throw new ArgumentException("A data directory is required.", "dataDirectory");
            }

            string root = Path.GetFullPath(dataDirectory);
            string indexPath = Path.Combine(root, "index.json");
            JObject index = ReadObject(indexPath);
            RequireVersion(index, indexPath);
            string datasetVersion = RequiredString(index, "dataset_version", indexPath);
            JArray records = index["records"] as JArray;
            if (records == null)
            {
                throw new InvalidDataException("Dataset index has no records array: " + indexPath);
            }

            var identities = new Dictionary<string, MatchEntry>(StringComparer.Ordinal);
            var recordsBySimulator = new Dictionary<string, MatchEntry>(StringComparer.Ordinal);
            var cars = new List<CarCatalogEntry>();
            int recordCount = 0;
            foreach (JToken recordPathToken in records)
            {
                string relativePath = recordPathToken.Value<string>();
                string recordPath = ResolveInside(root, relativePath);
                JObject record = ReadObject(recordPath);
                RequireVersion(record, recordPath);
                IndexRecord(
                    record,
                    recordPath,
                    datasetVersion,
                    identities,
                    recordsBySimulator,
                    cars);
                recordCount++;
            }

            cars.Sort(delegate(CarCatalogEntry left, CarCatalogEntry right)
            {
                int nameOrder = string.Compare(
                    left.DisplayName,
                    right.DisplayName,
                    StringComparison.OrdinalIgnoreCase);
                return nameOrder != 0
                    ? nameOrder
                    : string.Compare(left.CarClass, right.CarClass, StringComparison.OrdinalIgnoreCase);
            });
            return new AsDrivenDatabase(
                root,
                datasetVersion,
                recordCount,
                identities,
                recordsBySimulator,
                cars.ToArray());
        }

        public GuidanceSnapshot Match(string rawGameName, string rawCarIdentifier)
        {
            string simulator = CanonicalizeSimulator(rawGameName);
            if (simulator == null)
            {
                return GuidanceSnapshot.Empty(
                    "unsupported-game", rawGameName, rawCarIdentifier, DatasetVersion);
            }
            if (string.IsNullOrEmpty(rawCarIdentifier))
            {
                return GuidanceSnapshot.Empty(
                    "no-car", rawGameName, rawCarIdentifier, DatasetVersion);
            }

            foreach (string kind in MatchPriority)
            {
                MatchEntry entry;
                if (_identities.TryGetValue(Key(simulator, kind, rawCarIdentifier), out entry))
                {
                    return entry.CreateSnapshot(rawGameName, rawCarIdentifier, kind);
                }
            }

            return GuidanceSnapshot.Empty(
                "unmatched", rawGameName, rawCarIdentifier, DatasetVersion);
        }

        public GuidanceSnapshot Preview(string simulatorName, string recordId)
        {
            string simulator = CanonicalizeSimulator(simulatorName);
            MatchEntry entry;
            if (simulator == null
                || string.IsNullOrWhiteSpace(recordId)
                || !_records.TryGetValue(RecordKey(simulator, recordId), out entry))
            {
                return GuidanceSnapshot.Empty(
                    "preview-not-found",
                    simulatorName,
                    recordId,
                    DatasetVersion);
            }
            return entry.CreateSnapshot(
                SimulatorDisplayName(simulator),
                entry.DisplayName,
                "preview");
        }

        public static string CanonicalizeSimulator(string gameName)
        {
            if (string.IsNullOrWhiteSpace(gameName))
            {
                return null;
            }
            string compact = new string(
                gameName.Where(char.IsLetterOrDigit).ToArray()).ToLowerInvariant();
            if (compact == "automobilista2" || compact == "ams2")
            {
                return "ams2";
            }
            if (compact == "iracing")
            {
                return "iracing";
            }
            return null;
        }

        private static void IndexRecord(
            JObject record,
            string recordPath,
            string datasetVersion,
            Dictionary<string, MatchEntry> identities,
            Dictionary<string, MatchEntry> records,
            List<CarCatalogEntry> cars)
        {
            string recordId = RequiredString(record, "record_id", recordPath);
            JObject identity = RequiredObject(record, "identity", recordPath);
            JObject controls = RequiredObject(record, "authentic_controls", recordPath);
            JObject transmission = RequiredObject(controls, "transmission", recordPath);
            JObject steering = RequiredObject(controls, "steering", recordPath);
            JObject wheelRim = RequiredObject(steering, "wheel_rim", recordPath);
            JArray simulators = record["simulators"] as JArray;
            if (simulators == null || simulators.Count == 0)
            {
                throw new InvalidDataException("Record has no simulator entries: " + recordPath);
            }

            foreach (JObject simulator in simulators.OfType<JObject>())
            {
                string simulatorId = RequiredString(simulator, "simulator", recordPath);
                JObject behavior = RequiredObject(simulator, "behavior", recordPath);

                // Guidance is the effective layer: authentic controls with this
                // simulator's explicit overrides applied. A car whose real gearbox
                // has no clutch pedal can still require clutch input in a given
                // simulator, and the driver needs the value that works in the sim.
                JObject effectiveControls = ApplyOverrides(controls, simulator, recordPath);
                JObject effectiveTransmission = RequiredObject(
                    effectiveControls, "transmission", recordPath);
                JObject effectiveSteering = RequiredObject(
                    effectiveControls, "steering", recordPath);
                JObject effectiveWheelRim = RequiredObject(
                    effectiveSteering, "wheel_rim", recordPath);
                JObject confidence = RequiredObject(simulator, "confidence", recordPath);
                JArray sourceRefs = simulator["source_refs"] as JArray;
                JArray simulatorIdentities = simulator["identities"] as JArray;
                if (simulatorIdentities == null)
                {
                    throw new InvalidDataException("Simulator entry has no identities: " + recordPath);
                }

                var entry = new MatchEntry
                {
                    DatasetVersion = datasetVersion,
                    RecordId = recordId,
                    DisplayName = RequiredString(identity, "display_name", recordPath),
                    CarClass = RequiredString(identity, "class", recordPath),
                    ShiftActuation = RequiredString(effectiveTransmission, "shift_actuation", recordPath),
                    ShiftPattern = RequiredString(effectiveTransmission, "shift_pattern", recordPath),
                    GearCount = OptionalInteger(effectiveTransmission, "forward_gears"),
                    UpshiftGuidance = DescribeShiftAction(
                        RequiredObject(effectiveTransmission, "upshift", recordPath), true),
                    DownshiftGuidance = DescribeShiftAction(
                        RequiredObject(effectiveTransmission, "downshift", recordPath), false),
                    TechniqueSummary = DescribeTechniqueSummary(effectiveTransmission, behavior),
                    StandingStartClutch = RequiredString(
                        effectiveTransmission, "standing_start_clutch", recordPath),
                    AutoBlip = RequiredString(behavior, "auto_blip", recordPath),
                    ShiftCut = RequiredString(behavior, "shift_cut", recordPath),
                    ManualBlip = RequiredString(
                        RequiredObject(effectiveTransmission, "downshift", recordPath),
                        "manual_blip",
                        recordPath),
                    ThrottleLift = RequiredString(
                        RequiredObject(effectiveTransmission, "upshift", recordPath),
                        "throttle_lift",
                        recordPath),
                    WheelRimShape = RequiredString(effectiveWheelRim, "shape", recordPath),
                    WheelRimSourceLabel = RequiredString(effectiveWheelRim, "source_label", recordPath),
                    HasSteeringDOR = effectiveSteering["degrees_of_rotation"] != null,
                    SteeringDOR = OptionalInteger(effectiveSteering, "degrees_of_rotation"),
                    VerifiedGameVersion = RequiredString(
                        simulator, "verified_game_version", recordPath),
                    Confidence = RequiredString(confidence, "level", recordPath),
                    SourceSummary = sourceRefs == null
                        ? string.Empty
                        : string.Join(", ", sourceRefs.Values<string>().ToArray())
                };
                entry.ShiftType = DescribeShiftType(entry.GearCount, entry.ShiftActuation);
                string recordKey = RecordKey(simulatorId, recordId);
                if (records.ContainsKey(recordKey))
                {
                    throw new InvalidDataException(
                        "Duplicate record and simulator pair '" + recordId + "' for "
                        + simulatorId + " in " + recordPath);
                }
                records[recordKey] = entry;
                cars.Add(new CarCatalogEntry(
                    recordId,
                    entry.DisplayName,
                    entry.CarClass,
                    simulatorId));

                foreach (JObject simulatorIdentity in simulatorIdentities.OfType<JObject>())
                {
                    string kind = RequiredString(simulatorIdentity, "kind", recordPath);
                    if (!MatchPriority.Contains(kind))
                    {
                        continue;
                    }
                    string value = RequiredString(simulatorIdentity, "value", recordPath);
                    string key = Key(simulatorId, kind, value);
                    MatchEntry existing;
                    if (identities.TryGetValue(key, out existing)
                        && existing.RecordId != entry.RecordId)
                    {
                        throw new InvalidDataException(
                            "Duplicate exact identity '" + value + "' for " + simulatorId
                            + " (" + kind + ") in " + recordPath);
                    }
                    identities[key] = entry;
                }
            }
        }

        /// <summary>
        /// Returns the authentic controls with this simulator's overrides applied.
        /// An override states an explicit, sourced deviation: the real car's value
        /// stays in the record, while guidance uses the value that is true in the
        /// simulator. Records without overrides are returned unchanged, so the
        /// common case costs nothing.
        /// </summary>
        private static JObject ApplyOverrides(
            JObject controls, JObject simulator, string recordPath)
        {
            JArray overrides = simulator["overrides"] as JArray;
            if (overrides == null || overrides.Count == 0)
            {
                return controls;
            }

            var effective = (JObject)controls.DeepClone();
            foreach (JObject entry in overrides.OfType<JObject>())
            {
                string path = RequiredString(entry, "path", recordPath);
                JToken value = entry["value"];
                if (value == null)
                {
                    throw new InvalidDataException(
                        "Override has no value: " + path + " in " + recordPath);
                }

                const string prefix = "/authentic_controls/";
                if (!path.StartsWith(prefix, StringComparison.Ordinal))
                {
                    // Only the authentic layer feeds guidance. Anything else is
                    // data for reviewers and must not silently change the popup.
                    continue;
                }

                string[] segments = path.Substring(prefix.Length).Split('/');
                JObject parent = effective;
                for (int index = 0; index < segments.Length - 1; index++)
                {
                    parent = parent[segments[index]] as JObject;
                    if (parent == null)
                    {
                        throw new InvalidDataException(
                            "Override path does not exist: " + path + " in " + recordPath);
                    }
                }
                string leaf = segments[segments.Length - 1];
                if (parent[leaf] == null)
                {
                    throw new InvalidDataException(
                        "Override path does not exist: " + path + " in " + recordPath);
                }
                parent[leaf] = value.DeepClone();
            }
            return effective;
        }

        private static string DescribeShiftType(int gears, string actuation)
        {
            string label;
            switch (actuation)
            {
                case "h-pattern": label = "H-pattern shifter"; break;
                case "sequential-stick": label = "sequential stick"; break;
                case "sequential-paddles": label = "paddle shifters"; break;
                case "automatic-lever": label = "automatic lever"; break;
                case "direct-selection": label = "direct selection"; break;
                default: label = "unknown shifter"; break;
            }
            return gears > 0 ? gears + "-speed " + label : label;
        }

        private static string DescribeShiftAction(JObject action, bool upshift)
        {
            var parts = new List<string>();
            AddRequirement(parts, RequiredString(action, "clutch", "shift action"), "clutch");
            if (upshift)
            {
                AddRequirement(
                    parts,
                    RequiredString(action, "throttle_lift", "shift action"),
                    "throttle lift");
                AddState(
                    parts,
                    RequiredString(action, "automatic_cut", "shift action"),
                    "automatic cut",
                    "no automatic cut");
            }
            else
            {
                AddState(
                    parts,
                    RequiredString(action, "automatic_blip", "shift action"),
                    "automatic blip",
                    "no automatic blip");
                AddRequirement(
                    parts,
                    RequiredString(action, "manual_blip", "shift action"),
                    "manual blip");
            }
            return parts.Count == 0 ? "Not applicable" : string.Join(" · ", parts.ToArray());
        }

        private static string DescribeTechniqueSummary(JObject transmission, JObject behavior)
        {
            var sentences = new List<string>();
            string startClutch = RequiredString(
                transmission, "standing_start_clutch", "transmission");
            switch (startClutch)
            {
                case "required": sentences.Add("Use the clutch to pull away."); break;
                case "not-required": sentences.Add("Pull away without clutch input."); break;
                case "anti-stall-available": sentences.Add("Anti-stall is available when pulling away."); break;
            }

            var actions = new List<string>();
            string actuation = RequiredString(transmission, "shift_actuation", "transmission");
            string pattern = RequiredString(transmission, "shift_pattern", "transmission");
            switch (actuation)
            {
                case "h-pattern":
                    actions.Add(pattern == "dogleg-h"
                        ? "use the dogleg H-pattern shifter"
                        : "use the H-pattern shifter");
                    break;
                case "sequential-stick": actions.Add("use the sequential stick"); break;
                case "sequential-paddles": actions.Add("shift with the paddles"); break;
                case "automatic-lever": actions.Add("use the automatic lever"); break;
                case "direct-selection": actions.Add("use direct gear selection"); break;
            }

            JObject upshift = RequiredObject(transmission, "upshift", "transmission");
            JObject downshift = RequiredObject(transmission, "downshift", "transmission");
            string upClutch = RequiredString(upshift, "clutch", "upshift");
            string downClutch = RequiredString(downshift, "clutch", "downshift");
            if (upClutch == "required" && downClutch == "required")
            {
                actions.Add("use the clutch for every shift");
            }
            else if (upClutch == "not-required" && downClutch == "not-required")
            {
                actions.Add("no clutch is needed once moving");
            }
            else
            {
                if (upClutch == "required") actions.Add("use the clutch on upshifts");
                if (downClutch == "required") actions.Add("use the clutch on downshifts");
            }

            string throttleLift = RequiredString(upshift, "throttle_lift", "upshift");
            string shiftCut = RequiredString(behavior, "shift_cut", "simulator behavior");
            if (throttleLift == "required")
            {
                actions.Add("lift the throttle on upshifts");
            }
            else if (throttleLift == "partial")
            {
                actions.Add("partially lift the throttle on upshifts");
            }
            else if (throttleLift == "not-required" && shiftCut == "yes")
            {
                actions.Add("keep the throttle down on upshifts (automatic cut)");
            }
            else if (throttleLift == "not-required")
            {
                actions.Add("upshift without lifting the throttle");
            }
            else if (shiftCut == "yes")
            {
                actions.Add("automatic throttle cut handles upshifts");
            }
            else if (throttleLift == "unknown")
            {
                // Say so rather than silently omitting upshift guidance. A
                // "not-applicable" lift (an automatic gearbox) correctly stays
                // silent because there is no upshift technique to describe.
                actions.Add("upshift throttle technique is not yet verified");
            }

            string automaticBlip = RequiredString(behavior, "auto_blip", "simulator behavior");
            string manualBlip = RequiredString(downshift, "manual_blip", "downshift");
            if (automaticBlip == "yes")
            {
                actions.Add("automatic throttle blip handles downshifts");
            }
            else if (manualBlip == "required")
            {
                actions.Add("blip the throttle on downshifts");
            }
            else if (manualBlip == "not-required")
            {
                actions.Add("no throttle blip is needed on downshifts");
            }
            else if (automaticBlip == "no")
            {
                actions.Add("manual downshift blip technique is not yet verified");
            }

            if (actions.Count > 0)
            {
                sentences.Add(SentenceCase(string.Join("; ", actions.ToArray())) + ".");
            }
            return sentences.Count == 0
                ? "Shifting technique is not yet verified."
                : string.Join(" ", sentences.ToArray());
        }

        private static void AddRequirement(List<string> parts, string value, string label)
        {
            switch (value)
            {
                case "required": parts.Add(SentenceCase(label + " required")); break;
                case "not-required": parts.Add(SentenceCase(label + " not required")); break;
                case "optional": parts.Add(SentenceCase(label + " optional")); break;
                case "partial": parts.Add(SentenceCase("partial " + label)); break;
                case "unknown": parts.Add(SentenceCase(label + " unknown")); break;
            }
        }

        private static void AddState(
            List<string> parts, string value, string yesLabel, string noLabel)
        {
            switch (value)
            {
                case "yes": parts.Add(SentenceCase(yesLabel)); break;
                case "no": parts.Add(SentenceCase(noLabel)); break;
                case "unknown": parts.Add(SentenceCase(yesLabel + " unknown")); break;
            }
        }

        private static string SentenceCase(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                return value;
            }
            return char.ToUpperInvariant(value[0]) + value.Substring(1);
        }

        private static JObject ReadObject(string path)
        {
            if (!File.Exists(path))
            {
                throw new FileNotFoundException("Database file not found.", path);
            }
            return JObject.Parse(File.ReadAllText(path));
        }

        private static string ResolveInside(string root, string relativePath)
        {
            if (string.IsNullOrWhiteSpace(relativePath))
            {
                throw new InvalidDataException("Dataset index contains an empty record path.");
            }
            string fullPath = Path.GetFullPath(
                Path.Combine(root, relativePath.Replace('/', Path.DirectorySeparatorChar)));
            string prefix = root.TrimEnd(Path.DirectorySeparatorChar)
                + Path.DirectorySeparatorChar;
            if (!fullPath.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    "Dataset record path escapes the data directory: " + relativePath);
            }
            return fullPath;
        }

        private static void RequireVersion(JObject value, string path)
        {
            string version = RequiredString(value, "schema_version", path);
            if (version != "1.0.0")
            {
                throw new InvalidDataException(
                    "Unsupported schema_version '" + version + "' in " + path);
            }
        }

        private static JObject RequiredObject(JObject value, string name, string path)
        {
            JObject child = value[name] as JObject;
            if (child == null)
            {
                throw new InvalidDataException("Missing object '" + name + "' in " + path);
            }
            return child;
        }

        private static string RequiredString(JObject value, string name, string path)
        {
            JToken token = value[name];
            string result = token == null ? null : token.Value<string>();
            if (string.IsNullOrEmpty(result))
            {
                throw new InvalidDataException("Missing string '" + name + "' in " + path);
            }
            return result;
        }

        private static int OptionalInteger(JObject value, string name)
        {
            JToken token = value[name];
            return token == null || token.Type == JTokenType.Null ? 0 : token.Value<int>();
        }

        private static string Key(string simulator, string kind, string value)
        {
            return simulator + "\u001f" + kind + "\u001f" + value;
        }

        private static string RecordKey(string simulator, string recordId)
        {
            return simulator + "\u001f" + recordId;
        }

        private static string SimulatorDisplayName(string simulator)
        {
            switch (simulator)
            {
                case "ams2": return "Automobilista2";
                case "iracing": return "iRacing";
                default: return simulator;
            }
        }

        private sealed class MatchEntry
        {
            public string DatasetVersion;
            public string RecordId;
            public string DisplayName;
            public string CarClass;
            public string ShiftType;
            public string ShiftActuation;
            public string ShiftPattern;
            public int GearCount;
            public string UpshiftGuidance;
            public string DownshiftGuidance;
            public string TechniqueSummary;
            public string StandingStartClutch;
            public string AutoBlip;
            public string ShiftCut;
            public string ManualBlip;
            public string ThrottleLift;
            public string WheelRimShape;
            public string WheelRimSourceLabel;
            public bool HasSteeringDOR;
            public int SteeringDOR;
            public string VerifiedGameVersion;
            public string Confidence;
            public string SourceSummary;

            public GuidanceSnapshot CreateSnapshot(
                string rawGameName, string rawCarIdentifier, string matchKind)
            {
                return GuidanceSnapshot.Matched(
                    rawGameName,
                    rawCarIdentifier,
                    DatasetVersion,
                    matchKind,
                    RecordId,
                    DisplayName,
                    CarClass,
                    ShiftType,
                    ShiftActuation,
                    ShiftPattern,
                    GearCount,
                    UpshiftGuidance,
                    DownshiftGuidance,
                    TechniqueSummary,
                    StandingStartClutch,
                    AutoBlip,
                    ShiftCut,
                    ManualBlip,
                    ThrottleLift,
                    WheelRimShape,
                    WheelRimSourceLabel,
                    HasSteeringDOR,
                    SteeringDOR,
                    VerifiedGameVersion,
                    Confidence,
                    SourceSummary);
            }
        }
    }
}
