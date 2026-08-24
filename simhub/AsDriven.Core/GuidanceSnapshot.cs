using System;
using System.Collections.Generic;
namespace AsDriven.Core
{
    public sealed class GuidanceSnapshot
    {
        public bool HasMatch { get; private set; }
        public string MatchStatus { get; private set; }
        public string RawGameName { get; private set; }
        public string RawCarIdentifier { get; private set; }
        public string DatasetVersion { get; private set; }
        public string SimulatorLabel { get; private set; }
        public string RecordId { get; private set; }
        public string DisplayName { get; private set; }
        public string CarClass { get; private set; }
        public string ShiftType { get; private set; }
        public string ShiftActuation { get; private set; }
        public string ShiftPattern { get; private set; }
        public string FirstGearPosition { get; private set; }
        public int GearCount { get; private set; }
        public string UpshiftGuidance { get; private set; }
        public string DownshiftGuidance { get; private set; }
        public string TechniqueSummary { get; private set; }
        public string TechniqueSummaryLine1 { get; private set; }
        public string TechniqueSummaryLine2 { get; private set; }
        public string TechniqueSummaryCompactLine1 { get; private set; }
        public string TechniqueSummaryCompactLine2 { get; private set; }
        // Overlay-specific text is deliberately pre-fitted in the core model. Dash
        // Studio text items do not offer reliable runtime trimming, so leaving this
        // to the dashboard would make long telemetry names clip at the right edge.
        public string OverlayCarNameDetailed { get; private set; }
        public string OverlayCarClassDetailed { get; private set; }
        public string OverlayCarNameCompact { get; private set; }
        public string OverlayCarClassCompact { get; private set; }
        public string OverlayCarNameGlance { get; private set; }

        /// <summary>The aero package AMS2 selected, empty when the car has none.</summary>
        public string StandingStartClutch { get; private set; }
        public string AutoBlip { get; private set; }
        public string ShiftCut { get; private set; }

        // What the driver must do, from authentic_controls after any simulator
        // override. AutoBlip and ShiftCut above describe what the simulator
        // does instead, and the two are not interchangeable: a car with no
        // automatic blip may still have an unknown manual blip.
        public string ManualBlip { get; private set; }
        public string ThrottleLift { get; private set; }

        /// <summary>Clutch requirement for a running upshift.</summary>
        public string UpshiftClutch { get; private set; }

        /// <summary>Clutch requirement for a running downshift.</summary>
        public string DownshiftClutch { get; private set; }
        public string WheelRimShape { get; private set; }
        public string WheelRimSourceLabel { get; private set; }

        /// <summary>
        /// The record's driver-facing note, empty when it carries none. The
        /// overlay hides its note panel entirely rather than showing a blank
        /// one, so an empty value is a supported state and not a defect.
        /// </summary>
        public string DriverSummary { get; private set; }

        /// <summary>
        /// JSON Pointer paths the simulator entry overrides, empty when the
        /// simulator matches the real car on every curated value.
        /// </summary>
        public string[] OverriddenPaths { get; private set; }

        /// <summary>
        /// Paths whose simulator observation fills a real-car field that the
        /// reviewed sources did not establish.
        /// </summary>
        public string[] UnestablishedPaths { get; private set; }

        /// <summary>The reviewer's stated reason for each override.</summary>
        public string SimulatorDifference { get; private set; }

        /// <summary>True when this simulator departs from the real car at all.</summary>
        public bool SimulatorDiffers
        {
            get { return OverriddenPaths != null && OverriddenPaths.Length > 0; }
        }

        private bool Overrides(string fragment)
        {
            if (OverriddenPaths == null) { return false; }
            foreach (string path in OverriddenPaths)
            {
                if (path != null && path.IndexOf(fragment, StringComparison.Ordinal) >= 0)
                {
                    return true;
                }
            }
            return false;
        }

        private bool IsUnestablished(string fragment)
        {
            if (UnestablishedPaths == null) { return false; }
            foreach (string path in UnestablishedPaths)
            {
                if (path != null && path.IndexOf(fragment, StringComparison.Ordinal) >= 0)
                {
                    return true;
                }
            }
            return false;
        }

