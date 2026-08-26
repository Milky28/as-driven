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

        /// <summary>
        /// Whether a downshift result can say anything about the car.
        ///
        /// The coast test learns from a refusal: a gearbox that will not take
        /// the gear without a blip is telling you the driver has to supply one.
        /// A simulator that accepts every downshift at any engine speed refuses
        /// nothing, so "accepted" is a fact about the simulator's transmission
        /// model and not about the car, and the manual-blip test that follows a
        /// refusal is never reached at all.
        ///
        /// RaceRoom is the first known case, reported from the seat on a 190E
        /// Evo II DTM - a synchromesh H-pattern car already curated elsewhere as
        /// not blipping its own throttle - which took clutchless downshifts at
        /// any engine speed and still reported an automatic blip. An
        /// unregistered simulator is treated the same way, because nothing is
        /// known about it.
        /// </summary>
        public static bool DownshiftEngagementIsMeasurable(string simulator)
        {
            return !string.Equals(simulator, "raceroom", StringComparison.Ordinal)
                && !string.Equals(simulator, "other", StringComparison.Ordinal);
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
                // rFactor 2 publishes no engine torque either, which its first
                // drive reported directly rather than being assumed.
                && !string.Equals(simulator, "rf2", StringComparison.Ordinal)
                && !string.Equals(simulator, "other", StringComparison.Ordinal);
        }
    }
}
