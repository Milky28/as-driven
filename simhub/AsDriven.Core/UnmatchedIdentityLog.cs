using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace AsDriven.Core
{
    public sealed class UnmatchedIdentityObservation
    {
        public DateTime ObservedAtUtc { get; set; }
        public string GameName { get; set; }
        public string GameVersion { get; set; }
        public string CarModel { get; set; }
        public string CarId { get; set; }
        public string CarClass { get; set; }
        public string DatasetVersion { get; set; }
        public string SimHubVersion { get; set; }
    }

    public sealed class UnmatchedIdentityLog
    {
        private readonly object _gate = new object();
        private readonly HashSet<string> _knownIdentities =
            new HashSet<string>(StringComparer.Ordinal);

        public UnmatchedIdentityLog(string filePath)
        {
            if (string.IsNullOrWhiteSpace(filePath))
            {
                throw new ArgumentException("An unmatched identity log path is required.", "filePath");
            }
            FilePath = Path.GetFullPath(filePath);
            LoadKnownIdentities();
        }

        public string FilePath { get; private set; }

        public int Count
        {
            get
            {
                lock (_gate)
                {
                    return _knownIdentities.Count;
                }
            }
        }

        public bool Record(UnmatchedIdentityObservation observation)
        {
            if (observation == null)
            {
                throw new ArgumentNullException("observation");
            }

            string key = Key(observation);
            lock (_gate)
            {
                if (_knownIdentities.Contains(key))
                {
                    return false;
                }

                string directory = Path.GetDirectoryName(FilePath);
                if (!Directory.Exists(directory))
                {
                    Directory.CreateDirectory(directory);
                }

                JObject line = ToJson(observation);
                File.AppendAllText(
                    FilePath,
                    line.ToString(Formatting.None) + Environment.NewLine,
                    new UTF8Encoding(false));
                _knownIdentities.Add(key);
                return true;
            }
        }

        private void LoadKnownIdentities()
        {
            if (!File.Exists(FilePath))
            {
                return;
            }

            foreach (string line in File.ReadAllLines(FilePath))
            {
                if (string.IsNullOrWhiteSpace(line))
                {
                    continue;
                }
                try
                {
                    JObject value = JObject.Parse(line);
                    _knownIdentities.Add(Key(
                        Value(value, "game_name"),
                        Value(value, "game_version"),
                        Value(value, "car_model"),
                        Value(value, "car_id"),
                        Value(value, "car_class")));
                }
                catch (JsonException)
                {
                    // Preserve append-only diagnostics even if a manually edited line is invalid.
                }
            }
        }

        private static JObject ToJson(UnmatchedIdentityObservation observation)
        {
            return new JObject
            {
                { "observed_at_utc", observation.ObservedAtUtc.ToUniversalTime().ToString("o") },
                { "game_name", Safe(observation.GameName) },
                { "game_version", Safe(observation.GameVersion) },
                { "car_model", Safe(observation.CarModel) },
                { "car_id", Safe(observation.CarId) },
                { "car_class", Safe(observation.CarClass) },
                { "dataset_version", Safe(observation.DatasetVersion) },
                { "simhub_version", Safe(observation.SimHubVersion) }
            };
        }

        private static string Key(UnmatchedIdentityObservation observation)
        {
            return Key(
                observation.GameName,
                observation.GameVersion,
                observation.CarModel,
                observation.CarId,
                observation.CarClass);
        }

        private static string Key(
            string gameName,
            string gameVersion,
            string carModel,
            string carId,
            string carClass)
        {
            return Safe(gameName) + "\u001f"
                + Safe(gameVersion) + "\u001f"
                + Safe(carModel) + "\u001f"
                + Safe(carId) + "\u001f"
                + Safe(carClass);
        }

        private static string Value(JObject value, string name)
        {
            JToken token = value[name];
            return token == null ? string.Empty : token.Value<string>() ?? string.Empty;
        }

        private static string Safe(string value)
        {
            return value ?? string.Empty;
        }
    }
}
