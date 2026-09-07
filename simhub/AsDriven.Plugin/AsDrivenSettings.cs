using System.Collections.Generic;

namespace AsDriven.Plugin
{
    public sealed class VerificationAssistProfile
    {
        public string AutomaticClutch { get; set; }
        public string AutomaticShifting { get; set; }
        public string AutomaticThrottleBlip { get; set; }
        public bool Confirmed { get; set; }

        public VerificationAssistProfile()
        {
            AutomaticClutch = "unknown";
            AutomaticShifting = "unknown";
            AutomaticThrottleBlip = "unknown";
        }
    }

    /// <summary>Driver-declared equipment, kept local and separate from car evidence.</summary>
    public sealed class HardwareProfile
    {
        public bool Configured { get; set; }
        public bool RoundRim { get; set; }
        public bool GtFormulaRim { get; set; }
        public bool HPattern { get; set; }
        /// <summary>Legacy combined selection, retained only to migrate saved settings.</summary>
        public bool Sequential { get; set; }
        public bool SequentialStick { get; set; }
        public bool PaddleShifters { get; set; }
        public bool ClutchPedal { get; set; }
    }

    public sealed class AsDrivenSettings
    {
        public double PopupDurationSeconds { get; set; }
        public string PopupSize { get; set; }
        public string PopupTheme { get; set; }
        public string VerificationObserver { get; set; }
        /// <summary>
        /// Where the manual update check looks. Shipped pre-filled so the
        /// feature is discoverable, and still inert until the driver presses the
        /// button: nothing contacts it on a timer, at startup, or after an
        /// install. An empty legacy setting falls back to this shipped address.
        /// </summary>
        public const string DefaultUpdateCheckUrl =
            "https://raw.githubusercontent.com/Milky28/as-driven/main/as-driven-latest.json";

        public string UpdateCheckUrl { get; set; }
        public string LastUpdateCheckSummary { get; set; }
        public string LastUpdateCheckUtc { get; set; }
        public List<string> FavoriteCatalogCars { get; set; }
        public List<string> RecentCatalogCars { get; set; }
        public HardwareProfile MyHardware { get; set; }
        public Dictionary<string, VerificationAssistProfile> VerificationAssistProfiles { get; set; }
        /// <summary>Observed physical inputs for the four guided-drive actions.</summary>
        public Dictionary<string, string> GuidedDriveBindings { get; set; }

        public AsDrivenSettings()
        {
            PopupDurationSeconds = 10.0;
            PopupSize = "detailed";
            PopupTheme = "auto";
            VerificationObserver = string.Empty;
            UpdateCheckUrl = DefaultUpdateCheckUrl;
            LastUpdateCheckSummary = string.Empty;
            LastUpdateCheckUtc = string.Empty;
            FavoriteCatalogCars = new List<string>();
            RecentCatalogCars = new List<string>();
            MyHardware = new HardwareProfile();
            VerificationAssistProfiles = new Dictionary<string, VerificationAssistProfile>();
            GuidedDriveBindings = new Dictionary<string, string>();
        }
    }
}
