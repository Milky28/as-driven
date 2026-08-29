using System;
using System.Globalization;

namespace AsDriven.Core
{
    /// <summary>
    /// What a release manifest says compared with what is installed.
    ///
    /// The plugin never downloads or installs anything. This decides one thing:
    /// whether to tell the driver that something newer exists, and what to call
    /// it. Everything network-facing lives in the plugin; everything decidable
    /// lives here, where it can be tested without a server.
    /// </summary>
    public sealed class UpdateAvailability
    {
        public bool DatasetIsNewer { get; private set; }
        public bool PluginIsNewer { get; private set; }
        public string LatestDatasetVersion { get; private set; }
        public string LatestPluginVersion { get; private set; }
        public string ReleaseUrl { get; private set; }
        /// <summary>Why nothing could be compared, or empty when it could.</summary>
        public string Unavailable { get; private set; }

        public bool AnythingIsNewer
        {
            get { return DatasetIsNewer || PluginIsNewer; }
        }

        private UpdateAvailability() { }

        public static UpdateAvailability NotChecked(string reason)
        {
            return new UpdateAvailability
            {
                Unavailable = reason ?? string.Empty,
                LatestDatasetVersion = string.Empty,
                LatestPluginVersion = string.Empty,
                ReleaseUrl = string.Empty,
            };
        }

        /// <summary>
        /// Compare an installed pair against a manifest's pair.
        ///
        /// A manifest that omits a version says nothing about it, which is not
        /// the same as saying it is up to date: a dataset-only release carries
        /// no plugin version and must not be read as one.
        /// </summary>
        public static UpdateAvailability Compare(
            string installedDataset,
            string installedPlugin,
            string manifestDataset,
            string manifestPlugin,
            string releaseUrl)
        {
            return new UpdateAvailability
            {
                LatestDatasetVersion = Clean(manifestDataset),
                LatestPluginVersion = Clean(manifestPlugin),
                ReleaseUrl = Clean(releaseUrl),
                DatasetIsNewer = IsNewer(installedDataset, manifestDataset),
                PluginIsNewer = IsNewer(installedPlugin, manifestPlugin),
                Unavailable = string.Empty,
            };
        }

        /// <summary>
        /// Whether <paramref name="candidate"/> is a later version than
        /// <paramref name="installed"/>.
        ///
        /// Compared part by part as numbers, so 0.5.33 is later than 0.5.9 where
        /// a string comparison would say the opposite. A part that is not a
        /// number, or a version that cannot be read at all, answers false: an
        /// unreadable manifest must never look like an available update.
        /// </summary>
        public static bool IsNewer(string installed, string candidate)
        {
            int[] left = Parse(installed);
            int[] right = Parse(candidate);
            if (left == null || right == null)
            {
                return false;
            }
            int length = Math.Max(left.Length, right.Length);
            for (int index = 0; index < length; index++)
            {
                int a = index < left.Length ? left[index] : 0;
                int b = index < right.Length ? right[index] : 0;
                if (b != a)
                {
                    return b > a;
                }
            }
            return false;
        }

        private static int[] Parse(string version)
        {
            if (string.IsNullOrWhiteSpace(version))
            {
                return null;
            }
            string[] parts = version.Trim().Split('.');
            int[] numbers = new int[parts.Length];
            for (int index = 0; index < parts.Length; index++)
            {
                int value;
                if (!int.TryParse(parts[index], NumberStyles.None, CultureInfo.InvariantCulture, out value))
                {
                    return null;
                }
                numbers[index] = value;
            }
            return numbers;
        }

        private static string Clean(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? string.Empty : value.Trim();
        }

        /// <summary>The sentence the settings page shows for this result.</summary>
        public string Summary(string installedDataset, string installedPlugin)
        {
            if (Unavailable.Length > 0)
            {
                return Unavailable;
            }
            if (!AnythingIsNewer)
            {
                return "Up to date. Dataset " + installedDataset
                    + " and plugin " + installedPlugin + " are the current releases.";
            }
            string message = string.Empty;
            if (DatasetIsNewer)
            {
                message += "Dataset " + LatestDatasetVersion + " is available (installed "
                    + installedDataset + "). ";
            }
            if (PluginIsNewer)
            {
                message += "Plugin " + LatestPluginVersion + " is available (installed "
                    + installedPlugin + "). ";
            }
            // Said every time, because the plugin does not fetch anything and a
            // driver who reads "available" reasonably expects it to have acted.
            return message + "Nothing has been downloaded. Install it yourself from the release page.";
        }
    }
}
