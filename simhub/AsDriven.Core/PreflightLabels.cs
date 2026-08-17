using System;

namespace AsDriven.Core
{
    /// <summary>
    /// The wording the preflight card shows, and the tone that decides its
    /// colour. These live here rather than in dashboard expressions so the
    /// phrasing is asserted in tests instead of buried in a formula string, and
    /// so every surface says the same thing.
    ///
    /// The tone answers one question per moment: is this the driver's job. It
    /// deliberately has three answers. "unknown" is not a quiet "car" - an
    /// optional or unrecorded value must never render as though the car handles
    /// it, because that would turn a gap in the evidence into an instruction.
    /// </summary>
    public static class PreflightLabels
    {
        public const string ToneDriver = "you";
        public const string ToneCar = "car";
        /// <summary>Established, and the driver's choice. Distinct from
        /// <see cref="ToneUnknown"/>: an optional blip is a decided fact, not a
        /// gap in the evidence, and must not be shown as though it were.</summary>
        public const string ToneOptional = "optional";
        public const string ToneUnknown = "unknown";

        /// <summary>
        /// The aero packages AMS2 appends to a car's name. The simulator picks
        /// these from the circuit rather than the driver, so which one is loaded
        /// is worth showing - but appended to a name it pushes the car itself
        /// off the end of the card.
        /// </summary>
        private static readonly string[] AeroPackages =
        {
            "High Downforce", "Low Downforce", "Superspeedway", "Speedway"
        };

        /// <summary>The aero package in a display name, or empty when it carries none.</summary>
        public static string AeroPackage(string displayName)
        {
            if (string.IsNullOrEmpty(displayName)) { return string.Empty; }
            foreach (string package in AeroPackages)
            {
                if (displayName.EndsWith(" - " + package, StringComparison.Ordinal))
                {
                    return package;
                }
            }
            return string.Empty;
        }

        /// <summary>
        /// The aero package of the car that was actually loaded.
        ///
        /// One record is the exact identity for several aero configurations -
        /// the Reynard 98i covers the base car, High Downforce, Speedway and
        /// Superspeedway - so reading the package off the record's own name
        /// told a Speedway driver they were in the High Downforce car, and told
        /// a Low Downforce driver nothing at all. A name-shaped match carries
        /// the package the driver loaded, and its silence is meaningful: the
        /// base car has none. An opaque match has no name to read, so it falls
        /// back to the record, which is the best the record can say.
        /// </summary>
        public static string MatchedAeroPackage(
            string matchKind, string rawCarIdentifier, string displayName)
        {
            if (matchKind == "telemetry-name"
                || matchKind == "display-name"
                || matchKind == "alias")
            {
                return AeroPackage(rawCarIdentifier);
            }
            return AeroPackage(displayName);
        }

        /// <summary>The car's name without its aero package.</summary>
        public static string BaseName(string displayName)
        {
            string package = AeroPackage(displayName);
            return package.Length == 0
                ? displayName
                : displayName.Substring(0, displayName.Length - package.Length - 3);
        }

        /// <summary>
        /// The line under the car's name: its aero package where it has one,
        /// then the class the simulator reports.
        /// </summary>
        public static string ClassLine(string aeroPackage, string carClass)
        {
            string package = aeroPackage ?? string.Empty;
            if (package.Length == 0) { return carClass; }
            return string.IsNullOrEmpty(carClass)
                ? package
                : package + "  -  " + carClass;
        }

        public static string WheelRim(string shape)
        {
            switch (shape)
            {
                case "round": return "Round rim";
                case "d-shaped": return "D-shaped rim";
                // The three retired values still render, so an older installed
                // dataset shows the right words rather than "Unknown rim".
                case "gt-formula":
                case "gt-style":
                case "prototype":
                case "formula": return "GT / Formula rim";
                case "yoke": return "Yoke";
                case "other": return "Other rim";
                default: return "Rim not recorded";
            }
        }

        public static string WheelFeatures(string display, string shiftLights)
        {
            bool hasDisplay = display == "yes";
            bool hasLights = shiftLights == "yes";
            if (hasDisplay && hasLights) { return "Display and shift lights"; }
            if (hasDisplay) { return "Integrated display"; }
            if (hasLights) { return "Shift lights"; }
            if (display == "no" && shiftLights == "no") { return "No display or shift lights"; }
            return "Display not recorded";
        }

        public static string Shifter(int gears, string actuation)
        {
            string label;
            switch (actuation)
            {
                case "h-pattern": label = "H-pattern"; break;
                case "sequential-stick": label = "sequential"; break;
                case "sequential-paddles": label = "paddles"; break;
                case "automatic-lever": label = "automatic"; break;
                case "direct-selection": label = "direct select"; break;
                default: label = "shifter not recorded"; return label;
            }
            return gears > 0 ? gears + "-speed " + label : label;
        }

        public static string Gate(string actuation, string pattern)
        {
            return Gate(actuation, pattern, "unknown");
        }

