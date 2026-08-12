using System;
using System.IO;
using AuthenticControls.Core;
using Newtonsoft.Json.Linq;

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

                Version datasetVersion;
                True(
                    Version.TryParse(database.DatasetVersion, out datasetVersion),
                    "loads a semantic dataset version");
                True(database.RecordCount > 0, "loads curated records");
                Equal(database.RecordCount, database.Cars.Length, "lists every curated car for preview");
                for (int catalogIndex = 1; catalogIndex < database.Cars.Length; catalogIndex++)
                {
                    True(
                        string.Compare(
                            database.Cars[catalogIndex - 1].DisplayName,
                            database.Cars[catalogIndex].DisplayName,
                            StringComparison.OrdinalIgnoreCase) <= 0,
                        "sorts the preview catalog by display name");
                }
                GuidanceSnapshot preview = database.Preview("ams2", "ams2.lister-storm-gtm");
                True(preview.HasMatch, "loads a curated record directly for preview");
                Equal("preview", preview.MatchKind, "labels direct record lookup as preview data");
                Equal("Lister Storm GTM", preview.DisplayName, "previews the requested car");
                Equal("preview-not-found", database.Preview("ams2", "missing.record").MatchStatus, "rejects an unknown preview record");

                GuidanceSnapshot f301 = database.Match("Automobilista2", "Dallara F301");
                True(f301.HasMatch, "matches the exact AMS2 telemetry name");
                Equal("ams2.f301", f301.RecordId, "returns the correct record");
                Equal("telemetry-name", f301.MatchKind, "reports the identity kind");
                Equal("5-speed sequential stick", f301.ShiftType, "formats hardware guidance");
                Equal("sequential", f301.ShiftPattern, "exposes the curated shift pattern");
                Equal("yes", f301.AutoBlip, "exposes simulator auto-blip behavior");
                True(f301.UpshiftGuidance.Contains("Clutch unknown"), "does not invent clutch technique");
                True(f301.UpshiftGuidance.Contains("Throttle lift unknown"), "uses sentence-style technique capitalization");
                True(f301.UpshiftGuidance.Contains("Automatic cut"), "capitalizes automation guidance consistently");

                GuidanceSnapshot c9 = database.Match("Automobilista2", "Sauber Mercedes C9");
                Equal("dogleg-h", c9.ShiftPattern, "preserves dogleg H-pattern evidence");

                GuidanceSnapshot cadillac = database.Match("Automobilista2", "Cadillac DPi-VR");
                Equal("gt-style", cadillac.WheelRimShape, "normalizes the documented GTF1 wheel family");

                GuidanceSnapshot viper = database.Match("Automobilista2", "Dodge Viper GTS-R");
                True(viper.HasMatch, "matches the live Dodge Viper GTS-R identity");
                Equal("ams2.dodge-viper-gts-r", viper.RecordId, "returns the curated Viper record");
                Equal("6-speed sequential stick", viper.ShiftType, "formats the tested Viper shifter");
                Equal("sequential", viper.ShiftPattern, "exposes the Viper sequential pattern");
                Equal("required", viper.StandingStartClutch, "requires the Viper clutch from a stop");
                Equal("yes", viper.ShiftCut, "exposes the observed Viper automatic cut");
                Equal("yes", viper.AutoBlip, "exposes the observed Viper automatic blip");
                Equal("round", viper.WheelRimShape, "uses the period cockpit wheel shape");
                True(viper.UpshiftGuidance.Contains("Clutch not required"), "describes the Viper running upshift clutch");
                True(viper.UpshiftGuidance.Contains("Automatic cut"), "describes the Viper automatic upshift cut");
                True(viper.DownshiftGuidance.Contains("Automatic blip"), "describes the Viper automatic downshift blip");
                True(viper.TechniqueSummary.Contains("Use the clutch to pull away"), "gives actionable Viper start technique");
                True(viper.TechniqueSummary.Contains("automatic cut"), "gives actionable Viper upshift technique");
                True(viper.TechniqueSummary.Contains("automatic throttle blip"), "gives actionable Viper downshift technique");
                Equal(viper.TechniqueSummary, (viper.TechniqueSummaryLine1 + " " + viper.TechniqueSummaryLine2).Trim(), "splits technique guidance without losing text");
                True(viper.TechniqueSummaryLine1.Length <= 125, "keeps the first technique display line compact");
                Equal(viper.TechniqueSummary, (viper.TechniqueSummaryCompactLine1 + " " + viper.TechniqueSummaryCompactLine2).Trim(), "splits compact technique guidance without losing text");
                True(viper.TechniqueSummaryCompactLine1.Length <= 112, "fills the first compact technique line without exceeding its surface");

                GuidanceSnapshot alpine = database.Match("Automobilista2", "Alpine A424");
                True(alpine.HasMatch, "matches the live Alpine A424 identity");
                Equal("ams2.alpine-a424", alpine.RecordId, "returns the curated Alpine record");
                Equal("7-speed paddle shifters", alpine.ShiftType, "formats the tested Alpine transmission");
                Equal("not-required", alpine.StandingStartClutch, "does not require a physical clutch for Alpine hybrid move-off");
                Equal("yes", alpine.ShiftCut, "exposes the reviewed Alpine automatic cut");
                Equal("yes", alpine.AutoBlip, "exposes the directly observed Alpine automatic blip");
                Equal("prototype", alpine.WheelRimShape, "uses the closed prototype-style Alpine rim");
                True(alpine.UpshiftGuidance.Contains("Throttle lift not required"), "describes no-lift Alpine upshifts");
                True(alpine.DownshiftGuidance.Contains("Automatic blip"), "describes the Alpine automatic downshift blip");
                True(alpine.TechniqueSummary.Contains("Pull away without clutch input"), "describes Alpine pull-away technique without assuming a generic aid");
                True(alpine.TechniqueSummary.Contains("Shift with the paddles"), "describes the Alpine shift control");

                GuidanceSnapshot alpineLowDownforce = database.Match(
                    "Automobilista2", "Alpine A424 - Low Downforce");
                True(alpineLowDownforce.HasMatch, "matches the approved Alpine Low Downforce aero identity");
                Equal("ams2.alpine-a424", alpineLowDownforce.RecordId, "inherits Alpine controls for the aero package");
                Equal("telemetry-name", alpineLowDownforce.MatchKind, "keeps the Low Downforce alias exact");

                GuidanceSnapshot ligier = database.Match("Automobilista2", "Ligier JS P217");
                True(ligier.HasMatch, "matches the live Ligier JS P217 identity");
                Equal("ams2.ligier-js-p217", ligier.RecordId, "returns the shared Gen1 and Gen2 Ligier record");
                Equal("6-speed paddle shifters", ligier.ShiftType, "formats the tested Ligier transmission");
                Equal("not-required", ligier.StandingStartClutch, "does not require physical clutch input for Ligier move-off");
                Equal("yes", ligier.ShiftCut, "exposes the directly observed Ligier automatic cut");
                Equal("yes", ligier.AutoBlip, "exposes the directly observed Ligier automatic blip");
                Equal("prototype", ligier.WheelRimShape, "uses the closed prototype-style Ligier rim");

                foreach (string verifiedBatchCar in new[] {
                    "Oreca 07",
                    "Lamborghini SC63",
                    "Ligier JS P320",
                    "Ligier JS P4",
                    "Aston Martin Valkyrie Hypercar",
                    "Audi R8 LMS GT4",
                    "Chevrolet Corvette Z06 GT3.R",
                    "Lamborghini Huracan Super Trofeo EVO2",
                    "Aston Martin Vantage GT4 Evo",
                    "Aston Martin Vantage GTE"
                })
                {
                    GuidanceSnapshot verified = database.Match("Automobilista2", verifiedBatchCar);
                    True(verified.HasMatch, "matches verified batch identity " + verifiedBatchCar);
                    Equal("sequential-paddles", verified.ShiftActuation, "uses paddle shift for " + verifiedBatchCar);
                    Equal("yes", verified.ShiftCut, "exposes automatic cut for " + verifiedBatchCar);
                    Equal("yes", verified.AutoBlip, "exposes automatic blip for " + verifiedBatchCar);
                }

                GuidanceSnapshot oreca = database.Match("Automobilista2", "Oreca 07");
                Equal("ams2.oreca-07", oreca.RecordId, "returns the shared Oreca Gen1 and Gen2 record");
                Equal("6-speed paddle shifters", oreca.ShiftType, "formats the tested Oreca transmission");
                Equal("prototype", oreca.WheelRimShape, "uses the closed prototype-style Oreca rim");
                GuidanceSnapshot orecaLowDownforce = database.Match(
                    "Automobilista2", "Oreca 07 - Low Downforce");
                Equal("ams2.oreca-07", orecaLowDownforce.RecordId, "inherits Oreca controls for the aero package");
                Equal("telemetry-name", orecaLowDownforce.MatchKind, "keeps the Oreca aero alias exact");

                GuidanceSnapshot sc63 = database.Match("Automobilista2", "Lamborghini SC63");
                Equal("7-speed paddle shifters", sc63.ShiftType, "formats the tested SC63 transmission");
                Equal("prototype", sc63.WheelRimShape, "uses the closed prototype-style SC63 rim");
                GuidanceSnapshot sc63LowDownforce = database.Match(
                    "Automobilista2", "Lamborghini SC63 - Low Downforce");
                Equal("ams2.lamborghini-sc63", sc63LowDownforce.RecordId, "inherits SC63 controls for the aero package");

                GuidanceSnapshot p320 = database.Match("Automobilista2", "Ligier JS P320");
                Equal("required", p320.StandingStartClutch, "requires physical clutch input for the P320 standing start");
                Equal("prototype", p320.WheelRimShape, "uses the closed prototype-style P320 rim");

                GuidanceSnapshot p4 = database.Match("Automobilista2", "Ligier JS P4");
                Equal("not-required", p4.StandingStartClutch, "does not require physical clutch input for P4 move-off");
                Equal("prototype", p4.WheelRimShape, "uses the closed prototype-style P4 rim");

                GuidanceSnapshot valkyrie = database.Match("Automobilista2", "Aston Martin Valkyrie Hypercar");
                Equal("7-speed paddle shifters", valkyrie.ShiftType, "formats the tested Valkyrie transmission");
                Equal("prototype", valkyrie.WheelRimShape, "uses the closed prototype-style Valkyrie rim");
                GuidanceSnapshot unobservedValkyrieAero = database.Match(
                    "Automobilista2", "Aston Martin Valkyrie Hypercar - Low Downforce");
                False(unobservedValkyrieAero.HasMatch, "does not invent an unobserved Valkyrie aero alias");

                GuidanceSnapshot audiGt4 = database.Match("Automobilista2", "Audi R8 LMS GT4");
                Equal("7-speed paddle shifters", audiGt4.ShiftType, "formats the tested Audi GT4 transmission");
                Equal("gt-style", audiGt4.WheelRimShape, "uses the open-top Audi GT-style rim");

                GuidanceSnapshot corvetteGt3 = database.Match("Automobilista2", "Chevrolet Corvette Z06 GT3.R");
                Equal("6-speed paddle shifters", corvetteGt3.ShiftType, "formats the tested Corvette GT3 transmission");
                Equal("gt-style", corvetteGt3.WheelRimShape, "uses the open-top Corvette GT-style rim");
                GuidanceSnapshot corvetteLowDownforce = database.Match(
                    "Automobilista2", "Chevrolet Corvette Z06 GT3.R - Low Downforce");
                Equal("ams2.chevrolet-corvette-z06-gt3r", corvetteLowDownforce.RecordId, "inherits Corvette controls for the aero package");

                GuidanceSnapshot huracanEvo2 = database.Match(
                    "Automobilista2", "Lamborghini Huracan Super Trofeo EVO2");
                Equal("gt-style", huracanEvo2.WheelRimShape, "uses the open-top Huracan GT-style rim");
                GuidanceSnapshot huracanPredecessor = database.Match(
                    "Automobilista2", "LamborghiniHuracanLP6202SuperTrofeo");
                False(huracanPredecessor.HasMatch, "does not silently match the earlier Huracan predecessor");

                GuidanceSnapshot vantageGt4 = database.Match("Automobilista2", "Aston Martin Vantage GT4 Evo");
                Equal("6-speed paddle shifters", vantageGt4.ShiftType, "reports the six usable Vantage GT4 ratios");
                Equal("gt-style", vantageGt4.WheelRimShape, "uses the open-top Vantage GT4 rim");

                GuidanceSnapshot vantageGte = database.Match("Automobilista2", "Aston Martin Vantage GTE");
                Equal("6-speed paddle shifters", vantageGte.ShiftType, "formats the tested Vantage GTE transmission");
                Equal("gt-style", vantageGte.WheelRimShape, "uses the open-top Vantage GTE rim");

                foreach (string historicalSequentialCar in new[] {
                    "Lamborghini Murcielago R-GT",
                    "Maserati MC12 GT1",
                    "Lister Storm GTM",
                    "Panoz Esperante GTLM",
                    "Gillet Vertigo Streiff",
                    "Aston Martin DBR9",
                    "Chevrolet Corvette C5-R",
                    "Saleen S7-R GT1",
                    "Milano GT55",
                    "Milano GT36",
                    "Spyker C8 Spyder GT2-R",
                    "TVR Tuscan T400R GT2"
                })
                {
                    GuidanceSnapshot historical = database.Match("Automobilista2", historicalSequentialCar);
                    True(historical.HasMatch, "matches historical sequential identity " + historicalSequentialCar);
                    Equal(6, historical.GearCount, "uses six forward gears for " + historicalSequentialCar);
                    Equal("sequential-stick", historical.ShiftActuation, "uses the cockpit sequential stick for " + historicalSequentialCar);
                    Equal("required", historical.StandingStartClutch, "requires the standing-start clutch for " + historicalSequentialCar);
                    Equal("yes", historical.ShiftCut, "exposes automatic cut for " + historicalSequentialCar);
                    Equal("no", historical.AutoBlip, "does not invent automatic blip for " + historicalSequentialCar);
                    True(historical.DownshiftGuidance.Contains("Manual blip required"), "requires authentic driver blipping for " + historicalSequentialCar);
                    True(historical.TechniqueSummary.Contains("blip the throttle"), "shows actionable manual-blip technique for " + historicalSequentialCar);
                    string expectedRim = historicalSequentialCar == "Lister Storm GTM"
                        || historicalSequentialCar == "Lamborghini Murcielago R-GT"
                        || historicalSequentialCar == "Maserati MC12 GT1"
                        || historicalSequentialCar == "Panoz Esperante GTLM"
                        || historicalSequentialCar == "Gillet Vertigo Streiff"
                        ? "d-shaped"
                        : "round";
                    Equal(expectedRim, historical.WheelRimShape, "uses the observed rim for " + historicalSequentialCar);
                }

                GuidanceSnapshot dbr9LowDownforce = database.Match(
                    "Automobilista2", "Aston Martin DBR9 - Low Downforce");
                Equal("ams2.aston-martin-dbr9", dbr9LowDownforce.RecordId, "inherits DBR9 controls for the aero package");
                GuidanceSnapshot c5rLowDownforce = database.Match(
                    "Automobilista2", "Chevrolet Corvette C5-R - Low Downforce");
                Equal("ams2.chevrolet-corvette-c5-r", c5rLowDownforce.RecordId, "inherits C5-R controls for the aero package");

                GuidanceSnapshot porsche996 = database.Match(
                    "Automobilista2", "Porsche 996 GT3 RSR");
                True(porsche996.HasMatch, "matches the exact Porsche 996 GT3 RSR identity");
                Equal(6, porsche996.GearCount, "uses six Porsche forward gears");
                Equal("sequential-stick", porsche996.ShiftActuation, "uses the Porsche cockpit sequential stick");
                Equal("required", porsche996.StandingStartClutch, "requires the Porsche clutch from rest");
                Equal("yes", porsche996.ShiftCut, "exposes the Porsche automatic cut");
                Equal("yes", porsche996.AutoBlip, "exposes the Porsche automatic blip");
                Equal("round", porsche996.WheelRimShape, "uses the observed Porsche round rim");

                GuidanceSnapshot audiR8Lmp1 = database.Match("Automobilista2", "Audi R8 LMP1");
                Equal("6-speed paddle shifters", audiR8Lmp1.ShiftType, "formats the Audi R8 LMP1 transmission");
                Equal("required", audiR8Lmp1.StandingStartClutch, "requires the Audi R8 LMP1 clutch from rest");
                Equal("yes", audiR8Lmp1.ShiftCut, "exposes the Audi R8 LMP1 automatic cut");
                Equal("yes", audiR8Lmp1.AutoBlip, "exposes the Audi R8 LMP1 automatic blip");
                Equal("yoke", audiR8Lmp1.WheelRimShape, "uses the observed Audi yoke-style rim");

                GuidanceSnapshot courageC60 = database.Match("Automobilista2", "Courage C60 Hybrid");
                Equal("6-speed sequential stick", courageC60.ShiftType, "formats the Courage C60 transmission");
                Equal("yes", courageC60.ShiftCut, "exposes the Courage automatic cut");
                Equal("yes", courageC60.AutoBlip, "exposes the Courage automatic blip");
                Equal("d-shaped", courageC60.WheelRimShape, "uses the observed Courage D-shaped rim");

                GuidanceSnapshot dallaraSp1 = database.Match("Automobilista2", "Dallara SP1");
                Equal("6-speed paddle shifters", dallaraSp1.ShiftType, "uses the animated Dallara paddle actuation");
                Equal("yes", dallaraSp1.ShiftCut, "exposes the Dallara automatic cut");
                Equal("yes", dallaraSp1.AutoBlip, "exposes the Dallara automatic blip");
                Equal("prototype", dallaraSp1.WheelRimShape, "uses the Dallara prototype display rim");

                foreach (string lolaVariant in new[] { "Lola B05/40 V8", "Lola B05/40 Turbo" })
                {
                    GuidanceSnapshot lola = database.Match("Automobilista2", lolaVariant);
                    Equal("6-speed paddle shifters", lola.ShiftType, "formats the Lola transmission for " + lolaVariant);
                    Equal("not-required", lola.StandingStartClutch, "does not require physical clutch input for " + lolaVariant);
                    Equal("yes", lola.ShiftCut, "exposes automatic cut for " + lolaVariant);
                    Equal("yes", lola.AutoBlip, "exposes automatic blip for " + lolaVariant);
                    Equal("d-shaped", lola.WheelRimShape, "uses the D-shaped display rim for " + lolaVariant);
                }
                GuidanceSnapshot lolaV8LowDownforce = database.Match(
                    "Automobilista2", "Lola B05/40 V8 - Low Downforce");
                Equal("ams2.lola-b05-40-v8", lolaV8LowDownforce.RecordId, "inherits Lola V8 controls for the aero package");

                GuidanceSnapshot murcielagoLowDownforce = database.Match(
                    "Automobilista2", "Lamborghini Murcielago R-GT - Low Downforce");
                Equal("ams2.lamborghini-murcielago-r-gt", murcielagoLowDownforce.RecordId, "inherits Murcielago controls for the aero package");
                Equal("telemetry-name", murcielagoLowDownforce.MatchKind, "keeps the Murcielago aero alias exact");

                GuidanceSnapshot mc12LowDownforce = database.Match(
                    "Automobilista2", "Maserati MC12 GT1 - Low Downforce");
                Equal("ams2.maserati-mc12-gt1", mc12LowDownforce.RecordId, "inherits MC12 controls for the aero package");
                Equal("telemetry-name", mc12LowDownforce.MatchKind, "keeps the MC12 aero alias exact");

                GuidanceSnapshot diablo = database.Match("Automobilista2", "Lamborghini Diablo SV-R");
                True(diablo.HasMatch, "matches the exact Diablo SV-R identity");
                Equal("ams2.lamborghini-diablo-sv-r", diablo.RecordId, "returns the curated Diablo record");
                Equal(5, diablo.GearCount, "resolves the Diablo source conflict to five modeled gears");
                Equal("h-pattern", diablo.ShiftActuation, "uses the Diablo H-pattern shifter");
                Equal("dogleg-h", diablo.ShiftPattern, "uses the observed Diablo dogleg gate");
                Equal("required", diablo.StandingStartClutch, "requires the Diablo clutch from rest");
                Equal("no", diablo.ShiftCut, "does not invent automatic Diablo throttle cut");
                Equal("no", diablo.AutoBlip, "does not invent automatic Diablo throttle blip");
                Equal("round", diablo.WheelRimShape, "uses the observed round Diablo rim");
                True(diablo.UpshiftGuidance.Contains("Throttle lift required"), "describes the Diablo lift requirement");
                True(diablo.DownshiftGuidance.Contains("Manual blip required"), "describes the Diablo manual blip requirement");
                True(diablo.TechniqueSummary.Contains("dogleg H-pattern"), "describes the Diablo shifter technique");
                True(diablo.TechniqueSummary.Contains("lift the throttle"), "describes the Diablo upshift technique");
                True(diablo.TechniqueSummary.Contains("blip the throttle"), "describes the Diablo downshift technique");
                Equal(string.Empty, diablo.TechniqueSummaryLine2, "keeps the Diablo technique on one line when it fits");
                Equal("throttle on downshifts.", diablo.TechniqueSummaryCompactLine2, "moves the Diablo ending onto a safe second compact line");

                foreach (string formulaCar in new[] {
                    "Formula V10 Gen2",
                    "Formula Reiza",
                    "Formula Ultimate Hybrid Gen1",
                    "Formula Ultimate Gen2",
                    "Formula USA 2023"
                })
                {
                    GuidanceSnapshot formula = database.Match("Automobilista2", formulaCar);
                    True(formula.HasMatch, "matches curated Formula identity " + formulaCar);
                    Equal("formula", formula.WheelRimShape, "uses Formula rim for " + formulaCar);
                    Equal("sequential-paddles", formula.ShiftActuation, "uses paddle shift for " + formulaCar);
                }

                foreach (string liveFormulaVariant in new[] {
                    "Formula V10 Gen2 (B) - High Downforce",
                    "Formula V10 Gen2 (M) - High Downforce",
                    "Formula Ultimate Hybrid Gen1 - High Downforce",
                    "Formula USA 2023 - High Downforce"
                })
                {
                    GuidanceSnapshot formula = database.Match("Automobilista2", liveFormulaVariant);
                    True(formula.HasMatch, "matches live AMS2 Formula identity " + liveFormulaVariant);
                    Equal("telemetry-name", formula.MatchKind, "keeps live Formula matching exact");
                    Equal("formula", formula.WheelRimShape, "uses Formula rim for live variant " + liveFormulaVariant);
                }

                GuidanceSnapshot v8Gen3 = database.Match(
                    "Automobilista2", "Formula V8 Gen3 - High Downforce");
                True(v8Gen3.HasMatch, "matches the current Formula V8 Gen3 telemetry identity");
                Equal("ams2.formula-reiza", v8Gen3.RecordId, "maps Formula V8 Gen3 to the retained Formula Reiza record");
                Equal("Formula V8 Gen3", v8Gen3.DisplayName, "uses the current official Formula V8 Gen3 display name");

                GuidanceSnapshot hybridGen3 = database.Match(
                    "Automobilista2", "Formula Ultimate Hybrid Gen3 - High Downforce");
                True(hybridGen3.HasMatch, "matches the current Formula Hybrid Gen3 telemetry identity");
                Equal("ams2.formula-ultimate-2022", hybridGen3.RecordId, "maps Formula Hybrid Gen3 to the retained Formula Ultimate Gen2 record");
                Equal("Formula Hybrid Gen3", hybridGen3.DisplayName, "uses the current official Formula Hybrid Gen3 display name");

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

                var popup = new PopupState(TimeSpan.FromSeconds(10));
                var now = new DateTime(2026, 8, 10, 12, 0, 0, DateTimeKind.Utc);
                False(popup.IsVisible(now), "popup begins hidden");
                popup.OnIdentityChanged(true, "Dallara F301", now);
                True(popup.IsVisible(now.AddSeconds(9)), "identity change shows the timed popup");
                False(popup.IsVisible(now.AddSeconds(10)), "timed popup expires at its boundary");
                popup.SetAutomaticDuration(TimeSpan.FromSeconds(12));
                Equal(12.0, popup.AutomaticDurationSeconds, "popup duration is configurable");
                popup.OnIdentityChanged(true, "Unknown Car", now);
                True(popup.IsVisible(now), "unmatched identity also gets a contribution popup");
                popup.Toggle(now);
                False(popup.IsVisible(now), "toggle hides an automatically visible popup");
                popup.Toggle(now);
                True(popup.IsVisible(now.AddHours(1)), "toggle recalls a hidden popup persistently");
                popup.Show();
                True(popup.IsVisible(now.AddHours(1)), "manual show supports a persistent display");
                popup.Hide();
                False(popup.IsVisible(now), "manual hide clears all visibility");
                popup.OnIdentityChanged(false, string.Empty, now);
                False(popup.IsVisible(now), "stopping the game keeps the popup hidden");

                string unmatchedDirectory = Path.Combine(
                    Path.GetTempPath(), "AuthenticControlsTests-" + Guid.NewGuid().ToString("N"));
                string unmatchedPath = Path.Combine(unmatchedDirectory, "unmatched-identities.jsonl");
                try
                {
                    var unmatchedLog = new UnmatchedIdentityLog(unmatchedPath);
                    var observation = new UnmatchedIdentityObservation
                    {
                        ObservedAtUtc = now,
                        GameName = "Automobilista2",
                        GameVersion = "1.6.9.91",
                        CarModel = "Unmapped Formula - High Downforce",
                        CarId = "Unmapped Formula - High Downforce",
                        CarClass = "F-Unmapped_HD",
                        DatasetVersion = database.DatasetVersion,
                        SimHubVersion = "9.11.22"
                    };
                    True(unmatchedLog.Record(observation), "writes a new unmatched identity");
                    False(unmatchedLog.Record(observation), "deduplicates an identity in memory");
                    Equal(1, unmatchedLog.Count, "counts unique unmatched identities");
                    Equal(1, File.ReadAllLines(unmatchedPath).Length, "writes one JSON line");
                    string unmatchedJson = File.ReadAllText(unmatchedPath);
                    True(unmatchedJson.Contains("\"game_version\":\"1.6.9.91\""), "records the exact game version");
                    True(unmatchedJson.Contains("\"car_id\":\"Unmapped Formula - High Downforce\""), "records the raw car id");
                    True(unmatchedJson.Contains("\"car_class\":\"F-Unmapped_HD\""), "records the raw car class");

                    var reloadedLog = new UnmatchedIdentityLog(unmatchedPath);
                    Equal(1, reloadedLog.Count, "reloads persistent deduplication keys");
                    False(reloadedLog.Record(observation), "deduplicates across restarts");
                    observation.GameVersion = "1.6.10.0";
                    True(reloadedLog.Record(observation), "records the same identity for a new game version");
                    Equal(2, reloadedLog.Count, "keeps game versions as separate observations");
                    File.AppendAllText(unmatchedPath, "{invalid-json}" + Environment.NewLine);
                    var tolerantLog = new UnmatchedIdentityLog(unmatchedPath);
                    Equal(2, tolerantLog.Count, "ignores a malformed manually edited line");

                    string verificationDirectory = Path.Combine(
                        unmatchedDirectory, "verification-drafts");
                    var verificationDraft = new VerificationObservationDraft
                    {
                        Simulator = "ams2",
                        GameVersion = "1.6.9.91",
                        ClientVersion = "SimHub 9.11.22; Authentic Controls 0.11.0",
                        ObservedAtUtc = now,
                        Observer = "Test observer",
                        TelemetryName = "Test Prototype",
                        TelemetryClass = "TEST_CLASS",
                        InternalId = "Test Prototype",
                        AutomaticClutch = "disabled",
                        AutomaticShifting = "disabled",
                        AutomaticThrottleBlip = "unavailable",
                        AssistNotes = "No separate auto-blip assist is exposed.",
                        MoveOffWithoutPhysicalClutch = "no",
                        ForwardGears = 6,
                        DirectGearSelectionBehavior = "not-tested",
                        ClutchlessUpshift = "yes",
                        AutomaticCut = "yes",
                        AutomaticCutMethod = "Full-throttle shift accepted with visible interruption.",
                        ClutchlessDownshift = "yes",
                        AutomaticBlip = "yes",
                        AutomaticBlipMethod = "Throttle trace spiked without pedal input.",
                        VisibleShiftActuators = new[] { "paddles", "sequential-stick" },
                        PrimaryShiftActuation = "sequential-paddles",
                        ActuationBasis = "Visible paddles and driver animation.",
                        WheelShape = "prototype",
                        WheelIntegratedDisplay = "yes",
                        WheelShiftLights = "yes",
                        WheelOpenTop = "no",
                        WheelNotes = "Closed prototype rim.",
                        EvidenceNotes = new[] { "Draft only; requires reviewer approval." }
                    };
                    string verificationPath = VerificationObservationWriter.WriteDraft(
                        verificationDirectory,
                        verificationDraft);
                    True(File.Exists(verificationPath), "writes a guided verification draft");
                    JObject verificationJson = JObject.Parse(
                        File.ReadAllText(verificationPath));
                    Equal(
                        "urn:authentic-controls:schema:v1:verification-observation",
                        (string)verificationJson["$schema"],
                        "links the verification schema");
                    Equal("draft", (string)verificationJson["review_status"], "never auto-approves a draft");
                    Equal(6, (int)verificationJson["tests"]["forward_gears"], "records confirmed forward gears");
                    Equal("not-tested", (string)verificationJson["tests"]["direct_gear_selection_behavior"], "records the direct-selection test state");
                    Equal(2, ((JArray)verificationJson["cockpit"]["visible_shift_actuators"]).Count, "records multiple visible actuators");
                    True(
                        ((string)verificationJson["observation_id"]).StartsWith(
                            "ams2.test-prototype.",
                            StringComparison.Ordinal),
                        "creates a stable safe observation-id prefix");

                    bool rejectedMissingObserver = false;
                    verificationDraft.Observer = string.Empty;
                    try
                    {
                        VerificationObservationWriter.CreatePayload(verificationDraft);
                    }
                    catch (InvalidDataException)
                    {
                        rejectedMissingObserver = true;
                    }
                    True(rejectedMissingObserver, "rejects a draft without an observer");

                    var guidedDrive = new GuidedVerificationDrive();
                    guidedDrive.Start(6);
                    Equal("Move-off clutch test", guidedDrive.GetSnapshot().Title, "starts immediately with the first maneuver");
                    Equal(1, guidedDrive.GetSnapshot().StepNumber, "starts on driving test one without an extra introduction");
                    True(guidedDrive.GetSnapshot().PromptLine1.Length < 70, "keeps the move-off first prompt line short");
                    True(guidedDrive.GetSnapshot().PromptLine2.Length < 70, "keeps the move-off second prompt line short");
                    True(guidedDrive.GetSnapshot().Prompt.Contains(guidedDrive.GetSnapshot().PromptLine1), "retains a combined prompt for non-overlay consumers");
                    guidedDrive.AddSample(GuidedSample(now.AddMilliseconds(-100), 0, 100, 0, 0, 0, 0, false));
                    False(guidedDrive.GetSnapshot().ResultReady, "ignores an engine that was already stopped before the move-off test");
                    guidedDrive.AddSample(GuidedSample(now, 0, 100, 0, 1200, 0, 40, true));
                    guidedDrive.AddSample(GuidedSample(now.AddMilliseconds(100), 1, 45, 0, 1300, 3, 60, true));
                    False(guidedDrive.GetSnapshot().ResultReady, "does not accept a momentary initial roll as clutch-free move-off");
                    guidedDrive.AddSample(GuidedSample(now.AddMilliseconds(750), 1, 40, 0, 1350, 5, 65, true));
                    True(guidedDrive.GetSnapshot().ResultReady, "detects sustained clutch-free automatic creep from stationary");
                    guidedDrive.Next();
                    for (int observedGear = 1; observedGear <= 6; observedGear++)
                    {
                        guidedDrive.AddSample(GuidedSample(now, observedGear, 0, 30, 3000, 30, 100, true));
                    }
                    True(guidedDrive.GetSnapshot().ResultReady, "detects the suggested maximum gear");
                    guidedDrive.Next();
                    guidedDrive.AddSample(GuidedSample(now, 2, 55, 90, 5000, 70, 220, true));
                    guidedDrive.AddSample(GuidedSample(now.AddMilliseconds(50), 2, 70, 90, 5100, 72, 40, true));
                    guidedDrive.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 45, 90, 4200, 74, 35, true));
                    True(guidedDrive.GetSnapshot().ResultReady, "detects a full-throttle clutchless upshift");
                    guidedDrive.Next();
                    guidedDrive.AddSample(GuidedSample(now, 4, 60, 0, 4500, 80, 100, true));
                    guidedDrive.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 35, 25, 4000, 78, 90, true));
                    True(guidedDrive.GetSnapshot().ResultReady, "detects a clutchless downshift and throttle spike");
                    guidedDrive.Next();
                    GuidedDriveResults guidedResults = guidedDrive.GetResults();
                    True(guidedDrive.GetSnapshot().Completed, "finishes after the positive automatic-blip path");
                    Equal("yes", guidedResults.MoveOffWithoutPhysicalClutch, "prefills clutch-free move-off");
                    Equal(6, guidedResults.ForwardGears.Value, "prefills observed forward gears");
                    Equal("not-tested", guidedResults.DirectGearSelection, "does not infer direct H-pattern selection from gear telemetry alone");
                    Equal("yes", guidedResults.ClutchlessUpshift, "prefills accepted clutchless upshift");
                    Equal("yes", guidedResults.AutomaticCut, "prefills telemetry-supported automatic cut");
                    Equal("yes", guidedResults.ClutchlessDownshift, "prefills accepted clutchless downshift");
                    Equal("yes", guidedResults.AutomaticBlip, "prefills telemetry-supported automatic blip");
                    True(guidedResults.EvidenceNote.Contains("internal/automatic clutch state"), "documents vehicle clutch telemetry without treating it as pedal input");
                    guidedDrive.Next();
                    False(guidedDrive.GetSnapshot().Visible, "closes the completed in-sim prompt");
                    True(guidedDrive.GetSnapshot().Completed, "keeps completed results available for settings review after closing the prompt");

                    var moveOffStall = new GuidedVerificationDrive();
                    moveOffStall.Start(null);
                    moveOffStall.AddSample(GuidedSample(now, 0, 0, 0, 0, 0, 0, false));
                    moveOffStall.AddSample(GuidedSample(now.AddMilliseconds(100), 0, 0, 0, 1200, 0, 30, true));
                    moveOffStall.AddSample(GuidedSample(now.AddMilliseconds(200), 1, 0, 20, 0, 0, 0, false));
                    True(moveOffStall.GetSnapshot().ResultReady, "detects a stall only after first observing the engine running");
                    True(moveOffStall.GetSnapshot().Result.Contains("standing-start clutch is required"), "reports the post-start stall as a standing-start clutch requirement");

                    var rollingStall = new GuidedVerificationDrive();
                    rollingStall.Start(null);
                    rollingStall.AddSample(GuidedSample(now, 0, 0, 0, 1200, 0, 30, true));
                    rollingStall.AddSample(GuidedSample(now.AddMilliseconds(100), 1, 40, 20, 900, 3, 20, true));
                    False(rollingStall.GetSnapshot().ResultReady, "waits before accepting initial movement");
                    rollingStall.AddSample(GuidedSample(now.AddMilliseconds(200), 1, 0, 20, 0, 2, 0, false));
                    True(rollingStall.GetSnapshot().ResultReady, "rejects brief movement followed by an immediate stall");
                    False(rollingStall.GetSnapshot().ResultSuccessful, "classifies rolling stall as clutch required");
                    True(rollingStall.GetSnapshot().Result.Contains("rolled briefly"), "explains why rolling stall is not clutch-free move-off");

                    var skippedAutomaticTests = new GuidedVerificationDrive();
                    skippedAutomaticTests.Start(null);
                    skippedAutomaticTests.Skip();
                    skippedAutomaticTests.Skip();
                    skippedAutomaticTests.Skip();
                    skippedAutomaticTests.AddSample(GuidedSample(now, 2, 0, 80, 4500, 60, 150, true));
                    skippedAutomaticTests.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 0, 20, 3900, 62, 140, true));
                    skippedAutomaticTests.Next();
                    skippedAutomaticTests.Skip();
                    skippedAutomaticTests.AddSample(GuidedSample(now, 4, 0, 0, 4300, 70, 120, true));
                    skippedAutomaticTests.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 0, 25, 3800, 68, 115, true));
                    skippedAutomaticTests.Next();
                    GuidedDriveResults skippedResults = skippedAutomaticTests.GetResults();
                    Equal("not-tested", skippedResults.AutomaticCut, "does not infer no automatic cut when its test was skipped");
                    Equal("not-tested", skippedResults.AutomaticBlip, "does not infer no automatic blip when its test was skipped");
                }
                finally
                {
                    if (Directory.Exists(unmatchedDirectory))
                    {
                        Directory.Delete(unmatchedDirectory, true);
                    }
                }

                Equal("1.6.9.91", VersionText.Normalize("1, 6, 9, 91"), "normalizes comma-separated executable versions");
                Equal("9.11.22", VersionText.ParseSimHubStartupLine(
                    "[2026-08-10 16:05:45,598] INFO - Starting SimHub v9.11.22 (build time : 31/07/2026)"),
                    "extracts the real SimHub product version from its startup log");
                Equal("unknown", VersionText.ParseSimHubStartupLine("no version here"), "preserves unknown when a startup version is unavailable");

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

        private static GuidedTelemetrySample GuidedSample(
            DateTime timestamp,
            int gear,
            double clutch,
            double throttle,
            double rpm,
            double speedKmh,
            double torque,
            bool engineStarted)
        {
            return new GuidedTelemetrySample
            {
                TimestampUtc = timestamp,
                Gear = gear,
                Clutch = clutch,
                Throttle = throttle,
                Rpm = rpm,
                SpeedKmh = speedKmh,
                EngineTorque = torque,
                EngineStarted = engineStarted
            };
        }
    }
}
