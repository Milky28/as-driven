namespace AsDriven.Core
{
    /// <summary>
    /// The curated values read from one record for one simulator, held together
    /// so they can be passed as a single object.
    ///
    /// These used to travel as more than thirty positional arguments, nearly all
    /// of them strings. Inserting a field in the wrong place there compiled
    /// cleanly and silently wrote one value into another - a driver summary was
    /// read as a rim shape once, and a clutch value landed two positions out.
    /// Named assignment makes that class of mistake impossible: a field can only
    /// go where its name says.
    /// </summary>
    internal sealed class CarRecordValues
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
        public string UpshiftClutch;
        public string DownshiftClutch;
        public string DriverSummary;
        public string[] OverriddenPaths;
        public string SimulatorDifference;
        public string WheelRimShape;
        public string WheelRimSourceLabel;
        public string WheelIntegratedDisplay;
        public string WheelShiftLights;
        public bool HasSteeringDOR;
        public int SteeringDOR;
        public string VerifiedGameVersion;
        public string Confidence;
        public string SourceSummary;

        public GuidanceSnapshot CreateSnapshot(
            string rawGameName, string rawCarIdentifier, string matchKind)
        {
            return GuidanceSnapshot.Matched(this, rawGameName, rawCarIdentifier, matchKind);
        }
    }
}
