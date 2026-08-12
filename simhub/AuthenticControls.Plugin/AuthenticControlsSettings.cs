using System.Collections.Generic;

namespace AuthenticControls.Plugin
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

    public sealed class AuthenticControlsSettings
    {
        public double PopupDurationSeconds { get; set; }
        public string PopupSize { get; set; }
        public string VerificationObserver { get; set; }
        public Dictionary<string, VerificationAssistProfile> VerificationAssistProfiles { get; set; }

        public AuthenticControlsSettings()
        {
            PopupDurationSeconds = 10.0;
            PopupSize = "compact";
            VerificationObserver = string.Empty;
            VerificationAssistProfiles = new Dictionary<string, VerificationAssistProfile>();
        }
    }
}
