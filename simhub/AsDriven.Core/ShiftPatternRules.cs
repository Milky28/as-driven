using System;

namespace AsDriven.Core
{
    /// <summary>
    /// Decides which gate pattern a shift mechanism implies. The guided
    /// verification form fills the gate in for the driver where the mechanism
    /// settles it, and asks where it does not, so a stale answer from the
    /// previous car can never be saved as an observation of this one.
    /// </summary>
    public static class ShiftPatternRules
    {
        /// <summary>
        /// The gate implied by a shift mechanism, or null when the driver must
        /// report it from the cockpit.
        ///
        /// An H-pattern is deliberately never derived. Standard and dogleg are
        /// both legitimate, and defaulting to standard would record an
        /// assumption as an observation, which the evidence rules forbid.
        /// </summary>
        public static string DerivedGate(string actuation)
        {
            switch (actuation)
            {
                case "sequential-paddles":
                case "sequential-stick":
                    return "sequential";
                case "automatic-lever":
                    return "automatic-gate";
                case "direct-selection":
                    return "direct";
                default:
                    return null;
            }
        }

        /// <summary>
        /// True for a gate that only a mechanism implies. Such a value is
        /// dropped when the mechanism changes to one that no longer implies it,
        /// rather than being left behind as the new mechanism's answer.
        /// </summary>
        public static bool IsDerivedGate(string value)
        {
            return string.Equals(value, "sequential", StringComparison.Ordinal)
                || string.Equals(value, "automatic-gate", StringComparison.Ordinal)
                || string.Equals(value, "direct", StringComparison.Ordinal);
        }
    }
}
