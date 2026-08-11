using System;

namespace AuthenticControls.Plugin
{
    internal sealed class VerificationCaptureContext
    {
        public string Simulator { get; set; }
        public string SimulatorDisplayName { get; set; }
        public string GameVersion { get; set; }
        public string ClientVersion { get; set; }
        public DateTime ObservedAtUtc { get; set; }
        public string TelemetryName { get; set; }
        public string TelemetryClass { get; set; }
        public string InternalId { get; set; }
        public int? SuggestedForwardGears { get; set; }
    }
}
