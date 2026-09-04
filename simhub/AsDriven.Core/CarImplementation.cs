using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using Microsoft.Win32;

namespace AsDriven.Core
{
    /// <summary>
    /// Which installed copy of a car was driven.
    ///
    /// A simulator with a mod ecosystem reports the name its author chose, and
    /// several packages may depict the same real car while shifting differently.
    /// The name identifies the package no better than the package identifies the
    /// real car, so a drive that records only the name cannot be attributed to
    /// what was actually driven - and that cannot be recovered afterwards, which
    /// is why this is captured from the first drive rather than when mods are
    /// supported.
    ///
    /// It answers one question: is this the exact package that was driven? It
    /// says nothing about which real car the package depicts. That mapping is a
    /// reviewed judgement, and it is the risky one - an official car with a
    /// manufacturer's own name was mapped to the wrong generation in this dataset
    /// for months.
    /// </summary>
    public sealed class CarImplementation
    {
        private CarImplementation(
            string contentId,
            string author,
            string declaredVersion,
            string scope,
            string digest)
        {
            ContentId = contentId;
            Author = author;
            DeclaredVersion = declaredVersion;
            Scope = scope;
            Digest = digest;
        }

        public string ContentId { get; private set; }
        public string Author { get; private set; }
        public string DeclaredVersion { get; private set; }
        public string Scope { get; private set; }
        public string Digest { get; private set; }

        /// <summary>
        /// Fingerprint an Assetto Corsa car, or return null when it cannot be
        /// found. Null is an ordinary outcome: the block is optional precisely so
        /// that a drive still produces a usable draft when the installation is
        /// somewhere this does not look.
        /// </summary>
        public static CarImplementation ForAssettoCorsa(string contentId)
        {
            if (string.IsNullOrWhiteSpace(contentId))
            {
                return null;
            }
            string content = ResolveContentDirectory();
            if (content == null)
            {
                return null;
            }
            string carDirectory = Path.Combine(content, contentId);
            if (!Directory.Exists(carDirectory))
            {
                return null;
            }

            string scope;
            string digest = DigestCarData(carDirectory, out scope);
            if (digest == null)
            {
                return null;
            }
            string author, declaredVersion;
            ReadUiMetadata(carDirectory, out author, out declaredVersion);
            return new CarImplementation(contentId, author, declaredVersion, scope, digest);
        }

        /// <summary>
        /// Fingerprint the exact GTR2 .CAR definition and the physics files it
        /// selects. This separates stock content from installations such as the
        /// HQ Anniversary Patch even though every executable still reports
        /// version 1.1.0.0.
        /// </summary>
        public static CarImplementation ForGtr2(string gameRoot, string vehicleFile)
        {
            string carPath;
            if (string.IsNullOrWhiteSpace(gameRoot)
                || string.IsNullOrWhiteSpace(vehicleFile)
                || !Gtr2VehicleIdentity.TryResolveInside(gameRoot, vehicleFile, out carPath)
                || !File.Exists(carPath))
            {
                return null;
            }

            var files = new List<string> { carPath };
            string hdcName = Gtr2VehicleIdentity.ReadAssignment(carPath, "HDVehicle");
            string hdcPath = FindDependency(gameRoot, Path.GetDirectoryName(carPath), hdcName);
            if (hdcPath != null)
            {
                files.Add(hdcPath);
                string gearName = Gtr2VehicleIdentity.ReadAssignment(hdcPath, "GearFile");
                string gearPath = FindDependency(gameRoot, Path.GetDirectoryName(hdcPath), gearName);
                if (gearPath != null)
                {
                    files.Add(gearPath);
                }
            }

            string digest = DigestFiles(gameRoot, files);
            if (digest == null)
            {
                return null;
            }
            string version = ReadGtr2PatchVersion(gameRoot);
            string author = version == null ? null : "GTR233 and friends";
            return new CarImplementation(
                vehicleFile.Replace('\\', '/'),
                author,
                version,
                "gtr2-car-hdc-gear-files",
                digest);
        }