        /// <summary>
        /// A dogleg only establishes that first sits outside the racing plane. Which
        /// side is a separate fact - the McLaren MP4/4 mirrors it - so the side is
        /// stated only when the record records it, never assumed from the pattern.
        /// </summary>
        public static string Gate(string actuation, string pattern, string firstGearPosition)
        {
            if (pattern == "dogleg-h")
            {
                if (firstGearPosition == "down-left") { return "Dogleg gate - 1st down and left"; }
                if (firstGearPosition == "down-right") { return "Dogleg gate - 1st down and right"; }
                return "Dogleg gate - 1st outside the plane";
            }
            if (pattern == "standard-h")
            {
                if (firstGearPosition == "up-right") { return "Standard gate - 1st up and right"; }
                if (firstGearPosition == "down-left") { return "Standard gate - 1st down and left"; }
                return "Standard gate - 1st up and left";
            }
            if (actuation == "sequential-paddles") { return "Sequential - one gear at a time"; }
            if (actuation == "sequential-stick") { return "Fore and aft - one gear at a time"; }
            if (pattern == "sequential") { return "Sequential - one gear at a time"; }
            if (pattern == "automatic-gate") { return "Automatic gate"; }
            if (pattern == "direct") { return "Direct selection"; }
            return "Gate not recorded";
        }

        public static string Launch(string standingStartClutch)
        {
            switch (standingStartClutch)
            {
                case "required": return "Clutch required";
                case "not-required": return "No clutch needed";
                case "anti-stall-available": return "Anti-stall fitted";
                case "not-applicable": return "No clutch fitted";
                default: return "Not established";
            }
        }

        public static string LaunchTone(string standingStartClutch)
        {
            switch (standingStartClutch)
            {
                case "required": return ToneDriver;
                case "not-required":
                case "not-applicable": return ToneCar;
                default: return ToneUnknown;
            }
        }

        /// <summary>
        /// Whether the clutch is needed for a shift already under way. Always
        /// shown, even though it is "not required" on almost every car: without
        /// it the driver cannot tell a clutch-free gearbox from one nobody
        /// checked, and those are different facts.
        /// </summary>
        public static string RunningClutch(string clutch)
        {
            switch (clutch)
            {
                case "required": return "Clutch required";
                case "optional": return "Clutch optional";
                case "not-required": return "No clutch needed";
                case "not-applicable": return "No clutch fitted";
                default: return "Clutch not established";
            }
        }

        /// <summary>The launch cell's second line, empty when there is nothing
        /// further the record establishes.</summary>
        public static string LaunchDetail(string standingStartClutch)
        {
            return standingStartClutch == "anti-stall-available"
                ? "Anti-stall will catch it"
                : string.Empty;
        }

        public static string Upshift(string throttleLift, string automaticCut)
        {
            switch (throttleLift)
            {
                case "required": return "Lift the throttle";
                case "partial": return "Part lift";
                case "not-required":
                    return automaticCut == "yes" ? "Stay flat - car cuts" : "Stay flat";
                case "not-applicable": return "Nothing to do";
                default: return "Not established";
            }
        }

        public static string UpshiftTone(string throttleLift, string clutch)
        {
            if (clutch == "required") { return ToneDriver; }
            switch (throttleLift)
            {
                case "required":
                case "partial": return ToneDriver;
                case "not-required":
                case "not-applicable": return ToneCar;
                default: return ToneUnknown;
            }
        }

        public static string Downshift(string manualBlip, string automaticBlip)
        {
            switch (manualBlip)
            {
                case "required": return "Blip - rev-match";
                // Optional is its own answer. Rounding it up to "required" would
                // invent an instruction; rounding it down to "no blip needed"
                // would lose authentic technique the record deliberately keeps.
                case "optional": return "Blip optional";
                case "not-required":
                    return automaticBlip == "yes" ? "Car blips for you" : "No blip needed";
                case "not-applicable": return "Nothing to do";
                default: return "Not established";
            }
        }

        public static string DownshiftTone(string manualBlip, string clutch)
        {
            if (clutch == "required") { return ToneDriver; }
            switch (manualBlip)
            {
                case "required": return ToneDriver;
                case "optional": return ToneOptional;
                case "not-required":
                case "not-applicable": return ToneCar;
                default: return ToneUnknown;
            }
        }

        /// <summary>
        /// The tone for the whole USE band. Orange the moment any single moment
        /// needs the driver, because a band that reads "handled" while one of
        /// its cells does not is the one failure worth avoiding.
        /// </summary>
        public static string BandTone(string launchTone, string upshiftTone, string downshiftTone)
        {
            if (launchTone == ToneDriver || upshiftTone == ToneDriver || downshiftTone == ToneDriver)
            {
                return ToneDriver;
            }
            if (launchTone == ToneUnknown || upshiftTone == ToneUnknown
                || downshiftTone == ToneUnknown)
            {
                return ToneUnknown;
            }
            // Optional actions are not demanded of the driver, so a band whose
            // only outstanding item is optional still reads as handled.
            return ToneCar;
        }
    }
}
