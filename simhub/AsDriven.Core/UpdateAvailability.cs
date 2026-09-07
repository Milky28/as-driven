using System;
using System.Globalization;

namespace AsDriven.Core
{
    /// <summary>
    /// What a release manifest says compared with what is installed.
    ///
    /// The manual check decides whether something newer exists and carries the
    /// signed-by-hash package metadata used only if the driver then chooses to
    /// download and install it. Everything network-facing lives in the plugin;
    /// everything decidable lives here, where it can be tested without a server.
    /// </summary>
    public sealed class UpdateAvailability
    {
        public bool DatasetIsNewer { get; private set; }
        public bool PluginIsNewer { get; private set; }
        public string LatestDatasetVersion { get; private set; }
        public string LatestPluginVersion { get; private set; }
        public string ReleaseUrl { get; private set; }
        public string PackageUrl { get; private set; }
        public string PackageSha256 { get; private set; }
        /// <summary>Why nothing could be compared, or empty when it could.</summary>
        public string Unavailable { get; private set; }

        public bool AnythingIsNewer
        {
            get { return DatasetIsNewer || PluginIsNewer; }
        }

        public bool HasInstallPackage
        {
            get
            {
                Uri package;
                return AnythingIsNewer
                    && Uri.TryCreate(PackageUrl, UriKind.Absolute, out package)
                    && package.Scheme == Uri.UriSchemeHttps
                    && package.Host.Equals("github.com", StringComparison.OrdinalIgnoreCase)
                    && package.AbsolutePath.StartsWith(
                        "/Milky28/as-driven/releases/download/",
                        StringComparison.OrdinalIgnoreCase)
                    && IsSha256(PackageSha256);
            }
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
                PackageUrl = string.Empty,
                PackageSha256 = string.Empty,
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
            return Compare(
                installedDataset, installedPlugin, manifestDataset,
                manifestPlugin, releaseUrl, string.Empty, string.Empty);
        }

        public static UpdateAvailability Compare(
            string installedDataset,
            string installedPlugin,
            string manifestDataset,
            string manifestPlugin,
            string releaseUrl,
            string packageUrl,
            string packageSha256)
        {
            return new UpdateAvailability
            {
                LatestDatasetVersion = Clean(manifestDataset),
                LatestPluginVersion = Clean(manifestPlugin),
                ReleaseUrl = Clean(releaseUrl),
                PackageUrl = Clean(packageUrl),
                PackageSha256 = Clean(packageSha256).ToLowerInvariant(),
                DatasetIsNewer = IsNewer(installedDataset, manifestDataset),
                PluginIsNewer = IsNewer(installedPlugin, manifestPlugin),
                Unavailable = string.Empty,
            };
        }

        private static bool IsSha256(string value)
        {
            if (string.IsNullOrWhiteSpace(value) || value.Trim().Length != 64)
            {
                return false;
            }
            foreach (char character in value.Trim())
            {
                if (!((character >= '0' && character <= '9')
                    || (character >= 'a' && character <= 'f')
                    || (character >= 'A' && character <= 'F')))
                {
                    return false;
                }
            }
            return true;
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
            return HasInstallPackage
                ? message + "Nothing has been downloaded. Choose Download and install to continue."
                : message + "Nothing has been downloaded. Install it from the release page.";
        }
    }
}
