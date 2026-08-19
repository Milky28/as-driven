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
        }

        public string RecordId { get; private set; }
        public string DisplayName { get; private set; }
        public string CarClass { get; private set; }
        public string Simulator { get; private set; }

        /// <summary>
        /// The car's name as the browser lists it. Curated names no longer carry
        /// an aero package, so there is nothing to strip and nothing that two
        /// entries could collide over: the name is the name.
        /// </summary>
        public string BrowserName
        {
            get { return DisplayName; }
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
