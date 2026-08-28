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
        public const string DefaultTheme = "auto";
        public const string ModernTheme = "modern";
        public const string ModernLightTheme = "modern-light";
        public const string SixtiesTheme = "1960s-roadbook";
        public const string SeventiesTheme = "1970s-works";
        public const string EightiesTheme = "1980s-black-gold";
        public const string NinetiesTheme = "1990s-touring";

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
            // Glance was retired: two sizes that say the same thing beat a
            // third that had to leave things out. A stored "glance" falls
            // back to the default rather than selecting a missing dashboard.
            if (normalized == "detailed" || normalized == "compact")
            {
                return normalized;
            }
            return DefaultSize;
        }

        /// <summary>
        /// Accepts only themes packaged in the generated dashboard. Auto is a
        /// preference rather than a rendered theme and is resolved per car.
        /// </summary>
        public static string NormalizeTheme(string popupTheme)
        {
            string normalized = (popupTheme ?? string.Empty).Trim().ToLowerInvariant();
            if (normalized == DefaultTheme
                || normalized == ModernTheme
                || normalized == ModernLightTheme
                || normalized == SixtiesTheme
                || normalized == SeventiesTheme
                || normalized == EightiesTheme
                || normalized == NinetiesTheme)
            {
                return normalized;
            }
            return DefaultTheme;
        }

        /// <summary>
        /// Resolves auto from the curated start year. An absent year is not
        /// inferred from a car name; it deliberately uses the modern fallback.
        /// </summary>
        public static string ResolveTheme(string popupTheme, int yearFrom)
        {
            string normalized = NormalizeTheme(popupTheme);
            if (normalized != DefaultTheme)
            {
                return normalized;
            }
            if (yearFrom <= 0 || yearFrom >= 2000)
            {
                return ModernTheme;
            }
            if (yearFrom < 1970)
            {
                return SixtiesTheme;
            }
            if (yearFrom < 1980)
            {
                return SeventiesTheme;
            }
            if (yearFrom < 1990)
            {
                return EightiesTheme;
            }
            return NinetiesTheme;
        }
    }
}
