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

        /// <summary>
        /// How a simulator spells an aero package on the end of a car's name.
        /// AMS2 picks the package from the circuit rather than from the driver,
        /// so one car reports several names; a record declares which packages it
        /// covers and the base name grows one key per package here, rather than
        /// every spelling being written out by hand.
        ///
        /// Nothing is rewritten at match time. The expansion happens once, while
        /// the database is read, and produces keys still compared byte for byte,
        /// so a name no record declares still fails to match rather than
        /// resolving to a neighbour. as_driven_db.validate holds the same table
        /// and its round-trip test pins these exact strings.
        /// </summary>
        private static readonly Dictionary<string, Dictionary<string, string>> AeroSuffixes =
            BuildAeroSuffixes();

        private static Dictionary<string, Dictionary<string, string>> BuildAeroSuffixes()
        {
            var ams2 = new Dictionary<string, string>(StringComparer.Ordinal);
            ams2["base"] = string.Empty;
            ams2["high-downforce"] = " - High Downforce";
            ams2["low-downforce"] = " - Low Downforce";
            ams2["speedway"] = " - Speedway";
            ams2["superspeedway"] = " - Superspeedway";

            var all = new Dictionary<string, Dictionary<string, string>>(StringComparer.Ordinal);
            all["ams2"] = ams2;
            return all;
        }

        private readonly Dictionary<string, CarRecordValues> _identities;
        private readonly Dictionary<string, CarRecordValues> _records;

        private AsDrivenDatabase(
            string dataDirectory,
            string datasetVersion,
            int recordCount,
            Dictionary<string, CarRecordValues> identities,
            Dictionary<string, CarRecordValues> records,
            CarCatalogEntry[] cars,
            SimulatorCoverage[] simulators)
        {
            DataDirectory = dataDirectory;
            DatasetVersion = datasetVersion;
            RecordCount = recordCount;
            _identities = identities;
            _records = records;
            Cars = cars;
            Simulators = simulators;
        }

        public string DataDirectory { get; private set; }
        public string DatasetVersion { get; private set; }
        public int RecordCount { get; private set; }
        public CarCatalogEntry[] Cars { get; private set; }

        /// <summary>
        /// The simulators this installed dataset can actually answer for, most
        /// covered first. Derived from the loaded records, never declared.
        /// </summary>
        public SimulatorCoverage[] Simulators { get; private set; }

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

            var identities = new Dictionary<string, CarRecordValues>(StringComparer.Ordinal);
            var recordsBySimulator = new Dictionary<string, CarRecordValues>(StringComparer.Ordinal);
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

            QualifyCollidingLabels(cars);
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
                cars.ToArray(),
                SummarizeSimulators(cars));
        }

        /// <summary>
        /// Name the simulator on entries that would otherwise read identically.
        ///
        /// The catalog holds one entry per simulator entry, so a real car curated
        /// from two games is listed twice - deliberately, because the guidance
        /// can differ between them. Two identical rows in a picker are useless
        /// though, so the ones that collide say which game they are for. Only
        /// those: a car covered by one simulator keeps the plain name, which is
        /// almost all of them.
        /// </summary>
        private static void QualifyCollidingLabels(List<CarCatalogEntry> cars)
        {
            var counts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            foreach (CarCatalogEntry car in cars)
            {
                int seen;
                counts.TryGetValue(car.DisplayLabel, out seen);
                counts[car.DisplayLabel] = seen + 1;
            }
            var collisions = new List<CarCatalogEntry>();
            foreach (CarCatalogEntry car in cars)
            {
                if (counts[car.DisplayLabel] > 1)
                {
                    collisions.Add(car);
                }
            }
            foreach (CarCatalogEntry car in collisions)
            {
                car.QualifyWith(SimulatorProductName(car.Simulator));
            }
        }

        /// <summary>
        /// Counts the curated records per simulator so the plugin can tell the
        /// user which games are covered before they start one.
        /// </summary>
        private static SimulatorCoverage[] SummarizeSimulators(List<CarCatalogEntry> cars)
        {
            var counts = new Dictionary<string, int>(StringComparer.Ordinal);
            foreach (CarCatalogEntry car in cars)
            {
                int existing;
                counts.TryGetValue(car.Simulator, out existing);
                counts[car.Simulator] = existing + 1;
            }

            var coverage = new List<SimulatorCoverage>();
            foreach (KeyValuePair<string, int> pair in counts)
            {
                coverage.Add(new SimulatorCoverage(
                    pair.Key, SimulatorProductName(pair.Key), pair.Value));
            }

            coverage.Sort(delegate(SimulatorCoverage left, SimulatorCoverage right)
            {
                int byCount = right.RecordCount.CompareTo(left.RecordCount);
                return byCount != 0
                    ? byCount
                    : string.Compare(
                        left.DisplayName, right.DisplayName, StringComparison.OrdinalIgnoreCase);
            });
            return coverage.ToArray();
        }

        public GuidanceSnapshot Match(string rawGameName, string rawCarIdentifier)
        {
            string simulator = CanonicalizeSimulator(rawGameName);
            // A name the matcher recognizes is not the same as a game this
            // dataset can answer for. Without the record check, a simulator with
            // no curated cars reports every car as unmatched instead of saying
            // plainly that the game is not covered yet.
            if (simulator == null || !IsCovered(simulator))
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
                CarRecordValues entry;
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
            CarRecordValues entry;
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

        /// <summary>
        /// True when the installed dataset carries at least one record for the
        /// SimHub game name, so the plugin can answer "will this work?" without
        /// the user starting the game.
        /// </summary>
        public bool Supports(string rawGameName)
        {
            string simulator = CanonicalizeSimulator(rawGameName);
            return simulator != null && IsCovered(simulator);
        }

        private bool IsCovered(string simulator)
        {
            foreach (SimulatorCoverage entry in Simulators)
            {
                if (string.Equals(entry.Id, simulator, StringComparison.Ordinal))
                {
                    return true;
                }
            }
            return false;
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
            // SimHub names these games "AssettoCorsa",
            // "AssettoCorsaCompetizione" and "AssettoCorsaEvo".
            // Each is compared whole rather than by prefix, so the three Assetto
            // Corsa titles - and Competizione, which this dataset does not cover
            // - never resolve into one another. They are separate games with
            // separate cars and separate names for the same car.
            if (compact == "assettocorsa" || compact == "ac")
            {
                return "ac";
            }
            if (compact == "assettocorsacompetizione" || compact == "acc")
            {
                return "acc";
            }
            if (compact == "assettocorsaevo" || compact == "acevo")
            {
                return "ac-evo";
            }
            // SimHub names RaceRoom by its engine, "RRRE", and detects the
            // process as RRRE64. Neither is the product name a driver would
            // recognise, so the spellings a person might reasonably supply are
            // accepted alongside them. "r3e" is the community abbreviation.
            if (compact == "rrre"
                || compact == "rrre64"
                || compact == "raceroom"
                || compact == "raceroomracingexperience"
                || compact == "r3e")
            {
                return "raceroom";
            }
            return null;
        }

        private static void IndexRecord(
            JObject record,
            string recordPath,
            string datasetVersion,
            Dictionary<string, CarRecordValues> identities,
            Dictionary<string, CarRecordValues> records,
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
                JObject simulatorWheelRim = RequiredObject(
                    behavior, "wheel_rim_type", recordPath);

                // Guidance is the effective layer: authentic controls with this
                // simulator's explicit overrides applied. A car whose real gearbox
                // has no clutch pedal can still require clutch input in a given
                // simulator, and the driver needs the value that works in the sim.
                string[] overriddenPaths;
                string[] unestablishedPaths;
                ClassifyOverrides(
                    controls,
                    simulator,
                    recordPath,
                    out overriddenPaths,
                    out unestablishedPaths);
                JObject effectiveControls = ApplyOverrides(controls, simulator, recordPath);
                JObject effectiveTransmission = RequiredObject(
                    effectiveControls, "transmission", recordPath);
                JObject effectiveSteering = RequiredObject(
                    effectiveControls, "steering", recordPath);
                JObject confidence = RequiredObject(simulator, "confidence", recordPath);
                JArray sourceRefs = simulator["source_refs"] as JArray;
                JArray simulatorIdentities = simulator["identities"] as JArray;
                if (simulatorIdentities == null)
                {
                    throw new InvalidDataException("Simulator entry has no identities: " + recordPath);
                }

                var entry = new CarRecordValues
                {
                    DatasetVersion = datasetVersion,
                    SimulatorLabel = SimulatorShortName(simulatorId),
                    RecordId = recordId,
                    // What this simulator calls the car. A renamed car is named
                    // differently by each game that renames it - the Prodrive
                    // Ferrari 550 is Milano GT55 in AMS2 and GT Ferruccio 55 V12
                    // in Assetto Corsa - and the record used to show one game's
                    // invention during the other's session.
                    DisplayName = OptionalText(simulator, "display_name").Length > 0
                        ? OptionalText(simulator, "display_name")
                        : RequiredString(identity, "display_name", recordPath),
                    // The record carries one class, and for a car with no real
                    // racing category that value is whichever simulator groups
                    // it - "Vintage Cars Tier 1" is what AMS2 calls the Miura.
                    // Assetto Corsa records no class for its cars at all, so
                    // showing the record's class there put an AMS2 grouping on
                    // an AC card. A simulator that states no class is shown none.
                    CarClass = OptionalText(simulator, "class").Length > 0
                        ? OptionalText(simulator, "class")
                        : HasClassIdentity(simulatorIdentities)
                            ? RequiredString(identity, "class", recordPath)
                            : string.Empty,
                    ShiftActuation = RequiredString(effectiveTransmission, "shift_actuation", recordPath),
                    ShiftPattern = RequiredString(effectiveTransmission, "shift_pattern", recordPath),
                    FirstGearPosition = OptionalState(effectiveTransmission, "first_gear_position"),
                    GearCount = OptionalInteger(effectiveTransmission, "forward_gears"),
                    UpshiftGuidance = DescribeShiftAction(
                        RequiredObject(effectiveTransmission, "upshift", recordPath), behavior, true),
                    DownshiftGuidance = DescribeShiftAction(
                        RequiredObject(effectiveTransmission, "downshift", recordPath), behavior, false),
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
                    UpshiftClutch = RequiredString(
                        RequiredObject(effectiveTransmission, "upshift", recordPath),
                        "clutch",
                        recordPath),
                    DownshiftClutch = RequiredString(
                        RequiredObject(effectiveTransmission, "downshift", recordPath),
                        "clutch",
                        recordPath),
                    // The behavior block is the reviewed cockpit implementation
                    // for this simulator. It can establish what the driver sees
                    // even when no real-car source establishes the authentic rim.
                    WheelRimShape = RequiredString(simulatorWheelRim, "normalized", recordPath),
                    WheelRimSourceLabel = RequiredString(simulatorWheelRim, "source_label", recordPath),
                    DriverSummary = OptionalText(record, "driver_summary"),
                    OverriddenPaths = overriddenPaths,
                    UnestablishedPaths = unestablishedPaths,
                    SimulatorDifference = DescribeOverrides(simulator, overriddenPaths),
                    WheelIntegratedDisplay = OptionalState(simulatorWheelRim, "integrated_display"),
                    WheelShiftLights = OptionalState(simulatorWheelRim, "shift_lights"),
                    // The steering lock lives on the simulator entry: every
                    // curated value for it came from the AMS2 spreadsheet, which
                    // records what the game applies rather than how the real car
                    // was built. The authentic path is still read so a record
                    // that one day sources a real lock is not ignored.
                    HasSteeringDOR = behavior["steering_dor"] != null
                        || effectiveSteering["degrees_of_rotation"] != null,
                    SteeringDOR = behavior["steering_dor"] != null
                        ? OptionalInteger(behavior, "steering_dor")
                        : OptionalInteger(effectiveSteering, "degrees_of_rotation"),
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
                    foreach (string expanded in ExpandIdentity(
                        simulatorId, kind, simulatorIdentity, value, recordPath))
                    {
                        string key = Key(simulatorId, kind, expanded);
                        CarRecordValues existing;
                        if (identities.TryGetValue(key, out existing)
                            && existing.RecordId != entry.RecordId)
                        {
                            throw new InvalidDataException(
                                "Duplicate exact identity '" + expanded + "' for " + simulatorId
                                + " (" + kind + ") in " + recordPath);
                        }
                        identities[key] = entry;
                    }
                }
            }
        }

        /// <summary>
        /// Separates confirmed simulator departures from observations that fill
        /// an unresolved real-car field. Both use the override representation so
        /// guidance can show the value that works in the simulator, but only the
        /// former may be described as unlike the real car.
        /// </summary>
        private static void ClassifyOverrides(
            JObject controls,
            JObject simulator,
            string recordPath,
            out string[] departures,
            out string[] unestablished)
        {
            JArray overrides = simulator["overrides"] as JArray;
            if (overrides == null || overrides.Count == 0)
            {
                departures = new string[0];
                unestablished = new string[0];
                return;
            }
            var departurePaths = new List<string>();
            var unestablishedPaths = new List<string>();
            foreach (JObject entry in overrides.OfType<JObject>())
            {
                string path = RequiredString(entry, "path", recordPath);
                JToken simulatorValue = entry["value"];
                if (simulatorValue == null)
                {
                    throw new InvalidDataException(
                        "Override has no value: " + path + " in " + recordPath);
                }

                JToken authenticValue = AuthenticValueAtPath(controls, path, recordPath);
                if (IsUnestablished(authenticValue))
                {
                    if (!IsUnestablished(simulatorValue))
                    {
                        unestablishedPaths.Add(path);
                    }
                }
                else if (!JToken.DeepEquals(authenticValue, simulatorValue))
                {
                    departurePaths.Add(path);
                }
            }
            departures = departurePaths.ToArray();
            unestablished = unestablishedPaths.ToArray();
        }

        private static bool IsUnestablished(JToken value)
        {
            return value == null
                || value.Type == JTokenType.Null
                || (value.Type == JTokenType.String
                    && string.Equals(
                        value.Value<string>(), "unknown", StringComparison.Ordinal));
        }

        private static JToken AuthenticValueAtPath(
            JObject controls, string path, string recordPath)
        {
            const string prefix = "/authentic_controls/";
            if (!path.StartsWith(prefix, StringComparison.Ordinal))
            {
                return null;
            }

            JToken current = controls;
            foreach (string segment in path.Substring(prefix.Length).Split('/'))
            {
                JObject parent = current as JObject;
                if (parent == null || parent[segment] == null)
                {
                    throw new InvalidDataException(
                        "Override path does not exist: " + path + " in " + recordPath);
                }
                current = parent[segment];
            }
            return current;
        }

        /// <summary>
        /// The reviewer's own words for why the simulator differs, taken from
        /// each override's condition. Never generated: if a record states no
        /// condition there is nothing to show.
        /// </summary>
        private static string DescribeOverrides(JObject simulator, string[] departurePaths)
        {
            JArray overrides = simulator["overrides"] as JArray;
            if (overrides == null || overrides.Count == 0)
            {
                return string.Empty;
            }
            var departures = new HashSet<string>(departurePaths, StringComparer.Ordinal);
            var conditions = new List<string>();
            foreach (JObject entry in overrides.OfType<JObject>())
            {
                JToken path = entry["path"];
                if (path == null || !departures.Contains(path.Value<string>()))
                {
                    continue;
                }
                JToken condition = entry["condition"];
                if (condition != null && condition.Type != JTokenType.Null)
                {
                    string text = condition.Value<string>();
                    if (!string.IsNullOrWhiteSpace(text))
                    {
                        conditions.Add(text.Trim());
                    }
                }
            }
            return string.Join(" ", conditions.ToArray());
        }

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

        private static string DescribeShiftAction(
            JObject action, JObject behavior, bool upshift)
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
                    RequiredString(behavior, "shift_cut", "simulator behavior"),
                    "automatic cut",
                    "no automatic cut");
            }
            else
            {
                AddState(
                    parts,
                    RequiredString(behavior, "auto_blip", "simulator behavior"),
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

        /// <summary>
        /// Reads an optional state field, returning "unknown" when the record
        /// does not carry it. The wheel modifiers are optional in the schema, so
        /// an absent value means it was never observed and must never be shown
        /// to the driver as a "no".
        /// </summary>
        /// <summary>Reads an optional free-text field, empty when absent.</summary>
        private static string OptionalText(JObject value, string name)
        {
            JToken token = value[name];
            return token == null || token.Type == JTokenType.Null
                ? string.Empty
                : token.Value<string>();
        }

        private static string OptionalState(JObject value, string name)
        {
            JToken token = value[name];
            return token == null || token.Type == JTokenType.Null
                ? "unknown"
                : token.Value<string>();
        }

        /// <summary>
        /// The exact names one declared identity stands for.
        ///
        /// An identity with no declared packages is a single literal string,
        /// which is what every record wrote before this existed and what a
        /// simulator that names its variants unsystematically still writes. A
        /// package this table does not know is a fault in the data rather than a
        /// name to guess at, so it throws instead of being skipped: skipping it
        /// would leave the car quietly unmatched at one kind of circuit.
        /// </summary>
        private static List<string> ExpandIdentity(
            string simulatorId,
            string kind,
            JObject simulatorIdentity,
            string value,
            string recordPath)
        {
            var expanded = new List<string>();
            JArray packages = simulatorIdentity["aero_packages"] as JArray;
            Dictionary<string, string> suffixes;
            if (packages == null
                || kind != "telemetry-name"
                || !AeroSuffixes.TryGetValue(simulatorId, out suffixes))
            {
                expanded.Add(value);
                return expanded;
            }

            foreach (JToken token in packages)
            {
                string package = token.Value<string>();
                string suffix;
                if (package == null || !suffixes.TryGetValue(package, out suffix))
                {
                    throw new InvalidDataException(
                        "Unknown aero package '" + package + "' for " + simulatorId
                        + " in " + recordPath);
                }
                expanded.Add(value + suffix);
            }
            return expanded;
        }

        /// <summary>Whether this simulator states a class for the car.</summary>
        private static bool HasClassIdentity(JArray identities)
        {
            foreach (JObject identity in identities.OfType<JObject>())
            {
                JToken kind = identity["kind"];
                if (kind != null && kind.Value<string>() == "class-id")
                {
                    return true;
                }
            }
            return false;
        }

        private static string Key(string simulator, string kind, string value)
        {
            return simulator + "\u001f" + kind + "\u001f" + value;
        }

        private static string RecordKey(string simulator, string recordId)
        {
            return simulator + "\u001f" + recordId;
        }

        /// <summary>
        /// The SimHub game name for a simulator. Matching and preview snapshots
        /// depend on this exact spelling; use <see cref="SimulatorProductName"/>
        /// for anything shown to the user.
        /// </summary>
        private static string SimulatorDisplayName(string simulator)
        {
            switch (simulator)
            {
                case "ams2": return "Automobilista2";
                case "iracing": return "iRacing";
                case "ac": return "AssettoCorsa";
                case "acc": return "AssettoCorsaCompetizione";
                case "ac-evo": return "AssettoCorsaEvo";
                case "raceroom": return "RRRE";
                default: return simulator;
            }
        }

        /// <summary>
        /// The simulator's real product name, for display only.
        /// </summary>
        private static string SimulatorProductName(string simulator)
        {
            switch (simulator)
            {
                case "ams2": return "Automobilista 2";
                case "iracing": return "iRacing";
                case "ac": return "Assetto Corsa";
                case "acc": return "Assetto Corsa Competizione";
                case "ac-evo": return "Assetto Corsa EVO";
                case "raceroom": return "RaceRoom Racing Experience";
                default: return simulator;
            }
        }

        private static string SimulatorShortName(string simulator)
        {
            switch (simulator)
            {
                case "ams2": return "AMS2";
                case "iracing": return "iRacing";
                case "ac": return "AC";
                case "acc": return "ACC";
                case "ac-evo": return "AC EVO";
                case "raceroom": return "RaceRoom";
                default: return simulator;
            }
        }
    }
}