        private static string FindDependency(
            string gameRoot, string startingDirectory, string fileName)
        {
            if (string.IsNullOrWhiteSpace(fileName))
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
            string directory = startingDirectory;
            while (!string.IsNullOrEmpty(directory)
                && (string.Equals(directory, root, StringComparison.OrdinalIgnoreCase)
                    || directory.StartsWith(
                        root + Path.DirectorySeparatorChar,
                        StringComparison.OrdinalIgnoreCase)))
            {
                string candidate = Path.Combine(directory, fileName);
                if (File.Exists(candidate))
                {
                    return candidate;
                }
                if (string.Equals(directory, root, StringComparison.OrdinalIgnoreCase))
                {
                    break;
                }
                directory = Path.GetDirectoryName(directory);
            }
            return null;
        }

        private static string DigestFiles(string root, List<string> files)
        {
            try
            {
                files.Sort(StringComparer.OrdinalIgnoreCase);
                string fullRoot = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar);
                using (var sha = SHA256.Create())
                {
                    foreach (string file in files)
                    {
                        string relative = file.Substring(fullRoot.Length)
                            .TrimStart('\\', '/')
                            .Replace('\\', '/')
                            .ToLowerInvariant();
                        byte[] name = Encoding.UTF8.GetBytes(relative + "\n");
                        sha.TransformBlock(name, 0, name.Length, name, 0);
                        byte[] contents = File.ReadAllBytes(file);
                        sha.TransformBlock(contents, 0, contents.Length, contents, 0);
                    }
                    sha.TransformFinalBlock(new byte[0], 0, 0);
                    return ToHex(sha.Hash);
                }
            }
            catch
            {
                return null;
            }
        }

        private static string ReadGtr2PatchVersion(string gameRoot)
        {
            string readme = Path.Combine(gameRoot, "_GTR2_HQ_Anniversary_PATCH_README.txt");
            string[] lines;
            try
            {
                lines = File.Exists(readme) ? File.ReadAllLines(readme) : new string[0];
            }
            catch
            {
                return null;
            }
            foreach (string sourceLine in lines)
            {
                string line = (sourceLine ?? string.Empty).Trim();
                if (line.Length < 2 || (line[0] != 'v' && line[0] != 'V')
                    || !char.IsDigit(line[1]))
                {
                    continue;
                }
                int end = 1;
                while (end < line.Length
                    && (char.IsDigit(line[end]) || line[end] == '.'))
                {
                    end++;
                }
                string version = line.Substring(1, end - 1).TrimEnd('.');
                if (version.Length > 0)
                {
                    return version;
                }
            }
            return null;
        }

        /// <summary>
        /// The content\cars directory, without asking SimHub for it: its SDK
        /// exposes no game install path, and guessing at an internal one would
        /// break silently on an update. An explicit environment variable wins, as
        /// it does for the database itself; otherwise Steam's own library records
        /// are read.
        /// </summary>
        private static string ResolveContentDirectory()
        {
            string configured = Environment.GetEnvironmentVariable("AS_DRIVEN_AC_CONTENT");
            if (!string.IsNullOrWhiteSpace(configured))
            {
                return Directory.Exists(configured) ? Path.GetFullPath(configured) : null;
            }
            foreach (string library in SteamLibraries())
            {
                string candidate = Path.Combine(
                    library, "steamapps", "common", "assettocorsa", "content", "cars");
                if (Directory.Exists(candidate))
                {
                    return candidate;
                }
            }
            return null;
        }

        private static IEnumerable<string> SteamLibraries()
        {
            string steam = null;
            try
            {
                using (RegistryKey key = Registry.CurrentUser.OpenSubKey(@"Software\Valve\Steam"))
                {
                    if (key != null)
                    {
                        steam = key.GetValue("SteamPath") as string;
                    }
                }
            }
            catch
            {
                // Registry access can be restricted; treat it as "not found".
            }
            if (string.IsNullOrWhiteSpace(steam))
            {
                yield break;
            }
            steam = steam.Replace('/', '\\');
            yield return steam;

            // Additional libraries live in libraryfolders.vdf as quoted paths.
            string manifest = Path.Combine(steam, "steamapps", "libraryfolders.vdf");
            string[] lines;
            try
            {
                lines = File.Exists(manifest) ? File.ReadAllLines(manifest) : new string[0];
            }
            catch
            {
                yield break;
            }
            foreach (string line in lines)
            {
                string trimmed = line.Trim();
                if (trimmed.IndexOf("\"path\"", StringComparison.OrdinalIgnoreCase) < 0)
                {
                    continue;
                }
                int last = trimmed.LastIndexOf('"');
                int opening = last <= 0 ? -1 : trimmed.LastIndexOf('"', last - 1);
                if (opening < 0)
                {
                    continue;
                }
                string path = trimmed.Substring(opening + 1, last - opening - 1)
                    .Replace("\\\\", "\\");
                if (!string.IsNullOrWhiteSpace(path))
                {
                    yield return path;
                }
            }
        }

