using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using AsDriven.Core;

namespace AsDriven.Plugin
{
    /// <summary>
    /// Downloads a release only after the driver chooses to, verifies the
    /// manifest's SHA-256, and starts a local helper which waits for SimHub to
    /// exit before invoking the packaged rollback-capable installer.
    /// </summary>
    internal static class UpdateInstall
    {
        internal const int TimeoutMilliseconds = 120000;
        private const long MaximumPackageBytes = 512L * 1024L * 1024L;

        internal static string DownloadAndSchedule(UpdateAvailability update)
        {
            if (update == null || !update.HasInstallPackage)
            {
                throw new InvalidOperationException(
                    "This update does not provide a verified automatic-install package.");
            }

            string workRoot = Path.Combine(
                Path.GetTempPath(), "AsDrivenUpdate-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(workRoot);
            string packagePath = Path.Combine(workRoot, "As-Driven-update.zip");
            string helperPath = Path.Combine(workRoot, "Install-After-SimHub-Closes.ps1");
            try
            {
                Download(update.PackageUrl, packagePath);
                string actualHash = Sha256(packagePath);
                if (!actualHash.Equals(update.PackageSha256, StringComparison.OrdinalIgnoreCase))
                {
                    throw new InvalidDataException(
                        "The downloaded package failed its SHA-256 check. Nothing was installed.");
                }

                Process current = Process.GetCurrentProcess();
                string simHubExecutable = current.MainModule == null
                    ? string.Empty
                    : current.MainModule.FileName;
                if (string.IsNullOrWhiteSpace(simHubExecutable)
                    || !File.Exists(simHubExecutable))
                {
                    throw new InvalidOperationException(
                        "The running SimHub executable could not be located.");
                }
                string simHubRoot = Path.GetDirectoryName(simHubExecutable);
                File.WriteAllText(helperPath, HelperScript, new UTF8Encoding(false));

                var start = new ProcessStartInfo
                {
                    FileName = "powershell.exe",
                    Arguments = "-NoProfile -ExecutionPolicy Bypass -File "
                        + Quote(helperPath)
                        + " -ZipPath " + Quote(packagePath)
                        + " -SimHubProcessId " + current.Id
                        + " -SimHubExecutable " + Quote(simHubExecutable)
                        + " -SimHubInstallPath " + Quote(simHubRoot)
                        + " -WorkingRoot " + Quote(workRoot),
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden,
                };
                Process helper = Process.Start(start);
                if (helper == null)
                {
                    throw new InvalidOperationException("The update installer could not be started.");
                }
                return "Package downloaded and verified. Close SimHub to install it; "
                    + "the installer will request administrator approval and restart SimHub when finished.";
            }
            catch
            {
                TryDelete(workRoot);
                throw;
            }
        }

        private static void Download(string url, string target)
        {
            var request = (HttpWebRequest)WebRequest.Create(url);
            request.Method = "GET";
            request.Timeout = TimeoutMilliseconds;
            request.ReadWriteTimeout = TimeoutMilliseconds;
            request.UserAgent = "AsDriven";
            request.AllowAutoRedirect = true;
            using (var response = (HttpWebResponse)request.GetResponse())
            {
                if (response.ResponseUri == null
                    || response.ResponseUri.Scheme != Uri.UriSchemeHttps)
                {
                    throw new WebException("The package download left https.");
                }
                if (response.ContentLength > MaximumPackageBytes)
                {
                    throw new InvalidDataException("The update package is larger than 512 MiB.");
                }
                using (Stream input = response.GetResponseStream())
                using (var output = new FileStream(target, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    if (input == null)
                    {
                        throw new InvalidDataException("The package endpoint returned nothing.");
                    }
                    var buffer = new byte[81920];
                    long total = 0;
                    int read;
                    while ((read = input.Read(buffer, 0, buffer.Length)) > 0)
                    {
                        total += read;
                        if (total > MaximumPackageBytes)
                        {
                            throw new InvalidDataException("The update package is larger than 512 MiB.");
                        }
                        output.Write(buffer, 0, read);
                    }
                }
            }
        }

        private static string Sha256(string path)
        {
            using (var stream = File.OpenRead(path))
            using (SHA256 hash = SHA256.Create())
            {
                return BitConverter.ToString(hash.ComputeHash(stream))
                    .Replace("-", string.Empty).ToLowerInvariant();
            }
        }

        private static string Quote(string value)
        {
            if (value == null || value.IndexOf('"') >= 0)
            {
                throw new InvalidOperationException("An update path contains an unsupported quote.");
            }
            return "\"" + value + "\"";
        }

        private static void TryDelete(string path)
        {
            try
            {
                if (Directory.Exists(path))
                {
                    Directory.Delete(path, true);
                }
            }
            catch
            {
                // The useful download/install error must not be hidden by cleanup.
            }
        }

        private const string HelperScript = @"
param(
    [Parameter(Mandatory = $true)][string]$ZipPath,
    [Parameter(Mandatory = $true)][int]$SimHubProcessId,
    [Parameter(Mandatory = $true)][string]$SimHubExecutable,
    [Parameter(Mandatory = $true)][string]$SimHubInstallPath,
    [Parameter(Mandatory = $true)][string]$WorkingRoot
)
$ErrorActionPreference = 'Stop'
try {
    Wait-Process -Id $SimHubProcessId -ErrorAction SilentlyContinue
    $extractRoot = Join-Path $WorkingRoot 'extracted'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        if ($archive.Entries.Count -gt 20000) { throw 'The update package contains too many files.' }
        [long]$expandedBytes = 0
        foreach ($entry in $archive.Entries) {
            $expandedBytes += [long]$entry.Length
            if ($expandedBytes -gt 1073741824) { throw 'The expanded update exceeds 1 GiB.' }
            $entryPath = $entry.FullName.Replace('/', '\')
            if ($entryPath.Contains(':') -or [System.IO.Path]::IsPathRooted($entryPath) -or
                $entryPath.Split('\') -contains '..') {
                throw ('The update package contains an unsafe path: ' + $entry.FullName)
            }
        }
    }
    finally { $archive.Dispose() }
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $extractRoot
    $roots = @(Get-ChildItem -LiteralPath $extractRoot -Directory)
    if ($roots.Count -ne 1) { throw 'The update package must contain exactly one root directory.' }
    $manifestPath = Join-Path $roots[0].FullName 'release-manifest.json'
    $installerPath = Join-Path $roots[0].FullName 'simhub\install.ps1'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $installerPath -PathType Leaf)) {
        throw 'The verified update package does not contain the As Driven installer.'
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ([string]$manifest.package_format -ne 'as-driven-simhub' -or
        [string]$manifest.package_format_version -ne '1.0.0') {
        throw 'The update package format is not supported.'
    }
    $arguments = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ([char]34 + $installerPath + [char]34),
        '-SimHubInstallPath', ([char]34 + $SimHubInstallPath + [char]34)
    )
    $installer = Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -PassThru -ArgumentList $arguments
    if ($installer.ExitCode -ne 0) { throw ('The installer exited with code ' + $installer.ExitCode + '.') }
    Start-Process -FilePath $SimHubExecutable
}
catch {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        $_.Exception.Message,
        'As Driven update was not installed',
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null
}
finally {
    Remove-Item -LiteralPath $WorkingRoot -Recurse -Force -ErrorAction SilentlyContinue
}
";
    }
}
