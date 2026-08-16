namespace AsDriven.Core
{
    public sealed class GuidanceSnapshot
    {
        public bool HasMatch { get; private set; }
        public string MatchStatus { get; private set; }
        public string RawGameName { get; private set; }
        public string RawCarIdentifier { get; private set; }
        public string DatasetVersion { get; private set; }
        public string RecordId { get; private set; }
        public string DisplayName { get; private set; }
        public string CarClass { get; private set; }
        public string ShiftType { get; private set; }
        public string ShiftActuation { get; private set; }
        public string ShiftPattern { get; private set; }
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
        public string StandingStartClutch { get; private set; }
        public string AutoBlip { get; private set; }
        public string ShiftCut { get; private set; }

        // What the driver must do, from authentic_controls after any simulator
        // override. AutoBlip and ShiftCut above describe what the simulator
        // does instead, and the two are not interchangeable: a car with no
        // automatic blip may still have an unknown manual blip.
        public string ManualBlip { get; private set; }
        public string ThrottleLift { get; private set; }
        public string WheelRimShape { get; private set; }
        public string WheelRimSourceLabel { get; private set; }

        /// <summary>
        /// The record's driver-facing note, empty when it carries none. The
        /// overlay hides its note panel entirely rather than showing a blank
        /// one, so an empty value is a supported state and not a defect.
        /// </summary>
        public string DriverSummary { get; private set; }

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

        /// <summary>Gear count and actuation, e.g. "5-speed H-pattern".</summary>
        public string ShifterLabel
        {
            get { return PreflightLabels.Shifter(GearCount, ShiftActuation); }
        }

        /// <summary>Where the gears sit, e.g. "Dogleg gate - 1st down and left".</summary>
        public string ShifterGateLabel
        {
            get { return PreflightLabels.Gate(ShiftActuation, ShiftPattern); }
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

        public string UpshiftTone
        {
            get { return PreflightLabels.UpshiftTone(ThrottleLift); }
        }

        public string DownshiftTone
        {
            get { return PreflightLabels.DownshiftTone(ManualBlip); }
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

        internal static GuidanceSnapshot Matched(
            string rawGameName,
            string rawCarIdentifier,
            string datasetVersion,
            string matchKind,
            string recordId,
            string displayName,
            string carClass,
            string shiftType,
            string shiftActuation,
            string shiftPattern,
            int gearCount,
            string upshiftGuidance,
            string downshiftGuidance,
            string techniqueSummary,
            string standingStartClutch,
            string autoBlip,
            string shiftCut,
            string manualBlip,
            string throttleLift,
            string wheelRimShape,
            string wheelRimSourceLabel,
            string driverSummary,
            string wheelIntegratedDisplay,
            string wheelShiftLights,
            bool hasSteeringDOR,
            int steeringDOR,
            string verifiedGameVersion,
            string confidence,
            string sourceSummary)
        {
            string[] techniqueLines = SplitTechniqueSummary(techniqueSummary);
            string[] compactTechniqueLines = SplitCompactTechniqueSummary(techniqueSummary);
            return new GuidanceSnapshot
            {
                HasMatch = true,
                MatchStatus = "matched",
                RawGameName = rawGameName,
                RawCarIdentifier = rawCarIdentifier,
                DatasetVersion = datasetVersion,
                MatchKind = matchKind,
                RecordId = recordId,
                DisplayName = displayName,
                CarClass = carClass,
                ShiftType = shiftType,
                ShiftActuation = shiftActuation,
                ShiftPattern = shiftPattern,
                GearCount = gearCount,
                UpshiftGuidance = upshiftGuidance,
                DownshiftGuidance = downshiftGuidance,
                TechniqueSummary = techniqueSummary,
                TechniqueSummaryLine1 = techniqueLines[0],
                TechniqueSummaryLine2 = techniqueLines[1],
                TechniqueSummaryCompactLine1 = compactTechniqueLines[0],
                TechniqueSummaryCompactLine2 = compactTechniqueLines[1],
                OverlayCarNameDetailed = FitSingleLine(displayName, 530, 2150),
                OverlayCarClassDetailed = FitSingleLine(carClass, 530, 1200),
                OverlayCarNameCompact = FitSingleLine(displayName, 300, 1750),
                OverlayCarClassCompact = FitSingleLine(carClass, 300, 950),
                OverlayCarNameGlance = FitSingleLine(displayName, 166, 1500),
                StandingStartClutch = standingStartClutch,
                AutoBlip = autoBlip,
                ShiftCut = shiftCut,
                ManualBlip = manualBlip,
                ThrottleLift = throttleLift,
                WheelRimShape = wheelRimShape,
                WheelRimSourceLabel = wheelRimSourceLabel,
                DriverSummary = driverSummary,
                WheelIntegratedDisplay = wheelIntegratedDisplay,
                WheelShiftLights = wheelShiftLights,
                HasSteeringDOR = hasSteeringDOR,
                SteeringDOR = steeringDOR,
                VerifiedGameVersion = verifiedGameVersion,
                Confidence = confidence,
                SourceSummary = sourceSummary,
                GuidanceSummary = displayName + " | " + techniqueSummary
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
                RecordId = string.Empty,
                DisplayName = string.Empty,
                CarClass = string.Empty,
                ShiftType = string.Empty,
                ShiftActuation = string.Empty,
                ShiftPattern = string.Empty,
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
                WheelRimShape = string.Empty,
                WheelRimSourceLabel = string.Empty,
                DriverSummary = string.Empty,
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
