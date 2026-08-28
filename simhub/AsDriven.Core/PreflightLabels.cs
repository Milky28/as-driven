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
        /// <summary>Established, with no question of who acts on it. Used where
        /// a line states a fact about the car rather than dividing work between
        /// the driver and the car.</summary>
        public const string ToneKnown = "known";

        // The aero package the simulator loaded is deliberately not shown and not
        // read. It is chosen by the circuit rather than by the driver, so it
        // changes no rim, no shifter and no technique, and a preflight card that
        // named it was answering a question nobody had to act on. A record now
        // declares its packages and every one of them resolves to the same
        // guidance, so there is nothing left to tell them apart with.

        public static string WheelRim(string shape)
        {
            return WheelRim(shape, "no");
        }

        public static string WheelRim(string shape, string openTop)
        {
            switch (shape)
            {
                case "round":
                    if (openTop == "yes") { return "Open-top round rim"; }
                    if (openTop == "unknown") { return "Round rim, top unknown"; }
                    return "Round rim";
                case "d-shaped":
                    if (openTop == "yes") { return "Open-top D-shaped rim"; }
                    if (openTop == "unknown") { return "D-shaped rim, top unknown"; }
                    return "D-shaped rim";
                // The three retired values still render, so an older installed
                // dataset shows the right words rather than "Unknown rim".
                case "gt-formula":
                case "gt-style":
                case "prototype":
                case "formula": return "GT / Formula rim";
                case "yoke": return "Open-top rim (legacy)";
                case "other": return "Unclassified rim (legacy)";
                default: return "Rim not recorded";
            }
        }

        /// <summary>
        /// What the rim carries, over two fields recorded independently.
        ///
        /// The two can be known separately, so the label says which half is
        /// missing rather than collapsing every gap into one sentence. It used
        /// to answer "Display not recorded" whenever shift lights were absent,
        /// which was wrong twice over: it denied a display that had been
        /// recorded, and where the display was a `yes` it read as a complete
        /// answer while silently dropping the lights.
        ///
        /// Kept inside the width the band allows - the longest string here is
        /// 26 characters, and the compact template clips beyond about thirty.
        /// </summary>
        public static string WheelFeatures(string display, string shiftLights)
        {
            bool displayKnown = display == "yes" || display == "no";
            bool lightsKnown = shiftLights == "yes" || shiftLights == "no";
            if (!displayKnown)
            {
                return "Display not recorded";
            }
            if (!lightsKnown)
            {
                return display == "yes" ? "Display, lights unknown" : "No display, lights unknown";
            }
            bool hasDisplay = display == "yes";
            bool hasLights = shiftLights == "yes";
            if (hasDisplay && hasLights) { return "Display and shift lights"; }
            if (hasDisplay) { return "Integrated display"; }
            if (hasLights) { return "Shift lights"; }
            return "No display or shift lights";
        }

        /// <summary>
        /// Whether the rim's display and shift-light state is established.
        ///
        /// The card greys only what is not known, which is the same rule the
        /// technique band follows: an optional blip reads in ordinary text
        /// because it is a decided fact. A rim that plainly carries neither a
        /// display nor shift lights is a decided fact too - it tells the driver
        /// to fit the plain rim rather than the one with a screen - so it must
        /// not be shown in the colour that means "no evidence".
        ///
        /// This matters more than it looks. The feature does not follow from the
        /// rim shape: GT / Formula rims split almost evenly on whether they
        /// carry a display, so the line is the only place a driver can learn it.
        /// </summary>
        public static string WheelFeatureTone(string display, string shiftLights)
        {
            bool displayKnown = display == "yes" || display == "no";
            bool lightsKnown = shiftLights == "yes" || shiftLights == "no";
            return displayKnown && lightsKnown ? ToneKnown : ToneUnknown;
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
