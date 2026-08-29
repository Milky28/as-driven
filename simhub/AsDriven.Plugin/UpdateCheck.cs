using System;
using System.IO;
using System.Net;
using System.Text.RegularExpressions;
using AsDriven.Core;

namespace AsDriven.Plugin
{
    /// <summary>
    /// The only code in As Driven that touches the network, and it runs when a
    /// person presses a button.
    ///
    /// There is no timer, nothing at startup, and nothing after an install. The
    /// endpoint is empty until somebody sets it, and an empty endpoint makes no
    /// request at all - so an installation nobody configures keeps the property
    /// PRIVACY.md describes.
    ///
    /// It fetches a small manifest and compares two version strings. It never
    /// downloads a dataset or a plugin, because a curated value changing under a
    /// driver mid-session is worse than a stale one they know about.
    /// </summary>
    internal static class UpdateCheck
    {
        internal const int TimeoutMilliseconds = 8000;
        private const int MaximumManifestBytes = 64 * 1024;

        /// <summary>
        /// Whether a configured endpoint is one this will actually call.
        ///
        /// HTTPS only. A plaintext endpoint could be rewritten in transit into
        /// an announcement of an update that does not exist, pointing at a
        /// release page nobody published.
        /// </summary>
        internal static bool IsAllowedEndpoint(string url)
        {
            if (string.IsNullOrWhiteSpace(url))
            {
                return false;
            }
            Uri parsed;
            if (!Uri.TryCreate(url.Trim(), UriKind.Absolute, out parsed))
            {
                return false;
            }
            return parsed.Scheme == Uri.UriSchemeHttps;
        }

        /// <summary>Read a version out of the manifest without a JSON parser.</summary>
        internal static string ReadField(string manifest, string field)
        {
            if (string.IsNullOrEmpty(manifest))
            {
                return string.Empty;
            }
            Match match = Regex.Match(
                manifest,
                "\"" + Regex.Escape(field) + "\"\\s*:\\s*\"([^\"]{0,120})\"",
                RegexOptions.CultureInvariant);
            return match.Success ? match.Groups[1].Value.Trim() : string.Empty;
        }

        /// <summary>
        /// Ask the endpoint what the current releases are.
        ///
        /// Every failure answers NotChecked with the reason. None of them may
        /// answer "up to date": a plugin that reports currency because it could
        /// not reach the server is worse than one that says nothing, since the
        /// driver stops looking.
        /// </summary>
        internal static UpdateAvailability Fetch(
            string endpoint,
            string installedDataset,
            string installedPlugin)
        {
            if (string.IsNullOrWhiteSpace(endpoint))
            {
                return UpdateAvailability.NotChecked(
                    "No update endpoint is set, so nothing was contacted. As Driven makes no "
                    + "network request until one is configured here.");
            }
            if (!IsAllowedEndpoint(endpoint))
            {
                return UpdateAvailability.NotChecked(
                    "The update endpoint must be an https address. Nothing was contacted.");
            }
            try
            {
                var request = (HttpWebRequest)WebRequest.Create(endpoint.Trim());
                request.Method = "GET";
                request.Timeout = TimeoutMilliseconds;
                request.ReadWriteTimeout = TimeoutMilliseconds;
                request.UserAgent = "AsDriven";
                request.AllowAutoRedirect = true;
                using (var response = (HttpWebResponse)request.GetResponse())
                using (Stream stream = response.GetResponseStream())
                {
                    if (stream == null)
                    {
                        return UpdateAvailability.NotChecked("The update endpoint returned nothing.");
                    }
                    var buffer = new char[MaximumManifestBytes];
                    int read;
                    using (var reader = new StreamReader(stream))
                    {
                        read = reader.ReadBlock(buffer, 0, buffer.Length);
                    }
                    string manifest = new string(buffer, 0, Math.Max(read, 0));
                    string dataset = ReadField(manifest, "dataset_version");
                    string plugin = ReadField(manifest, "plugin_version");
                    string releaseUrl = ReadField(manifest, "release_url");
                    if (dataset.Length == 0 && plugin.Length == 0)
                    {
                        return UpdateAvailability.NotChecked(
                            "The update endpoint did not return a dataset or plugin version.");
                    }
                    return UpdateAvailability.Compare(
                        installedDataset, installedPlugin, dataset, plugin, releaseUrl);
                }
            }
            catch (WebException exception)
            {
                return UpdateAvailability.NotChecked(
                    "Could not reach the update endpoint: " + exception.Message);
            }
            catch (Exception exception)
            {
                return UpdateAvailability.NotChecked(
                    "The update check failed: " + exception.Message);
            }
        }
    }
}
