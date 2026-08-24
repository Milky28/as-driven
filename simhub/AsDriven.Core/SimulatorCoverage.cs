namespace AsDriven.Core
{
    /// <summary>
    /// A simulator the installed dataset actually carries records for. The list
    /// is derived from the loaded records rather than declared, so a simulator
    /// the matcher recognizes by name but has no data for is never advertised
    /// as supported.
    /// </summary>
    public sealed class SimulatorCoverage
    {
        internal SimulatorCoverage(string id, string displayName, int recordCount)
        {
            Id = id;
            DisplayName = displayName;
            RecordCount = recordCount;
        }

        public string Id { get; private set; }
        public string DisplayName { get; private set; }
        public int RecordCount { get; private set; }

        public string DisplayLabel
        {
            get
            {
                return DisplayName + " - " + RecordCount
                    + (RecordCount == 1 ? " car" : " cars");
            }
        }

        public override string ToString()
        {
            return DisplayLabel;
        }
    }
}