        /// <summary>
        /// Digest the car's data. Most Assetto Corsa cars ship it packed in one
        /// data.acd, which conveniently excludes skins and models while including
        /// the gearbox - so a new livery does not invalidate the fingerprint. A
        /// minority keep the directory loose, and those are digested by hashing
        /// each file's relative path and contents in a fixed order, so the result
        /// does not depend on how the filesystem enumerates them.
        /// </summary>
        private static string DigestCarData(string carDirectory, out string scope)
        {
            scope = null;
            string packed = Path.Combine(carDirectory, "data.acd");
            try
            {
                if (File.Exists(packed))
                {
                    scope = "data-acd";
                    using (var sha = SHA256.Create())
                    using (FileStream stream = File.OpenRead(packed))
                    {
                        return ToHex(sha.ComputeHash(stream));
                    }
                }
                string loose = Path.Combine(carDirectory, "data");
                if (!Directory.Exists(loose))
                {
                    return null;
                }
                scope = "loose-data-directory";
                var files = new List<string>(
                    Directory.GetFiles(loose, "*", SearchOption.AllDirectories));
                files.Sort(StringComparer.OrdinalIgnoreCase);
                using (var sha = SHA256.Create())
                {
                    foreach (string file in files)
                    {
                        string relative = file.Substring(loose.Length).TrimStart('\\', '/')
                            .Replace('\\', '/').ToLowerInvariant();
                        byte[] name = Encoding.UTF8.GetBytes(relative + "\n");
                        sha.TransformBlock(name, 0, name.Length, name, 0);
                        byte[] contents = File.ReadAllBytes(file);
                        sha.TransformBlock(contents, 0, contents.Length, contents, 0);
                    }
                    sha.TransformFinalBlock(new byte[0], 0, 0);
                    return ToHex(sha.Hash);
                }
            }
            catch
            {
                scope = null;
                return null;
            }
        }

        /// <summary>
        /// Author and declared version, when the package declares them. Barely
        /// half of an installed library does, so neither is ever identity.
        /// Parsed leniently: ui_car.json is author-written and frequently is not
        /// valid JSON.
        /// </summary>
        private static void ReadUiMetadata(
            string carDirectory, out string author, out string declaredVersion)
        {
            author = null;
            declaredVersion = null;
            string path = Path.Combine(carDirectory, "ui", "ui_car.json");
            string text;
            try
            {
                if (!File.Exists(path))
                {
                    return;
                }
                text = File.ReadAllText(path);
            }
            catch
            {
                return;
            }
            author = ExtractField(text, "author");
            declaredVersion = ExtractField(text, "version");
        }

        private static string ExtractField(string text, string field)
        {
            string marker = "\"" + field + "\"";
            int at = text.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
            if (at < 0)
            {
                return null;
            }
            int colon = text.IndexOf(':', at + marker.Length);
            if (colon < 0)
            {
                return null;
            }
            int open = text.IndexOf('"', colon + 1);
            if (open < 0)
            {
                return null;
            }
            int close = text.IndexOf('"', open + 1);
            if (close < 0)
            {
                return null;
            }
            string value = text.Substring(open + 1, close - open - 1).Trim();
            return value.Length == 0 ? null : value;
        }

        private static string ToHex(byte[] hash)
        {
            var builder = new StringBuilder(hash.Length * 2);
            foreach (byte value in hash)
            {
                builder.Append(value.ToString("x2"));
            }
            return builder.ToString();
        }
    }
}
