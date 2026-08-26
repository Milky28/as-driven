using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace AsDriven.Core
{
    public sealed class VerificationObservationDraft
    {
        public string Simulator { get; set; }
        /// <summary>
        /// What the telemetry client called the game, exactly as it arrived.
        /// Required when <see cref="Simulator"/> is "other": it is the only
        /// record of which game was driven, and without it one unregistered
        /// simulator cannot be told from another.
        /// </summary>
        public string SourceGameName { get; set; }
        public string GameVersion { get; set; }
        public string ClientVersion { get; set; }
        public string DatasetVersion { get; set; }
        public DateTime ObservedAtUtc { get; set; }
        public string Observer { get; set; }
        public string TelemetryName { get; set; }
        public string TelemetryClass { get; set; }
        public string InternalId { get; set; }
        public string AutomaticClutch { get; set; }
        public string AutomaticShifting { get; set; }
        public string AutomaticThrottleBlip { get; set; }
        public string AssistNotes { get; set; }
        public string MoveOffWithoutPhysicalClutch { get; set; }
        public int? ForwardGears { get; set; }
        public string DirectGearSelectionBehavior { get; set; }
        public string ClutchlessUpshift { get; set; }
        public string AutomaticCut { get; set; }
        public string AutomaticCutMethod { get; set; }
        public string ClutchlessDownshift { get; set; }
        public string AutomaticBlip { get; set; }
        public string AutomaticBlipMethod { get; set; }
        public string FullThrottleUpshift { get; set; }
        /// <summary>Which installed copy was driven; null when it could not be found.</summary>
        public CarImplementation Implementation { get; set; }
        public string CoastDownshift { get; set; }
        public string[] VisibleShiftActuators { get; set; }
        public string PrimaryShiftActuation { get; set; }
        public string ShiftPattern { get; set; }
        public string ActuationBasis { get; set; }
        public string WheelShape { get; set; }
        public string WheelIntegratedDisplay { get; set; }
        public string WheelShiftLights { get; set; }
        public string WheelOpenTop { get; set; }
        public string WheelNotes { get; set; }
        public string[] EvidenceNotes { get; set; }
    }

    public static class VerificationObservationWriter
    {
        private static readonly HashSet<string> ObservedStates = new HashSet<string>(
            new[] { "yes", "no", "unknown", "not-tested" },
            StringComparer.Ordinal);
        private static readonly HashSet<string> DirectSelectionStates = new HashSet<string>(
            new[] { "yes", "no", "unknown", "not-tested", "not-applicable" },
            StringComparer.Ordinal);
        private static readonly HashSet<string> AssistStates = new HashSet<string>(
            new[] { "enabled", "disabled", "unavailable", "unknown" },
            StringComparer.Ordinal);
        private static readonly HashSet<string> Simulators = new HashSet<string>(
            new[] { "ams2", "iracing", "ac", "acc", "ac-evo", "ac-rally", "raceroom", "rf2", "other" },
            StringComparer.Ordinal);
        private static readonly HashSet<string> ShiftActuations = new HashSet<string>(
            new[] { "h-pattern", "sequential-stick", "sequential-paddles", "automatic-lever", "direct-selection", "unknown" },
            StringComparer.Ordinal);
        private static readonly HashSet<string> ShiftPatterns = new HashSet<string>(
            new[] { "standard-h", "dogleg-h", "sequential", "automatic-gate", "direct", "unknown" },
            StringComparer.Ordinal);
        private static readonly HashSet<string> VisibleActuators = new HashSet<string>(
            new[] { "paddles", "sequential-stick", "h-pattern", "automatic-lever", "unknown" },
            StringComparer.Ordinal);
        private static readonly HashSet<string> WheelShapes = new HashSet<string>(
            // gt-style, prototype and formula are retired into gt-formula. They
            // stay accepted so a draft saved before the merge still loads.
            new[] { "round", "d-shaped", "gt-formula", "gt-style", "prototype", "formula", "yoke", "other", "unknown" },
            StringComparer.Ordinal);

        public static string WriteDraft(string directory, VerificationObservationDraft draft)
        {
            if (string.IsNullOrWhiteSpace(directory))
            {
                throw new ArgumentException("Observation directory is required.", "directory");
            }
            JObject payload = CreatePayload(draft);
            Directory.CreateDirectory(directory);
            string observationId = (string)payload["observation_id"];
            string path = Path.Combine(directory, observationId + ".json");
            using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
            using (var writer = new StreamWriter(stream))
            {
                writer.Write(payload.ToString(Formatting.Indented));
                writer.Write(Environment.NewLine);
            }
            return path;
        }

        /// <summary>
        /// Write a clearly marked public lead without personal attribution or
        /// installed-package identity. The original evidence file is untouched.
        /// Removing the implementation block deliberately makes a mod-capable
        /// simulator observation unsuitable for implementation-level promotion.
        /// </summary>
        public static string WriteRedactedCopy(string originalPath)
        {
            if (string.IsNullOrWhiteSpace(originalPath))
            {
                throw new ArgumentException("Observation path is required.", "originalPath");
            }
            string fullPath = Path.GetFullPath(originalPath);
            if (!File.Exists(fullPath))
            {
                throw new FileNotFoundException("Observation draft was not found.", fullPath);
            }
            JObject payload = JObject.Parse(File.ReadAllText(fullPath));
            payload["observer"] = "Anonymous";
            payload.Remove("implementation");
            const string disclosure =
                "Redacted public copy: observer attribution and the implementation block were removed. This copy is a research lead and may not support implementation-level promotion.";
            JArray notes = payload["evidence_notes"] as JArray;
            if (notes == null)
            {
                notes = new JArray();
                payload["evidence_notes"] = notes;
            }
            if (!notes.Any(item => string.Equals(
                (string)item,
                disclosure,
                StringComparison.Ordinal)))
            {
                notes.Add(disclosure);
            }
            string redactedPath = Path.Combine(
                Path.GetDirectoryName(fullPath),
                Path.GetFileNameWithoutExtension(fullPath) + ".redacted.json");
            using (var stream = new FileStream(
                redactedPath, FileMode.Create, FileAccess.Write, FileShare.Read))
            using (var writer = new StreamWriter(stream))
            {
                writer.Write(payload.ToString(Formatting.Indented));
                writer.Write(Environment.NewLine);
            }
            return redactedPath;
        }

        public static JObject CreatePayload(VerificationObservationDraft draft)
        {
            if (draft == null)
            {
                throw new ArgumentNullException("draft");
            }
            RequireText(draft.Simulator, "Simulator");
            RequireChoice(draft.Simulator, Simulators, "Simulator");
            if (string.Equals(draft.Simulator, "other", StringComparison.Ordinal))
            {
                RequireText(draft.SourceGameName, "SourceGameName");
            }
            RequireText(draft.GameVersion, "Game version");
            if (string.Equals(draft.GameVersion, "latest", StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException("Game version must be exact, not 'latest'.");
            }
            RequireText(draft.Observer, "Observer");
            RequireText(draft.TelemetryName, "Telemetry name");
            RequireText(draft.TelemetryClass, "Telemetry class");
            RequireChoice(draft.AutomaticClutch, AssistStates, "Automatic clutch state");
            RequireChoice(draft.AutomaticShifting, AssistStates, "Automatic shifting state");
            RequireChoice(draft.AutomaticThrottleBlip, AssistStates, "Automatic throttle-blip assist state");
            RequireChoice(draft.MoveOffWithoutPhysicalClutch, ObservedStates, "Move-off result");
            RequireChoice(draft.ClutchlessUpshift, ObservedStates, "Clutchless upshift result");
            RequireChoice(draft.DirectGearSelectionBehavior, DirectSelectionStates, "Direct gear-selection result");
            RequireChoice(draft.AutomaticCut, ObservedStates, "Automatic cut result");
            RequireChoice(draft.ClutchlessDownshift, ObservedStates, "Clutchless downshift result");
            RequireChoice(draft.AutomaticBlip, ObservedStates, "Automatic blip result");
            RequireChoice(draft.PrimaryShiftActuation, ShiftActuations, "Primary shift actuation");
            if (!string.IsNullOrWhiteSpace(draft.ShiftPattern))
            {
                RequireChoice(draft.ShiftPattern, ShiftPatterns, "Shift pattern");
            }
            RequireChoice(draft.WheelShape, WheelShapes, "Wheel shape");
            RequireChoice(draft.WheelIntegratedDisplay, ObservedStates, "Integrated-display result");
            RequireChoice(draft.WheelShiftLights, ObservedStates, "Shift-light result");
            RequireChoice(draft.WheelOpenTop, ObservedStates, "Open-top result");
            if (draft.ForwardGears.HasValue
                && (draft.ForwardGears.Value < 1 || draft.ForwardGears.Value > 20))
            {
                throw new InvalidDataException("Forward gears must be between 1 and 20.");
            }

            string[] visible = (draft.VisibleShiftActuators ?? new string[0])
                .Where(value => !string.IsNullOrWhiteSpace(value))
                .Distinct(StringComparer.Ordinal)
                .ToArray();
            foreach (string actuator in visible)
            {
                RequireChoice(actuator, VisibleActuators, "Visible shift actuator");
            }

            DateTime observedAt = draft.ObservedAtUtc == default(DateTime)
                ? DateTime.UtcNow
                : draft.ObservedAtUtc.ToUniversalTime();
            string observationId = CreateObservationId(
                draft.Simulator,
                draft.TelemetryName,
                observedAt);
            var identity = new JObject
            {
                { "telemetry_name", draft.TelemetryName.Trim() },
                { "telemetry_class", draft.TelemetryClass.Trim() }
            };
            AddOptional(identity, "internal_id", draft.InternalId);

            var assists = new JObject
            {
                { "automatic_clutch", draft.AutomaticClutch },
                { "automatic_shifting", draft.AutomaticShifting },
                { "automatic_throttle_blip", draft.AutomaticThrottleBlip }
            };
            AddOptional(assists, "notes", draft.AssistNotes);

            var tests = new JObject
            {
                { "move_off_without_physical_clutch", draft.MoveOffWithoutPhysicalClutch },
                { "forward_gears", draft.ForwardGears.HasValue ? new JValue(draft.ForwardGears.Value) : JValue.CreateNull() },
                { "direct_gear_selection_behavior", draft.DirectGearSelectionBehavior },
                { "clutchless_upshift", draft.ClutchlessUpshift },
                { "automatic_cut", draft.AutomaticCut },
                { "clutchless_downshift", draft.ClutchlessDownshift },
                { "automatic_blip", draft.AutomaticBlip }
            };
            AddOptional(tests, "full_throttle_upshift", draft.FullThrottleUpshift);
            AddOptional(tests, "coast_downshift", draft.CoastDownshift);
            AddOptional(tests, "automatic_cut_method", draft.AutomaticCutMethod);
            AddOptional(tests, "automatic_blip_method", draft.AutomaticBlipMethod);

            var wheel = new JObject
            {
                { "shape", draft.WheelShape },
                { "integrated_display", draft.WheelIntegratedDisplay },
                { "shift_lights", draft.WheelShiftLights },
                { "open_top", draft.WheelOpenTop }
            };
            AddOptional(wheel, "notes", draft.WheelNotes);
            var cockpit = new JObject
            {
                { "visible_shift_actuators", new JArray(visible) },
                { "primary_shift_actuation", draft.PrimaryShiftActuation },
                { "wheel_rim", wheel }
            };
            AddOptional(cockpit, "actuation_basis", draft.ActuationBasis);
            AddOptional(cockpit, "shift_pattern", draft.ShiftPattern);

            var payload = new JObject
            {
                { "$schema", "urn:as-driven:schema:v1:verification-observation" },
                { "schema_version", "1.0.0" },
                { "observation_id", observationId },
                { "simulator", draft.Simulator },
                { "game_version", draft.GameVersion.Trim() },
                { "observed_at", observedAt.ToString("o", CultureInfo.InvariantCulture) },
                { "observer", draft.Observer.Trim() },
                { "identity", identity },
                { "assists", assists },
                { "tests", tests },
                { "cockpit", cockpit },
                { "review_status", "draft" }
            };
            if (draft.Implementation != null)
            {
                var fingerprint = new JObject
                {
                    { "scope", draft.Implementation.Scope },
                    { "algorithm", "sha256" },
                    { "digest", draft.Implementation.Digest }
                };
                var implementation = new JObject
                {
                    { "content_id", draft.Implementation.ContentId },
                    { "fingerprint", fingerprint }
                };
                AddOptional(implementation, "author", draft.Implementation.Author);
                AddOptional(
                    implementation, "declared_version", draft.Implementation.DeclaredVersion);
                payload.Add("implementation", implementation);
            }
            AddOptional(payload, "source_game_name", draft.SourceGameName);
            AddOptional(payload, "client_version", draft.ClientVersion);
            AddOptional(payload, "dataset_version", draft.DatasetVersion);
            string[] notes = (draft.EvidenceNotes ?? new string[0])
                .Where(value => !string.IsNullOrWhiteSpace(value))
                .Select(value => value.Trim())
                .ToArray();
            if (notes.Length > 0)
            {
                payload.Add("evidence_notes", new JArray(notes));
            }
            return payload;
        }

        private static string CreateObservationId(
            string simulator,
            string telemetryName,
            DateTime observedAt)
        {
            string slug = new string(telemetryName.Trim().ToLowerInvariant()
                .Select(character =>
                    (character >= 'a' && character <= 'z')
                    || (character >= '0' && character <= '9')
                        ? character
                        : '-')
                .ToArray());
            while (slug.Contains("--"))
            {
                slug = slug.Replace("--", "-");
            }
            slug = slug.Trim('-');
            if (slug.Length == 0)
            {
                slug = "car";
            }
            if (slug.Length > 48)
            {
                slug = slug.Substring(0, 48).TrimEnd('-');
            }
            return simulator + "." + slug + "."
                + observedAt.ToString("yyyyMMddTHHmmssfff", CultureInfo.InvariantCulture).ToLowerInvariant()
                + "z-" + Guid.NewGuid().ToString("N").Substring(0, 8);
        }

        private static void AddOptional(JObject target, string name, string value)
        {
            if (!string.IsNullOrWhiteSpace(value))
            {
                target.Add(name, value.Trim());
            }
        }

        private static void RequireText(string value, string label)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                throw new InvalidDataException(label + " is required.");
            }
        }

        private static void RequireChoice(
            string value,
            HashSet<string> allowed,
            string label)
        {
            if (!allowed.Contains(value ?? string.Empty))
            {
                throw new InvalidDataException(label + " has an invalid value.");
            }
        }
    }
}