        /// <summary>Gear count or actuation differ from the real car.</summary>
        public bool ShifterDiffers
        {
            get
            {
                return Overrides("/forward_gears")
                    || Overrides("/shift_actuation")
                    || Overrides("/shift_pattern");
            }
        }

        public bool LaunchDiffers
        {
            get { return Overrides("/standing_start_clutch"); }
        }

        public bool UpshiftDiffers
        {
            get { return Overrides("/upshift"); }
        }

        public bool DownshiftDiffers
        {
            get { return Overrides("/downshift"); }
        }

        public bool WheelDiffers
        {
            get { return Overrides("/wheel_rim"); }
        }

        public bool ShifterUnestablished
        {
            get
            {
                return IsUnestablished("/forward_gears")
                    || IsUnestablished("/shift_actuation")
                    || IsUnestablished("/shift_pattern");
            }
        }

        public bool LaunchUnestablished
        {
            get { return IsUnestablished("/standing_start_clutch"); }
        }

        public bool UpshiftUnestablished
        {
            get { return IsUnestablished("/upshift"); }
        }

        public bool DownshiftUnestablished
        {
            get { return IsUnestablished("/downshift"); }
        }

        public bool WheelUnestablished
        {
            get { return IsUnestablished("/wheel_rim"); }
        }

        // Dashboard text items do not wrap, so the summary is pre-broken here.
        public string DriverSummaryLine1 { get; private set; }
        public string DriverSummaryLine2 { get; private set; }
        public string DriverSummaryLine3 { get; private set; }
        public string DriverSummaryCompactLine1 { get; private set; }
        public string DriverSummaryCompactLine2 { get; private set; }
        public string DriverSummaryCompactLine3 { get; private set; }

        /// <summary>Whether the rim itself carries a readout. Optional in the
        /// schema, so an unobserved value reads "unknown", never "no".</summary>
        public string WheelIntegratedDisplay { get; private set; }

        /// <summary>Whether the rim carries shift or rev lights.</summary>
        public string WheelShiftLights { get; private set; }

        // ---- preflight card wording, derived from the values above ----

        /// <summary>Rim construction, as the card names it.</summary>
        public string WheelRimLabel
        {
            get { return PreflightLabels.WheelRim(WheelRimShape); }
        }

        /// <summary>What the rim carries, kept as text per the icon contract.</summary>
        public string WheelFeatureLabel
        {
            get { return PreflightLabels.WheelFeatures(WheelIntegratedDisplay, WheelShiftLights); }
        }

        /// <summary>Whether <see cref="WheelFeatureLabel"/> states a fact or a gap.</summary>
        public string WheelFeatureTone
        {
            get { return PreflightLabels.WheelFeatureTone(WheelIntegratedDisplay, WheelShiftLights); }
        }

        /// <summary>Gear count and actuation, e.g. "5-speed H-pattern".</summary>
        public string ShifterLabel
        {
            get { return PreflightLabels.Shifter(GearCount, ShiftActuation); }
        }

        /// <summary>Where the gears sit, e.g. "Dogleg gate - 1st down and left".</summary>
        public string ShifterGateLabel
        {
            get { return PreflightLabels.Gate(ShiftActuation, ShiftPattern, FirstGearPosition); }
        }

        public string LaunchLabel
        {
            get { return PreflightLabels.Launch(StandingStartClutch); }
        }

        public string UpshiftLabel
        {
            get { return PreflightLabels.Upshift(ThrottleLift, ShiftCut); }
        }

        public string DownshiftLabel
        {
            get { return PreflightLabels.Downshift(ManualBlip, AutoBlip); }
        }

        public string LaunchTone
        {
            get { return PreflightLabels.LaunchTone(StandingStartClutch); }
        }

        /// <summary>Whether the clutch is needed for a running upshift.</summary>
        public string UpshiftClutchLabel
        {
            get { return PreflightLabels.RunningClutch(UpshiftClutch); }
        }

        /// <summary>Whether the clutch is needed for a running downshift.</summary>
        public string DownshiftClutchLabel
        {
            get { return PreflightLabels.RunningClutch(DownshiftClutch); }
        }

