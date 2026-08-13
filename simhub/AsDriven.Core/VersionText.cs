using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace AsDriven.Core
{
    public static class VersionText
    {
        public static string Normalize(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return "unknown";
            }

            var parts = new List<string>();
            foreach (Match match in Regex.Matches(value, "[0-9]+"))
            {
                parts.Add(match.Value);
            }
            return parts.Count == 0 ? "unknown" : string.Join(".", parts.ToArray());
        }

        public static string ParseSimHubStartupLine(string value)
        {
            Match match = Regex.Match(
                value ?? string.Empty,
                @"Starting\s+SimHub\s+v(?<version>[0-9]+(?:\.[0-9]+)+)",
                RegexOptions.IgnoreCase);
            return match.Success ? Normalize(match.Groups["version"].Value) : "unknown";
        }
    }
}
