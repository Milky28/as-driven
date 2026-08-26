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
            // AC, ACC and RaceRoom do not publish engine torque through
            // SimHub. A successful full-throttle upshift can establish
            // acceptance, but it cannot distinguish a modeled cut from another
            // shift implementation, so asking a contributor to settle the cut
            // asks for something no amount of driving can produce.
            //
            // An unregistered simulator answers "other" and is treated the same
            // way, because nothing is known about what it publishes. That is the
            // safe direction: the worst case is a review that does not ask for a
            // cut which could in fact have been measured, against a review that
            // demands one the telemetry can never supply.
            return !string.Equals(simulator, "ac", StringComparison.Ordinal)
                && !string.Equals(simulator, "acc", StringComparison.Ordinal)
                && !string.Equals(simulator, "raceroom", StringComparison.Ordinal)
                && !string.Equals(simulator, "other", StringComparison.Ordinal);
        }
    }
}