        public string LaunchDetailLabel
        {
            get { return PreflightLabels.LaunchDetail(StandingStartClutch); }
        }

        public string UpshiftTone
        {
            get { return PreflightLabels.UpshiftTone(ThrottleLift, UpshiftClutch); }
        }

        public string DownshiftTone
        {
            get { return PreflightLabels.DownshiftTone(ManualBlip, DownshiftClutch); }
        }

        /// <summary>Tone for the whole USE band, and so for its rail.</summary>
        public string UseBandTone
        {
            get { return PreflightLabels.BandTone(LaunchTone, UpshiftTone, DownshiftTone); }
        }
        public bool HasSteeringDOR { get; private set; }
        public int SteeringDOR { get; private set; }
        public string VerifiedGameVersion { get; private set; }
        public string Confidence { get; private set; }
        public string SourceSummary { get; private set; }
        public string MatchKind { get; private set; }
        public string GuidanceSummary { get; private set; }
        public int PopupRevision { get; private set; }

        /// <summary>
        /// Builds a matched snapshot from one record's curated values.
        /// </summary>
        internal static GuidanceSnapshot Matched(
            CarRecordValues values,
            string rawGameName,
            string rawCarIdentifier,
            string matchKind)
        {
            string baseName = values.DisplayName;
            string classLine = values.CarClass;
            string[] techniqueLines = SplitTechniqueSummary(values.TechniqueSummary);
            string[] summaryLines = WrapLines(values.DriverSummary, 620, 1250, 3);
            string[] compactSummaryLines = WrapLines(values.DriverSummary, 432, 1100, 3);
            string[] compactTechniqueLines = SplitCompactTechniqueSummary(values.TechniqueSummary);
            return new GuidanceSnapshot
            {
                HasMatch = true,
                MatchStatus = "matched",
                RawGameName = rawGameName,
                RawCarIdentifier = rawCarIdentifier,
                DatasetVersion = values.DatasetVersion,
                SimulatorLabel = values.SimulatorLabel,
                MatchKind = matchKind,
                RecordId = values.RecordId,
                DisplayName = values.DisplayName,
                CarClass = values.CarClass,
                ShiftType = values.ShiftType,
                ShiftActuation = values.ShiftActuation,
                ShiftPattern = values.ShiftPattern,
                FirstGearPosition = values.FirstGearPosition,
                GearCount = values.GearCount,
                UpshiftGuidance = values.UpshiftGuidance,
                DownshiftGuidance = values.DownshiftGuidance,
                TechniqueSummary = values.TechniqueSummary,
                TechniqueSummaryLine1 = techniqueLines[0],
                TechniqueSummaryLine2 = techniqueLines[1],
                TechniqueSummaryCompactLine1 = compactTechniqueLines[0],
                TechniqueSummaryCompactLine2 = compactTechniqueLines[1],
                // The aero package moves to the class line: appended to the name
                // it pushed the car itself off the end of the card.
                OverlayCarNameDetailed = FitSingleLine(baseName, 530, 2150),
                OverlayCarClassDetailed = FitSingleLine(classLine, 530, 1200),
                OverlayCarNameCompact = FitSingleLine(baseName, 300, 1750),
                OverlayCarClassCompact = FitSingleLine(classLine, 300, 950),
                OverlayCarNameGlance = FitSingleLine(baseName, 166, 1500),
                StandingStartClutch = values.StandingStartClutch,
                AutoBlip = values.AutoBlip,
                ShiftCut = values.ShiftCut,
                ManualBlip = values.ManualBlip,
                ThrottleLift = values.ThrottleLift,
                UpshiftClutch = values.UpshiftClutch,
                DownshiftClutch = values.DownshiftClutch,
                WheelRimShape = values.WheelRimShape,
                WheelRimSourceLabel = values.WheelRimSourceLabel,
                DriverSummary = values.DriverSummary,
                OverriddenPaths = values.OverriddenPaths ?? new string[0],
                UnestablishedPaths = values.UnestablishedPaths ?? new string[0],
                SimulatorDifference = values.SimulatorDifference,
                DriverSummaryLine1 = summaryLines[0],
                DriverSummaryLine2 = summaryLines[1],
                DriverSummaryLine3 = summaryLines[2],
                DriverSummaryCompactLine1 = compactSummaryLines[0],
                DriverSummaryCompactLine2 = compactSummaryLines[1],
                DriverSummaryCompactLine3 = compactSummaryLines[2],
                WheelIntegratedDisplay = values.WheelIntegratedDisplay,
                WheelShiftLights = values.WheelShiftLights,
                HasSteeringDOR = values.HasSteeringDOR,
                SteeringDOR = values.SteeringDOR,
                VerifiedGameVersion = values.VerifiedGameVersion,
                Confidence = values.Confidence,
                SourceSummary = values.SourceSummary,
                GuidanceSummary = values.DisplayName + " | " + values.TechniqueSummary
            };
        }

