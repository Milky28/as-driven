using System;

namespace AsDriven.Plugin
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

        public VerificationCaptureContext WithObservedAt(DateTime observedAtUtc)
        {
            return new VerificationCaptureContext
            {
                Simulator = Simulator,
                SimulatorDisplayName = SimulatorDisplayName,
                GameVersion = GameVersion,
                ClientVersion = ClientVersion,
                ObservedAtUtc = observedAtUtc,
                TelemetryName = TelemetryName,
                TelemetryClass = TelemetryClass,
                InternalId = InternalId,
                SuggestedForwardGears = SuggestedForwardGears
            };
        }
    }
}
