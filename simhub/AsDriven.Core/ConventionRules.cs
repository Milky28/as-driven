using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;

namespace AsDriven.Core
{
    /// <summary>
    /// What cars of a given mechanism and era were usually driven like, for
    /// display where the real car's own value is not established.
    /// </summary>
    /// <remarks>
    /// A rule is evidence about a class, never a finding about the car in front
    /// of the driver. It only ever describes a field the record leaves unknown,
    /// so an established value always wins and can never be overwritten here.
    /// Rules are matched against the authentic controls rather than the values a
    /// simulator overrides, because the gap being filled is the real car's.
    /// See docs/convention-guidance.md.
    /// </remarks>
    public static class ConventionRules
    {
        private const string Unknown = "unknown";

        /// <summary>
        /// Reads the rule registry beside the dataset. A database published
        /// before conventions existed simply has no file, which is a supported
        /// state and yields no guidance rather than an error.
        /// </summary>
        public static JArray Load(string dataDirectory)
        {
            if (string.IsNullOrWhiteSpace(dataDirectory))
            {
                return new JArray();
            }

            string path = Path.Combine(Path.GetFullPath(dataDirectory), "conventions.json");
            if (!File.Exists(path))
            {
                return new JArray();
            }

            JObject registry;
            try
            {
                registry = JObject.Parse(File.ReadAllText(path));
            }
            catch (Exception)
            {
                // Guidance is an extra, never a reason to fail loading a car.
                return new JArray();
            }

            JArray conventions = registry["conventions"] as JArray;
            return conventions ?? new JArray();
        }

        /// <summary>
        /// The guidance that applies to one record, joined into a single note.
        /// Empty when every field a rule speaks to is already established, which
        /// is the common case and not a defect.
        /// </summary>
        public static string Resolve(JArray conventions, JObject authenticControls)
        {
            if (conventions == null || conventions.Count == 0 || authenticControls == null)
            {
                return string.Empty;
            }

            JObject transmission = authenticControls["transmission"] as JObject;
            if (transmission == null)
            {
                return string.Empty;
            }

            var lines = new List<string>();
            foreach (JObject rule in conventions.OfType<JObject>())
            {
                if (!Matches(rule["when"] as JObject, transmission))
                {
                    continue;
                }

                if (!SpeaksToAnOpenField(rule["then"] as JArray, authenticControls))
                {
                    continue;
                }

                string guidance = (string)rule["guidance"];
                if (!string.IsNullOrWhiteSpace(guidance) && !lines.Contains(guidance))
                {
                    lines.Add(guidance);
                }
            }

            return string.Join(" ", lines.ToArray());
        }

        private static bool Matches(JObject when, JObject transmission)
        {
            if (when == null)
            {
                return false;
            }

            JObject expected = when["transmission"] as JObject;
            if (expected != null)
            {
                foreach (KeyValuePair<string, JToken> condition in expected)
                {
                    string actual = ValueOrEmpty(transmission[condition.Key]);
                    string wanted = condition.Value.Type == JTokenType.Null
                        ? string.Empty
                        : condition.Value.ToString();

                    // A rule may deliberately key on a gap, so `unknown` is a
                    // value to match rather than a wildcard, and an absent field
                    // is the same thing as one recorded unknown.
                    if (string.Equals(wanted, Unknown, StringComparison.Ordinal))
                    {
                        if (actual.Length != 0 && !string.Equals(actual, Unknown, StringComparison.Ordinal))
                        {
                            return false;
                        }
                    }
                    else if (!string.Equals(actual, wanted, StringComparison.Ordinal))
                    {
                        return false;
                    }
                }
            }

            return true;
        }

        private static bool SpeaksToAnOpenField(JArray then, JObject authenticControls)
        {
            if (then == null)
            {
                return false;
            }

            foreach (JObject outcome in then.OfType<JObject>())
            {
                string pointer = (string)outcome["path"];
                if (string.IsNullOrWhiteSpace(pointer))
                {
                    continue;
                }

                string current = ValueOrEmpty(Resolve(authenticControls, pointer));
                if (current.Length == 0 || string.Equals(current, Unknown, StringComparison.Ordinal))
                {
                    return true;
                }
            }

            return false;
        }

        private static JToken Resolve(JObject authenticControls, string pointer)
        {
            // Paths are written against the record, so drop the leading segment
            // that names the block this method was handed.
            const string Prefix = "/authentic_controls/";
            if (!pointer.StartsWith(Prefix, StringComparison.Ordinal))
            {
                return null;
            }

            JToken node = authenticControls;
            foreach (string part in pointer.Substring(Prefix.Length).Split('/'))
            {
                JObject container = node as JObject;
                if (container == null)
                {
                    return null;
                }

                node = container[part];
                if (node == null)
                {
                    return null;
                }
            }

            return node;
        }

        private static string ValueOrEmpty(JToken token)
        {
            if (token == null || token.Type == JTokenType.Null)
            {
                return string.Empty;
            }

            return token.ToString();
        }
    }
}