        public static GuidanceSnapshot Empty(
            string status,
            string rawGameName,
            string rawCarIdentifier,
            string datasetVersion)
        {
            return new GuidanceSnapshot
            {
                HasMatch = false,
                MatchStatus = status,
                RawGameName = rawGameName ?? string.Empty,
                RawCarIdentifier = rawCarIdentifier ?? string.Empty,
                DatasetVersion = datasetVersion ?? string.Empty,
                SimulatorLabel = string.Empty,
                RecordId = string.Empty,
                DisplayName = string.Empty,
                CarClass = string.Empty,
                ShiftType = string.Empty,
                ShiftActuation = string.Empty,
                ShiftPattern = string.Empty,
                FirstGearPosition = string.Empty,
                GearCount = 0,
                UpshiftGuidance = string.Empty,
                DownshiftGuidance = string.Empty,
                TechniqueSummary = string.Empty,
                TechniqueSummaryLine1 = string.Empty,
                TechniqueSummaryLine2 = string.Empty,
                TechniqueSummaryCompactLine1 = string.Empty,
                TechniqueSummaryCompactLine2 = string.Empty,
                OverlayCarNameDetailed = string.Empty,
                OverlayCarClassDetailed = string.Empty,
                OverlayCarNameCompact = string.Empty,
                OverlayCarClassCompact = string.Empty,
                OverlayCarNameGlance = string.Empty,
                StandingStartClutch = string.Empty,
                AutoBlip = string.Empty,
                ShiftCut = string.Empty,
                ManualBlip = string.Empty,
                ThrottleLift = string.Empty,
                UpshiftClutch = string.Empty,
                DownshiftClutch = string.Empty,
                WheelRimShape = string.Empty,
                WheelRimSourceLabel = string.Empty,
                DriverSummary = string.Empty,
                OverriddenPaths = new string[0],
                UnestablishedPaths = new string[0],
                SimulatorDifference = string.Empty,
                DriverSummaryLine1 = string.Empty,
                DriverSummaryLine2 = string.Empty,
                DriverSummaryLine3 = string.Empty,
                DriverSummaryCompactLine1 = string.Empty,
                DriverSummaryCompactLine2 = string.Empty,
                DriverSummaryCompactLine3 = string.Empty,
                WheelIntegratedDisplay = string.Empty,
                WheelShiftLights = string.Empty,
                HasSteeringDOR = false,
                SteeringDOR = 0,
                VerifiedGameVersion = string.Empty,
                Confidence = string.Empty,
                SourceSummary = string.Empty,
                MatchKind = string.Empty,
                GuidanceSummary = string.Empty
            };
        }

        internal GuidanceSnapshot WithPopupRevision(int revision)
        {
            PopupRevision = revision;
            return this;
        }

        /// <summary>
        /// Wraps free text across a fixed number of lines. Dashboard text items
        /// do not wrap, so any paragraph the overlay shows has to be broken here
        /// and drawn one item per line. The last line ellipsises rather than
        /// clipping mid-word, so a summary is never cut off silently.
        /// </summary>
        private static string[] WrapLines(
            string value, int availableWidth, int fontSize, int maxLines)
        {
            value = Normalize(value);
            var lines = new List<string>();
            for (int index = 0; index < maxLines; index++)
            {
                if (value.Length == 0)
                {
                    lines.Add(string.Empty);
                    continue;
                }
                bool last = index == maxLines - 1;
                if (!last && Fits(value, availableWidth, fontSize))
                {
                    lines.Add(value);
                    value = string.Empty;
                    continue;
                }
                if (last)
                {
                    lines.Add(FitSingleLine(value, availableWidth, fontSize));
                    value = string.Empty;
                    continue;
                }
                int split = LastFittingBreak(value, availableWidth, fontSize);
                if (split <= 0)
                {
                    lines.Add(FitSingleLine(value, availableWidth, fontSize));
                    value = string.Empty;
                    continue;
                }
                lines.Add(value.Substring(0, split).TrimEnd());
                value = value.Substring(split + 1).TrimStart();
            }
            return lines.ToArray();
        }

