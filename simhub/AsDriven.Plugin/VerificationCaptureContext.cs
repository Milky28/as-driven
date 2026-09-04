using System;
using AsDriven.Core;

namespace AsDriven.Plugin
{
    internal sealed class VerificationCaptureContext
    {
        public string Simulator { get; set; }
        /// <summary>What the game called itself, kept for an unregistered simulator.</summary>
        public string SourceGameName { get; set; }
        public string SimulatorDisplayName { get; set; }
        public string GameVersion { get; set; }
        public string ClientVersion { get; set; }
        public DateTime ObservedAtUtc { get; set; }
        public string TelemetryName { get; set; }
        public string TelemetryClass { get; set; }
        public string InternalId { get; set; }
        public CarImplementation Implementation { get; set; }
        public int? SuggestedForwardGears { get; set; }

        public VerificationCaptureContext WithObservedAt(DateTime observedAtUtc)
        {
            return new VerificationCaptureContext
            {
                Simulator = Simulator,
                SourceGameName = SourceGameName,
                SimulatorDisplayName = SimulatorDisplayName,
                GameVersion = GameVersion,
                ClientVersion = ClientVersion,
                ObservedAtUtc = observedAtUtc,
                TelemetryName = TelemetryName,
                TelemetryClass = TelemetryClass,
                InternalId = InternalId,
                Implementation = Implementation,
                SuggestedForwardGears = SuggestedForwardGears
            };
        }
    }
}
