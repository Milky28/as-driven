namespace AuthenticControls.Core
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
        public string StandingStartClutch { get; private set; }
        public string AutoBlip { get; private set; }
        public string ShiftCut { get; private set; }
        public string WheelRimShape { get; private set; }
        public string WheelRimSourceLabel { get; private set; }
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
            string wheelRimShape,
            string wheelRimSourceLabel,
            bool hasSteeringDOR,
            int steeringDOR,
            string verifiedGameVersion,
            string confidence,
            string sourceSummary)
        {
            string[] techniqueLines = SplitTechniqueSummary(techniqueSummary);
            string[] compactTechniqueLines = SplitCompactTechniqueSummary(
                techniqueSummary);
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
                StandingStartClutch = standingStartClutch,
                AutoBlip = autoBlip,
                ShiftCut = shiftCut,
                WheelRimShape = wheelRimShape,
                WheelRimSourceLabel = wheelRimSourceLabel,
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
                StandingStartClutch = string.Empty,
                AutoBlip = string.Empty,
                ShiftCut = string.Empty,
                WheelRimShape = string.Empty,
                WheelRimSourceLabel = string.Empty,
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
            return SplitTechniqueSummary(value, 145, 120, 85);
        }

        private static string[] SplitCompactTechniqueSummary(string value)
        {
            return SplitTechniqueSummary(value, 112, 110, 80);
        }

        private static string[] SplitTechniqueSummary(
            string value,
            int singleLineLength,
            int targetLength,
            int minimumSplit)
        {
            value = value ?? string.Empty;
            if (value.Length <= singleLineLength)
            {
                return new[] { value, string.Empty };
            }

            int split = value.LastIndexOf(' ', targetLength);
            if (split < minimumSplit)
            {
                split = value.IndexOf(' ', targetLength);
            }
            if (split <= 0)
            {
                return new[] { value, string.Empty };
            }
            return new[]
            {
                value.Substring(0, split).TrimEnd(),
                value.Substring(split + 1).TrimStart()
            };
        }
    }
}
