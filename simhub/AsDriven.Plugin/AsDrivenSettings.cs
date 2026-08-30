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

    public sealed class AsDrivenSettings
    {
        public double PopupDurationSeconds { get; set; }
        public string PopupSize { get; set; }
        public string PopupTheme { get; set; }
        public string VerificationObserver { get; set; }
        /// <summary>
        /// Where "Check for updates" looks, and the switch that decides whether
        /// the plugin may reach the network at all.
        ///
        /// Empty by default, and empty means no request is ever made. The check
        /// is manual in every case - there is no timer and nothing runs at
        /// startup - so an installation nobody configures behaves exactly as
        /// the privacy note describes: no network feature.
        /// </summary>
        public string UpdateCheckUrl { get; set; }
        public Dictionary<string, VerificationAssistProfile> VerificationAssistProfiles { get; set; }

        public AsDrivenSettings()
        {
            PopupDurationSeconds = 10.0;
            PopupSize = "detailed";
            PopupTheme = "auto";
            VerificationObserver = string.Empty;
            UpdateCheckUrl = string.Empty;
            VerificationAssistProfiles = new Dictionary<string, VerificationAssistProfile>();
        }
    }
}