        private static string[] SplitTechniqueSummary(string value)
        {
            return SplitTechniqueSummary(value, 756, 1350);
        }

        private static string[] SplitCompactTechniqueSummary(string value)
        {
            return SplitTechniqueSummary(value, 464, 950);
        }

        private static string[] SplitTechniqueSummary(
            string value,
            int availableWidth,
            int fontSize)
        {
            value = Normalize(value);
            if (Fits(value, availableWidth, fontSize))
            {
                return new[] { value, string.Empty };
            }

            int split = LastFittingBreak(value, availableWidth, fontSize);
            string first = split <= 0
                ? FitSingleLine(value, availableWidth, fontSize)
                : value.Substring(0, split).TrimEnd();
            string remainder = split <= 0
                ? string.Empty
                : value.Substring(split + 1).TrimStart();
            return new[]
            {
                first,
                FitSingleLine(remainder, availableWidth, fontSize)
            };
        }

        private static string FitSingleLine(string value, int availableWidth, int fontSize)
        {
            value = Normalize(value);
            if (Fits(value, availableWidth, fontSize))
            {
                return value;
            }

            const string ellipsis = "...";
            int lastBreak = LastFittingBreak(value, availableWidth - EstimatedWidth(ellipsis, fontSize), fontSize);
            if (lastBreak > 0)
            {
                return value.Substring(0, lastBreak).TrimEnd() + ellipsis;
            }

            int length = value.Length;
            while (length > 0 && !Fits(value.Substring(0, length) + ellipsis, availableWidth, fontSize))
            {
                length--;
            }
            return length == 0 ? ellipsis : value.Substring(0, length).TrimEnd() + ellipsis;
        }

        private static int LastFittingBreak(string value, int availableWidth, int fontSize)
        {
            int width = 0;
            int lastBreak = -1;
            for (int index = 0; index < value.Length; index++)
            {
                width += EstimatedWidth(value[index], fontSize);
                if (width > availableWidth)
                {
                    break;
                }
                if (char.IsWhiteSpace(value[index]))
                {
                    lastBreak = index;
                }
            }
            return lastBreak;
        }

        private static bool Fits(string value, int availableWidth, int fontSize)
        {
            return EstimatedWidth(value, fontSize) <= availableWidth;
        }

        // Values approximate Segoe UI's typographic advances with a modest safety
        // margin. They are stored in thousandths of an em; fontSize is expressed
        // in hundredths of a pixel. The previous deliberately loose upper bounds
        // left nearly half of the Detailed text row unused and could ellipsize a
        // sentence that fit comfortably across the available two lines.
        private static int EstimatedWidth(string value, int fontSize)
        {
            int width = 0;
            for (int index = 0; index < value.Length; index++)
            {
                width += EstimatedWidth(value[index], fontSize);
            }
            return width;
        }

        private static int EstimatedWidth(char value, int fontSize)
        {
            int units;
            if (char.IsWhiteSpace(value)) units = 300;
            else if ("ilI1|!.,:;'`".IndexOf(value) >= 0) units = 360;
            else if ("mwMW@#%&QO".IndexOf(value) >= 0) units = 1000;
            else if (char.IsUpper(value)) units = 800;
            else if (char.IsDigit(value)) units = 650;
            else if (char.IsPunctuation(value)) units = 500;
            else if (value > 127) units = 1000;
            else units = 600;
            return (units * fontSize + 99999) / 100000;
        }

        private static string Normalize(string value)
        {
            return (value ?? string.Empty).Trim();
        }
    }
}
