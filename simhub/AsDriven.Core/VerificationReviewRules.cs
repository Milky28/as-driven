using System;

namespace AsDriven.Core
{
    /// <summary>
    /// Keeps the contribution form's review prompts aligned with what the
    /// selected mechanism and simulator telemetry can actually establish.
    /// Values remain unknown where telemetry is unavailable; this only decides
    /// whether asking the contributor to review that unresolved value is useful.
    /// </summary>
    public static class VerificationReviewRules
    {
        public static bool DirectGearSelectionApplies(string primaryActuation)
        {
            return string.Equals(primaryActuation, "h-pattern", StringComparison.Ordinal)
                || string.Equals(primaryActuation, "direct-selection", StringComparison.Ordinal);
        }

        public static bool AutomaticCutIsMeasurable(string simulator)
        {
            // ACC does not publish engine torque through SimHub. A successful
            // full-throttle upshift can establish acceptance, but it cannot
            // distinguish a modeled cut from another shift implementation.
            return !string.Equals(simulator, "acc", StringComparison.Ordinal);
        }
    }
}
