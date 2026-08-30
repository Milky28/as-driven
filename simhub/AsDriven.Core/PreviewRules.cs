using System;

namespace AsDriven.Core
{
    /// <summary>
    /// Decisions about the offline car preview. The plugin owns the SimHub
    /// overlay objects; the rules that decide when preview yields to the live
    /// car, and which layout to prefer, are plain logic kept here so they can
    /// be tested without the simulator running.
    /// </summary>
    public static class PreviewRules
    {
        public const string LayoutNamePrefix = "As Driven";
        public const string StandardLayoutName = "As Driven";

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
        public static bool IsAsDrivenLayoutName(string name)
        {
            return !string.IsNullOrWhiteSpace(name)
                && name.StartsWith(LayoutNamePrefix, StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>
        /// The layout to prefer. One preset ships, positioned for an ordinary
        /// desktop; a super-ultrawide preset was packaged alongside it until
        /// 0.21.0 and was dropped because a driver repositions the overlay once
        /// and the second preset only added a choice to get wrong.
        /// </summary>
        public static string PreferredLayoutName(double virtualScreenWidth)
        {
            return StandardLayoutName;
        }
    }
}
