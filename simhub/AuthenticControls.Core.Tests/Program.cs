using System;
using System.IO;
using AuthenticControls.Core;

namespace AuthenticControls.Core.Tests
{
    internal static class Program
    {
        private static int _assertions;

        private static int Main(string[] args)
        {
            try
            {
                string repositoryRoot = args.Length > 0
                    ? Path.GetFullPath(args[0])
                    : Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", ".."));
                string dataDirectory = Path.Combine(repositoryRoot, "data", "v1");
                AuthenticControlsDatabase database = AuthenticControlsDatabase.Load(dataDirectory);

                Equal("0.2.0", database.DatasetVersion, "loads dataset version");
                Equal(10, database.RecordCount, "loads all curated records");

                GuidanceSnapshot f301 = database.Match("Automobilista2", "Dallara F301");
                True(f301.HasMatch, "matches the exact AMS2 telemetry name");
                Equal("ams2.f301", f301.RecordId, "returns the correct record");
                Equal("telemetry-name", f301.MatchKind, "reports the identity kind");
                Equal("5-speed sequential stick", f301.ShiftType, "formats hardware guidance");
                Equal("yes", f301.AutoBlip, "exposes simulator auto-blip behavior");
                True(f301.UpshiftGuidance.Contains("clutch unknown"), "does not invent clutch technique");

                GuidanceSnapshot wrongCase = database.Match("Automobilista2", "dallara f301");
                False(wrongCase.HasMatch, "matching is case-sensitive and exact");
                Equal("unmatched", wrongCase.MatchStatus, "reports unmatched telemetry");

                GuidanceSnapshot unsupported = database.Match("Other Simulator", "Dallara F301");
                Equal("unsupported-game", unsupported.MatchStatus, "gates by simulator");

                var session = new SessionState(database);
                True(session.Update(true, "Automobilista2", "Dallara F301"), "detects first identity");
                Equal(1, session.Current.PopupRevision, "increments popup revision for a match");
                False(session.Update(true, "Automobilista2", "Dallara F301"), "ignores unchanged identity");
                True(session.Update(true, "Automobilista2", "Unknown Car"), "detects a changed identity");
                False(session.Current.HasMatch, "unknown car clears the previous match");
                Equal(string.Empty, session.Current.RecordId, "unknown car cannot retain a stale record");
                Equal(1, session.Current.PopupRevision, "unmatched identity does not request a popup");

                Console.WriteLine("PASS: " + _assertions + " Authentic Controls .NET assertions");
                return 0;
            }
            catch (Exception exception)
            {
                Console.Error.WriteLine("FAIL: " + exception.Message);
                return 1;
            }
        }

        private static void True(bool value, string label)
        {
            _assertions++;
            if (!value)
            {
                throw new InvalidOperationException(label);
            }
        }

        private static void False(bool value, string label)
        {
            True(!value, label);
        }

        private static void Equal<T>(T expected, T actual, string label)
        {
            _assertions++;
            if (!object.Equals(expected, actual))
            {
                throw new InvalidOperationException(
                    label + ": expected '" + expected + "', got '" + actual + "'");
            }
        }
    }
}
