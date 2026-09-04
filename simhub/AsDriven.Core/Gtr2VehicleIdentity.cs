using System;
using System.IO;
using System.Text;

namespace AsDriven.Core
{
    /// <summary>
    /// The exact GTR2 vehicle selected in the active telemetry session. SimHub's
    /// GTR2 reader reports a generated DC__ timestamp for every car in a game
    /// session, so its generic CarModel and CarId fields are not identities.
    /// GTR2 writes the selected .CAR path into vehicledata.spt; the player
    /// profile provides an offline fallback for tooling and tests.
    /// </summary>
    public sealed class Gtr2VehicleIdentity
    {
        private Gtr2VehicleIdentity(
            string telemetryName,
            string internalId,
            CarImplementation implementation)
        {
            TelemetryName = telemetryName;
            InternalId = internalId;
            Implementation = implementation;
        }

        public string TelemetryName { get; private set; }
        public string InternalId { get; private set; }
        public CarImplementation Implementation { get; private set; }

        public static Gtr2VehicleIdentity Resolve(string gameRoot)
        {
            return Resolve(gameRoot, null);
        }

        /// <summary>
        /// Resolve a live session only when vehicledata.spt has been written by
        /// the current game process. This deliberately does not fall back to a
        /// profile that may still name the car used in the previous session.
        /// </summary>
        public static Gtr2VehicleIdentity Resolve(string gameRoot, DateTime? sessionStartedUtc)
        {
            if (string.IsNullOrWhiteSpace(gameRoot) || !Directory.Exists(gameRoot))
            {
                return null;
            }
            string root;
            try
            {
                root = Path.GetFullPath(gameRoot).TrimEnd(Path.DirectorySeparatorChar);
            }
            catch
            {
                return null;
            }

            string userData = Path.Combine(root, "UserData");
            if (!Directory.Exists(userData))
            {
                return null;
            }

            string sessionVehicle = ReadSessionVehicleFile(
                Path.Combine(userData, "vehicledata.spt"),
                sessionStartedUtc);
            Gtr2VehicleIdentity sessionIdentity = ResolveVehicle(root, sessionVehicle);
            if (sessionIdentity != null || sessionStartedUtc.HasValue)
            {
                return sessionIdentity;
            }

            string[] profiles;
            try
            {
                profiles = Directory.GetFiles(userData, "*.PLR", SearchOption.AllDirectories);
                Array.Sort(profiles, delegate(string left, string right)
                {
                    return File.GetLastWriteTimeUtc(right).CompareTo(File.GetLastWriteTimeUtc(left));
                });
            }
            catch
            {
                return null;
            }

            foreach (string profile in profiles)
            {
                string vehicleFile = ReadAssignment(profile, "Vehicle File");
                Gtr2VehicleIdentity identity = ResolveVehicle(root, vehicleFile);
                if (identity != null) return identity;
            }
            return null;
        }

        private static Gtr2VehicleIdentity ResolveVehicle(string root, string vehicleFile)
        {
            string fullVehiclePath;
            if (string.IsNullOrWhiteSpace(vehicleFile)
                || !TryResolveInside(root, vehicleFile, out fullVehiclePath)
                || !File.Exists(fullVehiclePath))
            {
                return null;
            }
            string description = ReadAssignment(fullVehiclePath, "Description");
            if (string.IsNullOrWhiteSpace(description))
            {
                return null;
            }
            string internalId = vehicleFile.Trim().Replace('\\', '/');
            return new Gtr2VehicleIdentity(
                description.Trim(),
                internalId,
                CarImplementation.ForGtr2(root, internalId));
        }

        private static string ReadSessionVehicleFile(string path, DateTime? sessionStartedUtc)
        {
            try
            {
                if (!File.Exists(path)
                    || (sessionStartedUtc.HasValue
                        && File.GetLastWriteTimeUtc(path) < sessionStartedUtc.Value.AddSeconds(-2)))
                {
                    return null;
                }

                // The SPT header begins with 12 binary bytes followed by four
                // NUL-terminated strings: driver, description, .CAR path, track.
                // Only the small header is needed, and FileShare.ReadWrite keeps
                // this usable while GTR2 is actively appending telemetry.
                byte[] header = new byte[4096];
                int count;
                using (var stream = new FileStream(
                    path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
                {
                    count = stream.Read(header, 0, header.Length);
                }
                int offset = 12;
                ReadNullTerminatedAscii(header, count, ref offset);
                ReadNullTerminatedAscii(header, count, ref offset);
                string vehicleFile = ReadNullTerminatedAscii(header, count, ref offset);
                return vehicleFile != null
                    && vehicleFile.EndsWith(".CAR", StringComparison.OrdinalIgnoreCase)
                    ? vehicleFile
                    : null;
            }
            catch
            {
                return null;
            }
        }

        private static string ReadNullTerminatedAscii(byte[] bytes, int count, ref int offset)
        {
            if (offset < 0 || offset >= count)
            {
                return null;
            }
            int start = offset;
            while (offset < count && bytes[offset] != 0)
            {
                offset++;
            }
            if (offset >= count)
            {
                return null;
            }
            string value = Encoding.ASCII.GetString(bytes, start, offset - start);
            offset++;
            return value;
        }

        internal static string ReadAssignment(string path, string name)
        {
            string[] lines;
            try
            {
                lines = File.ReadAllLines(path);
            }
            catch
            {
                return null;
            }
            foreach (string sourceLine in lines)
            {
                string line = (sourceLine ?? string.Empty).Trim().Trim('\0');
                int equals = line.IndexOf('=');
                if (equals <= 0
                    || !string.Equals(
                        line.Substring(0, equals).Trim(),
                        name,
                        StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }
                string value = line.Substring(equals + 1).Trim();
                if (value.Length >= 2 && value[0] == '"' && value[value.Length - 1] == '"')
                {
                    value = value.Substring(1, value.Length - 2);
                }
                return value.Trim();
            }
            return null;
        }

        internal static bool TryResolveInside(
            string gameRoot, string relativePath, out string fullPath)
        {
            fullPath = null;
            try
            {
                string root = Path.GetFullPath(gameRoot).TrimEnd(Path.DirectorySeparatorChar);
                string normalized = relativePath.Replace('/', Path.DirectorySeparatorChar)
                    .Replace('\\', Path.DirectorySeparatorChar);
                string candidate = Path.GetFullPath(Path.Combine(root, normalized));
                string prefix = root + Path.DirectorySeparatorChar;
                if (!candidate.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                {
                    return false;
                }
                fullPath = candidate;
                return true;
            }
            catch
            {
                return false;
            }
        }
    }
}
