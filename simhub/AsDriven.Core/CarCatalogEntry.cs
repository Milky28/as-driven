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
        }

        public string RecordId { get; private set; }
        public string DisplayName { get; private set; }
        public string CarClass { get; private set; }
        public string Simulator { get; private set; }

        public string DisplayLabel
        {
            get
            {
                return string.IsNullOrWhiteSpace(CarClass)
                    ? DisplayName
                    : DisplayName + " — " + CarClass;
            }
        }

        public override string ToString()
        {
            return DisplayLabel;
        }
    }
}
