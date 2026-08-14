using System;
using System.Drawing;
using System.IO;
using AsDriven.Core;
using Newtonsoft.Json.Linq;

namespace AsDriven.Core.Tests
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
                AsDrivenDatabase database = AsDrivenDatabase.Load(dataDirectory);

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
                True(f301.UpshiftGuidance.Contains("Clutch not required"), "exposes verified running-shift clutch technique");
                True(f301.UpshiftGuidance.Contains("Throttle lift not required"), "exposes verified automatic-cut technique");
                True(f301.UpshiftGuidance.Contains("Automatic cut"), "capitalizes automation guidance consistently");

                GuidanceSnapshot c9 = database.Match("Automobilista2", "Sauber Mercedes C9");
                Equal("dogleg-h", c9.ShiftPattern, "preserves dogleg H-pattern evidence");

                GuidanceSnapshot cadillac = database.Match("Automobilista2", "Cadillac DPi-VR");
                Equal("prototype", cadillac.WheelRimShape, "uses the verified current cockpit wheel category");

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
                True(viper.TechniqueSummaryLine1.Length > 0, "provides a detailed technique first line");
                True(viper.TechniqueSummaryCompactLine1.Length > 0, "provides a compact technique first line");
                AssertOverlayTextFits(viper, "Viper overlay text");

                foreach (CarCatalogEntry catalogEntry in database.Cars)
                {
                    AssertOverlayTextFits(
                        database.Preview(catalogEntry.Simulator, catalogEntry.RecordId),
                        "overlay text fits " + catalogEntry.RecordId);
                }

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

                GuidanceSnapshot roadValkyrie = database.Match("Automobilista2", "Aston Martin Valkyrie");
                Equal("ams2.aston-martin-valkyrie", roadValkyrie.RecordId, "keeps the road Valkyrie distinct from the race car");
                Equal("7-speed paddle shifters", roadValkyrie.ShiftType, "formats the road Valkyrie transmission");
                Equal("gt-style", roadValkyrie.WheelRimShape, "uses the observed road Valkyrie rim category");

                GuidanceSnapshot gt2Stradale = database.Match("Automobilista2", "Maserati GT2 Stradale");
                Equal("8-speed paddle shifters", gt2Stradale.ShiftType, "formats the GT2 Stradale dual-clutch interface");
                Equal("not-required", gt2Stradale.StandingStartClutch, "models automated GT2 Stradale pull-away");

                foreach (string promotedIdentity in new[] {
                    "Ligier JS2 R",
                    "Lamborghini Miura SV",
                    "Lamborghini Revuelto",
                    "Audi R8 V10 GT",
                    "Dodge Viper ACR",
                    "BMW M3 E46 GTR",
                    "Maserati GranSport Trofeo",
                    "Stock USA Gen1 - Speedway",
                    "Stock USA Gen2 - Superspeedway",
                    "Stock USA Gen3 - Superspeedway"
                })
                {
                    GuidanceSnapshot promoted = database.Match("Automobilista2", promotedIdentity);
                    True(promoted.HasMatch, "matches exact guided identity " + promotedIdentity);
                    Equal("telemetry-name", promoted.MatchKind, "uses exact telemetry identity for " + promotedIdentity);
                }

                Equal(7, database.Match("Automobilista2", "Audi R8 V10 GT").GearCount, "uses the later seven-speed R8 GT generation");
                Equal("h-pattern", database.Match("Automobilista2", "Stock USA Gen1 - Speedway").ShiftActuation, "uses Gen1 H-pattern hardware");
                Equal("sequential-stick", database.Match("Automobilista2", "Stock USA Gen3 - Superspeedway").ShiftActuation, "uses Gen3 sequential-stick hardware");
                False(database.Match("Automobilista2", "Stock USA Gen3").HasMatch, "does not invent an untested generic Gen3 alias");

                foreach (string renaultFormula in new[] {
                    "Renault R25 - High Downforce",
                    "Renault R26 - High Downforce",
                    "Renault R28 - High Downforce"
                })
                {
                    GuidanceSnapshot renault = database.Match("Automobilista2", renaultFormula);
                    True(renault.HasMatch, "matches exact Renault formula identity " + renaultFormula);
                    Equal("sequential-paddles", renault.ShiftActuation, "uses Renault formula paddles for " + renaultFormula);
                    Equal("required", renault.StandingStartClutch, "requires Renault formula standing-start clutch for " + renaultFormula);
                    Equal("yes", renault.ShiftCut, "exposes detected automatic cut for " + renaultFormula);
                    Equal("yes", renault.AutoBlip, "exposes detected automatic blip for " + renaultFormula);
                    Equal("formula", renault.WheelRimShape, "uses Formula rim for " + renaultFormula);
                }

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

                GuidanceSnapshot saleenOverlay = database.Match(
                    "Automobilista2", "Saleen S7-R GT1");
                Equal(
                    saleenOverlay.TechniqueSummary,
                    (saleenOverlay.TechniqueSummaryLine1 + " "
                        + saleenOverlay.TechniqueSummaryLine2).Trim(),
                    "keeps the complete Saleen technique sentence across the Detailed card");
                True(
                    !saleenOverlay.TechniqueSummaryLine1.EndsWith("...", StringComparison.Ordinal)
                        && !saleenOverlay.TechniqueSummaryLine2.EndsWith("...", StringComparison.Ordinal),
                    "does not truncate the Saleen technique despite available second-line space");

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
                Equal(diablo.TechniqueSummary, (diablo.TechniqueSummaryLine1 + " " + diablo.TechniqueSummaryLine2).Trim(), "preserves full detailed Diablo technique when it fits");
                AssertOverlayTextFits(diablo, "Diablo overlay text");

                foreach (string formulaCar in new[] {
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
                    Path.GetTempPath(), "AsDrivenTests-" + Guid.NewGuid().ToString("N"));
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
                        ClientVersion = "SimHub 9.11.22; As Driven 0.11.0",
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
                        "urn:as-driven:schema:v1:verification-observation",
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

                    var transientThrottleCut = new GuidedVerificationDrive();
                    transientThrottleCut.Start(null);
                    transientThrottleCut.Skip();
                    transientThrottleCut.Skip();
                    transientThrottleCut.AddSample(GuidedSample(now, 2, 0, 90, 5000, 70, 150, true));
                    transientThrottleCut.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 0, 20, 4300, 72, 100, true));
                    False(transientThrottleCut.GetSnapshot().ResultReady, "waits briefly for interrupted throttle telemetry to recover");
                    transientThrottleCut.AddSample(GuidedSample(now.AddMilliseconds(200), 3, 0, 90, 4200, 74, 95, true));
                    True(transientThrottleCut.GetSnapshot().ResultReady, "detects a brief shift-local throttle interruption and recovery");
                    transientThrottleCut.Next();
                    Equal("yes", transientThrottleCut.GetResults().AutomaticCut, "records a controlled transient throttle interruption as automatic cut");
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

                Equal(10.0, PopupPreferences.NormalizeDuration(double.NaN), "falls back to the default popup duration for a nonsense value");
                Equal(10.0, PopupPreferences.NormalizeDuration(double.PositiveInfinity), "falls back to the default popup duration for infinity");
                Equal(1.0, PopupPreferences.NormalizeDuration(0), "clamps a popup duration up to the supported minimum");
                Equal(1.0, PopupPreferences.NormalizeDuration(-30), "clamps a negative popup duration to the minimum");
                Equal(60.0, PopupPreferences.NormalizeDuration(900), "clamps a popup duration down to the supported maximum");
                Equal(12.0, PopupPreferences.NormalizeDuration(11.6), "rounds a fractional popup duration");
                Equal(7.0, PopupPreferences.NormalizeDuration(7), "keeps a supported popup duration");

                Equal("compact", PopupPreferences.NormalizeSize(null), "falls back to the default popup size when unset");
                Equal("compact", PopupPreferences.NormalizeSize("   "), "falls back to the default popup size when blank");
                Equal("compact", PopupPreferences.NormalizeSize("enormous"), "falls back to the default popup size for an unrenderable value");
                Equal("glance", PopupPreferences.NormalizeSize("  GLANCE "), "accepts a supported popup size regardless of case or padding");
                Equal("detailed", PopupPreferences.NormalizeSize("detailed"), "keeps a supported popup size");

                True(
                    PreviewRules.ShouldLeavePreview(true, true, "Porsche 963", "BMW M Hybrid V8"),
                    "leaves preview when the game reports a different live car");
                False(
                    PreviewRules.ShouldLeavePreview(true, true, "Porsche 963", "Porsche 963"),
                    "stays in preview when the live car matches the previewed car");
                False(
                    PreviewRules.ShouldLeavePreview(true, true, "Porsche 963", "   "),
                    "treats a blank live identity as no car change, so loading does not cancel preview");
                False(
                    PreviewRules.ShouldLeavePreview(true, false, "Porsche 963", "BMW M Hybrid V8"),
                    "keeps preview available while the game is not running");
                False(
                    PreviewRules.ShouldLeavePreview(false, true, string.Empty, "BMW M Hybrid V8"),
                    "does nothing when preview is not active");

                True(PreviewRules.IsAsDrivenLayoutName("As Driven"), "recognizes the plugin's own overlay layout");
                True(PreviewRules.IsAsDrivenLayoutName("as driven 5120x1440"), "recognizes its layout regardless of case");
                False(PreviewRules.IsAsDrivenLayoutName("My Custom Dash"), "never claims an unrelated user overlay");
                False(PreviewRules.IsAsDrivenLayoutName(null), "treats a missing layout name as unrelated");
                Equal("As Driven", PreviewRules.PreferredLayoutName(1920), "prefers the standard layout on an ordinary desktop");
                Equal("As Driven 5120x1440", PreviewRules.PreferredLayoutName(5120), "prefers the wide layout on a triple-width desktop");

                Equal("sequential", ShiftPatternRules.DerivedGate("sequential-paddles"), "derives a sequential gate from paddles");
                Equal("sequential", ShiftPatternRules.DerivedGate("sequential-stick"), "derives a sequential gate from a sequential stick");
                Equal("automatic-gate", ShiftPatternRules.DerivedGate("automatic-lever"), "derives an automatic gate from an automatic lever");
                Equal("direct", ShiftPatternRules.DerivedGate("direct-selection"), "derives a direct gate from direct selection");
                // The whole point of the field: standard and dogleg are both
                // legitimate, so the driver reports which one the cockpit shows.
                True(ShiftPatternRules.DerivedGate("h-pattern") == null, "never guesses the gate of an H-pattern car");
                True(ShiftPatternRules.DerivedGate("unknown") == null, "derives no gate from an unknown mechanism");
                // A car with no automatic blip may still have an unknown manual
                // blip. The two must stay separate, or the overlay turns an
                // unknown into an instruction to blip.
                GuidanceSnapshot retro = database.Preview("ams2", "ams2.formula-retro-v12");
                Equal("no", retro.AutoBlip, "Formula Retro V12 has no automatic blip in the simulator");
                Equal("unknown", retro.ManualBlip, "but its manual downshift blip is not established");
                GuidanceSnapshot brabham = database.Preview("ams2", "ams2.brabham-bt26a");
                Equal("no", brabham.AutoBlip, "Brabham BT26A also has no automatic blip");
                Equal("required", brabham.ManualBlip, "and its dog box does require a driver blip");
                Equal("required", brabham.ThrottleLift, "the driver lifts to upshift the Brabham");

                True(ShiftPatternRules.IsDerivedGate("sequential"), "treats a sequential gate as mechanism-implied");
                False(ShiftPatternRules.IsDerivedGate("dogleg-h"), "never discards an observed dogleg gate as mechanism-implied");
                False(ShiftPatternRules.IsDerivedGate("standard-h"), "never discards an observed standard gate as mechanism-implied");

                string syntheticRoot = Path.Combine(
                    Path.GetTempPath(), "AsDrivenTests-" + Guid.NewGuid().ToString("N"));
                try
                {
                    // An unverified upshift lift with no automatic cut must say so
                    // instead of silently omitting upshift guidance.
                    GuidanceSnapshot unverified = LoadSyntheticGuidance(
                        syntheticRoot, "Unverified Upshift Car", "unknown", "no", "sequential-stick");
                    True(
                        unverified.TechniqueSummary.Contains("upshift throttle technique is not yet verified"),
                        "discloses an unverified upshift technique instead of omitting it");

                    // An override makes guidance use the simulator's value while the
                    // record keeps the real car's. Without this the popup would tell
                    // a PDK driver no clutch is needed in a sim that stalls without it.
                    string clutchOverride =
                        "[{\"path\":\"/authentic_controls/transmission/standing_start_clutch\","
                        + "\"value\":\"required\",\"condition\":\"AMS2 requires clutch input to move off.\","
                        + "\"source_refs\":[\"test.source\"],"
                        + "\"confidence\":{\"level\":\"verified\",\"basis\":\"observed\"}}]";
                    GuidanceSnapshot overridden = LoadSyntheticGuidance(
                        syntheticRoot, "Override Car", "not-required", "yes", "sequential-paddles",
                        clutchOverride);
                    Equal("required", overridden.StandingStartClutch,
                        "applies a simulator override to the standing-start clutch");
                    True(
                        overridden.TechniqueSummary.Contains("Use the clutch to pull away"),
                        "derives technique guidance from the overridden value");

                    GuidanceSnapshot notOverridden = LoadSyntheticGuidance(
                        syntheticRoot, "Plain Car", "not-required", "yes", "sequential-paddles");
                    Equal("not-required", notOverridden.StandingStartClutch,
                        "leaves a record without overrides untouched");

                    // An automatic gearbox has no upshift technique to describe,
                    // so it must stay silent rather than claim it is unverified.
                    GuidanceSnapshot automatic = LoadSyntheticGuidance(
                        syntheticRoot, "Automatic Car", "not-applicable", "unknown", "automatic-lever");
                    False(
                        automatic.TechniqueSummary.Contains("not yet verified"),
                        "keeps an automatic gearbox silent about upshift throttle technique");
                }
                finally
                {
                    if (Directory.Exists(syntheticRoot))
                    {
                        Directory.Delete(syntheticRoot, true);
                    }
                }

                Console.WriteLine("PASS: " + _assertions + " As Driven .NET assertions");
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

        private static void AssertOverlayTextFits(GuidanceSnapshot snapshot, string label)
        {
            // Dash Studio uses Segoe UI. GDI's typographic measurement includes
            // glyph overhang and makes this a deliberately stricter fitting check
            // than the bounding width handed to each generated TextItem.
            True(FitsSegoeUi(snapshot.TechniqueSummaryLine1, 764, 13.5f, false), label + " detailed technique line 1 fits");
            True(FitsSegoeUi(snapshot.TechniqueSummaryLine2, 764, 13.5f, false), label + " detailed technique line 2 fits");
            True(FitsSegoeUi(snapshot.TechniqueSummaryCompactLine1, 472, 9.5f, false), label + " compact technique line 1 fits");
            True(FitsSegoeUi(snapshot.TechniqueSummaryCompactLine2, 472, 9.5f, false), label + " compact technique line 2 fits");
            True(FitsSegoeUi(snapshot.OverlayCarNameDetailed, 534, 21.5f, true), label + " detailed car name fits");
            True(FitsSegoeUi(snapshot.OverlayCarClassDetailed, 534, 12f, true), label + " detailed car class fits");
            True(FitsSegoeUi(snapshot.OverlayCarNameCompact, 310, 17.5f, true), label + " compact car name fits");
            True(FitsSegoeUi(snapshot.OverlayCarClassCompact, 310, 9.5f, true), label + " compact car class fits");
            True(FitsSegoeUi(snapshot.OverlayCarNameGlance, 174, 15f, true), label + " glance car name fits");
            AssertTechniqueDisplay(snapshot.TechniqueSummary, snapshot.TechniqueSummaryLine1, snapshot.TechniqueSummaryLine2, label + " detailed technique");
            AssertTechniqueDisplay(snapshot.TechniqueSummary, snapshot.TechniqueSummaryCompactLine1, snapshot.TechniqueSummaryCompactLine2, label + " compact technique");
            AssertFittedPrefix(snapshot.DisplayName, snapshot.OverlayCarNameDetailed, label + " detailed car name");
            AssertFittedPrefix(snapshot.DisplayName, snapshot.OverlayCarNameCompact, label + " compact car name");
            AssertFittedPrefix(snapshot.DisplayName, snapshot.OverlayCarNameGlance, label + " glance car name");
            AssertFittedPrefix(snapshot.CarClass, snapshot.OverlayCarClassDetailed, label + " detailed car class");
            AssertFittedPrefix(snapshot.CarClass, snapshot.OverlayCarClassCompact, label + " compact car class");
        }

        private static void AssertTechniqueDisplay(string summary, string line1, string line2, string label)
        {
            string displayed = (line1 + " " + line2).Trim();
            True(line1.Length >= Math.Min(12, summary.Length), label + " retains a meaningful first line");
            AssertFittedPrefix(summary, line1, label + " starts at the guidance beginning");
            if (!displayed.EndsWith("...", StringComparison.Ordinal))
            {
                Equal(summary, displayed, label + " preserves all guidance when no ellipsis is required");
            }
        }

        private static void AssertFittedPrefix(string original, string fitted, string label)
        {
            if (string.IsNullOrEmpty(original))
            {
                Equal(string.Empty, fitted, label + " remains empty");
                return;
            }
            string prefix = fitted.EndsWith("...", StringComparison.Ordinal)
                ? fitted.Substring(0, fitted.Length - 3).TrimEnd()
                : fitted;
            True(prefix.Length >= Math.Min(4, original.Length), label + " retains meaningful text");
            True(original.StartsWith(prefix, StringComparison.Ordinal), label + " preserves the source prefix");
        }

        private static bool FitsSegoeUi(string value, float width, float fontSize, bool bold)
        {
            if (string.IsNullOrEmpty(value))
            {
                return true;
            }
            using (var bitmap = new Bitmap(1, 1))
            using (Graphics graphics = Graphics.FromImage(bitmap))
            using (var font = new Font("Segoe UI", fontSize, bold ? FontStyle.Bold : FontStyle.Regular, GraphicsUnit.Pixel))
            {
                SizeF size = graphics.MeasureString(value, font, int.MaxValue, StringFormat.GenericTypographic);
                return size.Width <= width;
            }
        }

        /// <summary>
        /// Writes a one-record dataset and returns its guidance, so technique
        /// combinations absent from the curated data can still be asserted.
        /// </summary>
        private static GuidanceSnapshot LoadSyntheticGuidance(
            string root,
            string telemetryName,
            string upshiftThrottleLift,
            string simulatorShiftCut,
            string shiftActuation,
            string overrideJson = null)
        {
            string directory = Path.Combine(root, Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(Path.Combine(directory, "cars"));
            string recordId = "ams2.synthetic";
            string overrides = overrideJson ?? "[]";
            string record = "{"
                + "\"schema_version\":\"1.0.0\","
                + "\"record_id\":\"" + recordId + "\","
                + "\"identity\":{\"display_name\":\"" + telemetryName + "\","
                + "\"manufacturer\":\"Test\",\"model\":\"Test\","
                + "\"year\":{\"label\":\"test\"},\"class\":\"TEST\"},"
                + "\"authentic_controls\":{\"transmission\":{"
                + "\"forward_gears\":6,\"gearbox_type\":\"unknown\","
                + "\"shift_actuation\":\"" + shiftActuation + "\",\"shift_pattern\":\"sequential\","
                + "\"upshift\":{\"clutch\":\"not-required\",\"throttle_lift\":\"" + upshiftThrottleLift + "\","
                + "\"automatic_cut\":\"" + simulatorShiftCut + "\",\"manual_blip\":\"not-applicable\",\"automatic_blip\":\"not-applicable\"},"
                + "\"downshift\":{\"clutch\":\"not-required\",\"throttle_lift\":\"not-applicable\","
                + "\"automatic_cut\":\"not-applicable\",\"manual_blip\":\"not-required\",\"automatic_blip\":\"yes\"},"
                + "\"standing_start_clutch\":\"not-required\"},"
                + "\"steering\":{\"wheel_rim\":{\"shape\":\"round\",\"source_label\":\"test\"}}},"
                + "\"simulators\":[{\"simulator\":\"ams2\","
                + "\"identities\":[{\"kind\":\"telemetry-name\",\"value\":\"" + telemetryName + "\"}],"
                + "\"behavior\":{\"shift_type\":\"" + shiftActuation + "\",\"auto_blip\":\"yes\","
                + "\"shift_cut\":\"" + simulatorShiftCut + "\","
                + "\"wheel_rim_type\":{\"normalized\":\"round\",\"source_label\":\"test\"}},"
                + "\"overrides\":" + overrides + ",\"verified_game_version\":\"1.6.9.91\",\"verified_at\":\"2026-08-13\","
                + "\"source_refs\":[\"test.source\"],"
                + "\"confidence\":{\"level\":\"medium\",\"basis\":\"synthetic test record\"}}],"
                + "\"provenance\":{\"claims\":[{\"paths\":[\"/identity\"],\"source_refs\":[\"test.source\"],"
                + "\"confidence\":\"medium\",\"basis\":\"synthetic\"}]},"
                + "\"updated_at\":\"2026-08-13\"}";
            File.WriteAllText(Path.Combine(directory, "cars", recordId + ".json"), record);
            File.WriteAllText(
                Path.Combine(directory, "index.json"),
                "{\"schema_version\":\"1.0.0\",\"dataset_version\":\"0.0.0\","
                    + "\"released_at\":\"2026-08-13\",\"records\":[\"cars/" + recordId + ".json\"]}");
            AsDrivenDatabase database = AsDrivenDatabase.Load(directory);
            return database.Match("Automobilista2", telemetryName);
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
