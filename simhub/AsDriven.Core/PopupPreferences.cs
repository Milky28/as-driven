using System;

namespace AsDriven.Core
{
    /// <summary>
    /// Normalizes the stored popup preferences. These rules decide what the
    /// driver actually sees, so they live in the testable core rather than in
    /// the SimHub-coupled plugin adapter.
    /// </summary>
    public static class PopupPreferences
    {
        public const double DefaultDurationSeconds = 10.0;
        public const double MinimumDurationSeconds = 1.0;
        public const double MaximumDurationSeconds = 60.0;
        public const string DefaultSize = "compact";

        /// <summary>
        /// Clamps a stored duration into the supported range. A missing or
        /// nonsense value falls back to the default rather than disabling the
        /// popup or leaving it on screen indefinitely.
        /// </summary>
        public static double NormalizeDuration(double seconds)
        {
            if (double.IsNaN(seconds) || double.IsInfinity(seconds))
            {
                return DefaultDurationSeconds;
            }
            return Math.Max(
                MinimumDurationSeconds,
                Math.Min(MaximumDurationSeconds, Math.Round(seconds)));
        }

        /// <summary>
        /// Accepts only the sizes the plugin can render. An unknown value falls
        /// back to the default instead of selecting a missing dashboard.
        /// </summary>
        public static string NormalizeSize(string popupSize)
        {
            string normalized = (popupSize ?? string.Empty).Trim().ToLowerInvariant();
            if (normalized == "detailed" || normalized == "compact" || normalized == "glance")
            {
                return normalized;
            }
            return DefaultSize;
        }
    }
}
