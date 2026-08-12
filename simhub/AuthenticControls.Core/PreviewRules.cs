using System;

namespace AuthenticControls.Core
{
    /// <summary>
    /// Decisions about the offline car preview. The plugin owns the SimHub
    /// overlay objects; the rules that decide when preview yields to the live
    /// car, and which layout to prefer, are plain logic kept here so they can
    /// be tested without the simulator running.
    /// </summary>
    public static class PreviewRules
    {
        public const string LayoutNamePrefix = "Authentic Controls";
        public const string WideLayoutName = "Authentic Controls 5120x1440";
        public const string StandardLayoutName = "Authentic Controls";

        /// <summary>
        /// Minimum virtual screen width that prefers the wide layout.
        /// </summary>
        public const double WideLayoutMinimumWidth = 3840;

        /// <summary>
        /// Preview is abandoned once the game reports a real car that differs
        /// from the one preview was entered against. A blank live identifier is
        /// not a car change, so loading screens do not cancel a preview.
        /// </summary>
        public static bool ShouldLeavePreview(
            bool previewActive,
            bool gameRunning,
            string previewLiveCarIdentifier,
            string currentLiveCarIdentifier)
        {
            return previewActive
                && gameRunning
                && !string.IsNullOrWhiteSpace(currentLiveCarIdentifier)
                && !string.Equals(
                    previewLiveCarIdentifier ?? string.Empty,
                    currentLiveCarIdentifier,
                    StringComparison.Ordinal);
        }

        /// <summary>
        /// Identifies a layout belonging to this plugin by name, so a user's
        /// unrelated overlays are never started or stopped by the preview.
        /// </summary>
        public static bool IsAuthenticControlsLayoutName(string name)
        {
            return !string.IsNullOrWhiteSpace(name)
                && name.StartsWith(LayoutNamePrefix, StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>
        /// Chooses the layout name to prefer for the available desktop width.
        /// </summary>
        public static string PreferredLayoutName(double virtualScreenWidth)
        {
            return virtualScreenWidth >= WideLayoutMinimumWidth
                ? WideLayoutName
                : StandardLayoutName;
        }
    }
}
