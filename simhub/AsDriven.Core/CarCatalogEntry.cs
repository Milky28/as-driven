namespace AsDriven.Core
{
    public sealed class CarCatalogEntry
    {
        internal CarCatalogEntry(
            string recordId,
            string displayName,
            string carClass,
            string simulator)
        {
            RecordId = recordId;
            DisplayName = displayName;
            CarClass = carClass;
            Simulator = simulator;
            // Assume the package is not needed until the catalog proves it is.
            ShowAeroPackage = false;
        }

        public string RecordId { get; private set; }
        public string DisplayName { get; private set; }
        public string CarClass { get; private set; }
        public string Simulator { get; private set; }

        /// <summary>
        /// Whether this entry has to name its aero package to stay distinct.
        /// AMS2 appends the package to 60 of the curated names, and repeating it
        /// down a browser list is noise unless two entries would otherwise read
        /// the same. The catalog decides this once, when it is built.
        /// </summary>
        public bool ShowAeroPackage { get; internal set; }

        /// <summary>The car's name, without its aero package unless it needs it.</summary>
        public string BrowserName
        {
            get
            {
                return ShowAeroPackage
                    ? DisplayName
                    : PreflightLabels.BaseName(DisplayName);
            }
        }

        public string DisplayLabel
        {
            get
            {
                return string.IsNullOrWhiteSpace(CarClass)
                    ? BrowserName
                    : BrowserName + " — " + CarClass;
            }
        }

        public override string ToString()
        {
            return DisplayLabel;
        }
    }
}
