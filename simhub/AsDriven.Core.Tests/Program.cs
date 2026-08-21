using System;
using System.Collections.Generic;
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
                // The catalog is one entry per simulator entry, not per record: a
                // car covered by two simulators is previewable under each. That
                // was the same number until the Huracan gained an Assetto Corsa
                // EVO entry, and this assertion had quietly been checking that
                // no record was covered twice.
                var catalogRecords = new HashSet<string>(StringComparer.Ordinal);
                var catalogPairs = new HashSet<string>(StringComparer.Ordinal);
                foreach (CarCatalogEntry car in database.Cars)
                {
                    catalogRecords.Add(car.RecordId);
                    catalogPairs.Add(car.RecordId + "\u001f" + car.Simulator);
                }
                Equal(database.RecordCount, catalogRecords.Count,
                    "lists every curated car for preview");
                True(database.Cars.Length >= database.RecordCount,
                    "a car covered by several simulators is previewable under each");
                Equal(database.Cars.Length, catalogPairs.Count,
                    "never lists one car twice for the same simulator");
                for (int catalogIndex = 1; catalogIndex < database.Cars.Length; catalogIndex++)
                {
                    True(
                        string.Compare(
                            database.Cars[catalogIndex - 1].DisplayName,
                            database.Cars[catalogIndex].DisplayName,
                            StringComparison.OrdinalIgnoreCase) <= 0,
                        "sorts the preview catalog by display name");
                }
                GuidanceSnapshot preview = database.Preview("ams2", "lister-storm-gtm");
                True(preview.HasMatch, "loads a curated record directly for preview");
                Equal("preview", preview.MatchKind, "labels direct record lookup as preview data");
                Equal("Lister Storm GTM", preview.DisplayName, "previews the requested car");
                Equal("preview-not-found", database.Preview("ams2", "missing.record").MatchStatus, "rejects an unknown preview record");

                // The second simulator. SimHub calls this game "AssettoCorsaEvo",
                // and the matcher has to recognize it before any drive in it can
                // be recorded. Compared whole rather than by prefix: plain
                // Assetto Corsa and Competizione are separate games with separate
                // cars, and resolving either here would match them against AC
                // EVO records.
                Equal("ac-evo", AsDrivenDatabase.CanonicalizeSimulator("AssettoCorsaEvo"),
                    "recognizes SimHub's Assetto Corsa EVO game name");
                Equal("ac-evo", AsDrivenDatabase.CanonicalizeSimulator("Assetto Corsa EVO"),
                    "recognizes the product spelling of Assetto Corsa EVO");
                Equal(null, AsDrivenDatabase.CanonicalizeSimulator("AssettoCorsa"),
                    "does not resolve plain Assetto Corsa to the EVO dataset");
                Equal(null, AsDrivenDatabase.CanonicalizeSimulator("AssettoCorsaCompetizione"),
                    "does not resolve Competizione to the EVO dataset");

                // Until one record names it, a recognized game is still reported
                // as uncovered - that message is for the driver and does not
                // change. What changes is that its car identities are written to
                // the local diagnostics log anyway, because otherwise there is no
                // way to learn the identities the first record needs.
                // Assetto Corsa EVO now carries a curated record, so the car it
                // was driven in resolves. The name is its own: AMS2 calls the
                // same car "Lamborghini Huracan Super Trofeo EVO2", and both
                // reach one record because the entries are separate identities
                // rather than one spelling guessed at.
                GuidanceSnapshot acEvo = database.Match(
                    "AssettoCorsaEvo", "Lamborghini Huracan ST EVO2");
                True(acEvo.HasMatch, "matches the car Assetto Corsa EVO was driven in");
                Equal("Lamborghini Huracan Super Trofeo EVO2", acEvo.DisplayName,
                    "answers with the real car, not the simulator name for it");
                Equal("unmatched",
                    database.Match("AssettoCorsaEvo", "Some Car It Does Not Have").MatchStatus,
                    "a covered game still fails closed on a car with no record");
                // Recognized, and carrying no records at all: the driver is told
                // the game is not covered rather than that every car is missing.
                Equal("unsupported-game",
                    database.Match("iRacing", "Any Car").MatchStatus,
                    "reports a recognized game with no records as not yet covered");

                // A record declares the aero packages it covers and the database
                // expands them into one exact key each. Every configuration of a
                // car has to reach that car's guidance, and the card says the
                // same thing for all of them: the circuit picks the package, so
                // it changes no rim, no shifter and no technique.
                GuidanceSnapshot speedway = database.Match(
                    "Automobilista2", "Reynard 98i Mercedes-Benz - Speedway");
                True(speedway.HasMatch, "matches an expanded aero configuration");
                Equal("CART", speedway.OverlayCarClassDetailed,
                    "the class line carries the class alone");

                GuidanceSnapshot basePackage = database.Match(
                    "Automobilista2", "Reynard 98i Mercedes-Benz");
                True(basePackage.HasMatch, "matches the base configuration");
                Equal(speedway.RecordId, basePackage.RecordId,
                    "every aero configuration resolves to the same record");
                Equal(speedway.OverlayCarClassDetailed, basePackage.OverlayCarClassDetailed,
                    "and to the same card, because the package changes nothing on it");

                GuidanceSnapshot superspeedway = database.Match(
                    "Automobilista2", "Reynard 98i Mercedes-Benz - Superspeedway");
                Equal(speedway.RecordId, superspeedway.RecordId,
                    "a declared package the record never spelled out still matches");

                GuidanceSnapshot lowDownforce = database.Match(
                    "Automobilista2", "BMW M4 GT3 - Low Downforce");
                Equal("bmw-m4-gt3", lowDownforce.RecordId,
                    "an expanded package resolves to its base car's record");
                Equal("BMW M4 GT3", lowDownforce.DisplayName,
                    "and the card names the car, not the configuration");

                // A package nothing declares is still nobody's car. Expansion
                // adds keys; it never softens the comparison.
                False(database.Match("Automobilista2", "BMW M4 GT3 - Speedway").HasMatch,
                    "an undeclared package does not match");

                GuidanceSnapshot f301 = database.Match("Automobilista2", "Dallara F301");
                True(f301.HasMatch, "matches the exact AMS2 telemetry name");
                Equal("f301", f301.RecordId, "returns the correct record");
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
                Equal("gt-formula", cadillac.WheelRimShape, "uses the merged GT/Formula Cadillac rim");

                GuidanceSnapshot viper = database.Match("Automobilista2", "Dodge Viper GTS-R");
                True(viper.HasMatch, "matches the live Dodge Viper GTS-R identity");
                Equal("dodge-viper-gts-r", viper.RecordId, "returns the curated Viper record");
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

                // The browser lists cars, not configurations. No curated name
                // carries an aero package any more, so nothing has to be stripped
                // and no two entries can collide over one.
                var browserLabels = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                foreach (CarCatalogEntry entry in database.Cars)
                {
                    False(browserLabels.ContainsKey(entry.DisplayLabel),
                        "browser labels stay distinct: " + entry.DisplayLabel);
                    browserLabels[entry.DisplayLabel] = entry.RecordId;
                    Equal(entry.DisplayName, entry.BrowserName,
                        "a browser name is the car's name: " + entry.RecordId);
                    False(entry.DisplayName.EndsWith(" Downforce", StringComparison.Ordinal)
                        || entry.DisplayName.EndsWith("speedway", StringComparison.Ordinal)
                        || entry.DisplayName.EndsWith(" - Speedway", StringComparison.Ordinal),
                        "no curated name carries an aero package: " + entry.RecordId);
                }
                GuidanceSnapshot mp412 = database.Match(
                    "Automobilista2", "McLaren Mercedes MP4/12 - High Downforce");
                if (mp412.HasMatch)
                {
                    CarCatalogEntry browsed = null;
                    foreach (CarCatalogEntry entry in database.Cars)
                    {
                        if (entry.RecordId == mp412.RecordId) { browsed = entry; }
                    }
                    True(browsed != null, "the MP4/12 appears in the browser");
                    Equal("McLaren Mercedes MP4/12", browsed.BrowserName,
                        "under the car's own name");
                }

                foreach (CarCatalogEntry catalogEntry in database.Cars)
                {
                    AssertOverlayTextFits(
                        database.Preview(catalogEntry.Simulator, catalogEntry.RecordId),
                        "overlay text fits " + catalogEntry.RecordId);
                }

                GuidanceSnapshot alpine = database.Match("Automobilista2", "Alpine A424");
                True(alpine.HasMatch, "matches the live Alpine A424 identity");
                Equal("alpine-a424", alpine.RecordId, "returns the curated Alpine record");
                Equal("7-speed paddle shifters", alpine.ShiftType, "formats the tested Alpine transmission");
                Equal("not-required", alpine.StandingStartClutch, "does not require a physical clutch for Alpine hybrid move-off");
                Equal("yes", alpine.ShiftCut, "exposes the reviewed Alpine automatic cut");
                Equal("yes", alpine.AutoBlip, "exposes the directly observed Alpine automatic blip");
                Equal("gt-formula", alpine.WheelRimShape, "uses the merged GT/Formula Alpine rim");
                True(alpine.UpshiftGuidance.Contains("Throttle lift not required"), "describes no-lift Alpine upshifts");
                True(alpine.DownshiftGuidance.Contains("Automatic blip"), "describes the Alpine automatic downshift blip");
                True(alpine.TechniqueSummary.Contains("Pull away without clutch input"), "describes Alpine pull-away technique without assuming a generic aid");
                True(alpine.TechniqueSummary.Contains("Shift with the paddles"), "describes the Alpine shift control");

                GuidanceSnapshot alpineLowDownforce = database.Match(
                    "Automobilista2", "Alpine A424 - Low Downforce");
                True(alpineLowDownforce.HasMatch, "matches the approved Alpine Low Downforce aero identity");
                Equal("alpine-a424", alpineLowDownforce.RecordId, "inherits Alpine controls for the aero package");
                Equal("telemetry-name", alpineLowDownforce.MatchKind, "keeps the Low Downforce alias exact");

                GuidanceSnapshot ligier = database.Match("Automobilista2", "Ligier JS P217");
                True(ligier.HasMatch, "matches the live Ligier JS P217 identity");
                Equal("ligier-js-p217", ligier.RecordId, "returns the shared Gen1 and Gen2 Ligier record");
                Equal("6-speed paddle shifters", ligier.ShiftType, "formats the tested Ligier transmission");
                Equal("not-required", ligier.StandingStartClutch, "does not require physical clutch input for Ligier move-off");
                Equal("yes", ligier.ShiftCut, "exposes the directly observed Ligier automatic cut");
                Equal("yes", ligier.AutoBlip, "exposes the directly observed Ligier automatic blip");
                Equal("gt-formula", ligier.WheelRimShape, "uses the merged GT/Formula Ligier rim");

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
                Equal("oreca-07", oreca.RecordId, "returns the shared Oreca Gen1 and Gen2 record");
                Equal("6-speed paddle shifters", oreca.ShiftType, "formats the tested Oreca transmission");
                Equal("gt-formula", oreca.WheelRimShape, "uses the merged GT/Formula Oreca rim");
                GuidanceSnapshot orecaLowDownforce = database.Match(
                    "Automobilista2", "Oreca 07 - Low Downforce");
                Equal("oreca-07", orecaLowDownforce.RecordId, "inherits Oreca controls for the aero package");
                Equal("telemetry-name", orecaLowDownforce.MatchKind, "keeps the Oreca aero alias exact");

                GuidanceSnapshot sc63 = database.Match("Automobilista2", "Lamborghini SC63");
                Equal("7-speed paddle shifters", sc63.ShiftType, "formats the tested SC63 transmission");
                Equal("gt-formula", sc63.WheelRimShape, "uses the merged GT/Formula SC63 rim");
                GuidanceSnapshot sc63LowDownforce = database.Match(
                    "Automobilista2", "Lamborghini SC63 - Low Downforce");
                Equal("lamborghini-sc63", sc63LowDownforce.RecordId, "inherits SC63 controls for the aero package");

                GuidanceSnapshot p320 = database.Match("Automobilista2", "Ligier JS P320");
                Equal("required", p320.StandingStartClutch, "requires physical clutch input for the P320 standing start");
                Equal("gt-formula", p320.WheelRimShape, "uses the merged GT/Formula P320 rim");

                GuidanceSnapshot p4 = database.Match("Automobilista2", "Ligier JS P4");
                Equal("not-required", p4.StandingStartClutch, "does not require physical clutch input for P4 move-off");
                Equal("gt-formula", p4.WheelRimShape, "uses the merged GT/Formula P4 rim");

                GuidanceSnapshot valkyrie = database.Match("Automobilista2", "Aston Martin Valkyrie Hypercar");
                Equal("7-speed paddle shifters", valkyrie.ShiftType, "formats the tested Valkyrie transmission");
                Equal("gt-formula", valkyrie.WheelRimShape, "uses the merged GT/Formula Valkyrie rim");
                GuidanceSnapshot unobservedValkyrieAero = database.Match(
                    "Automobilista2", "Aston Martin Valkyrie Hypercar - Low Downforce");
                False(unobservedValkyrieAero.HasMatch, "does not invent an unobserved Valkyrie aero alias");

                GuidanceSnapshot roadValkyrie = database.Match("Automobilista2", "Aston Martin Valkyrie");
                Equal("aston-martin-valkyrie", roadValkyrie.RecordId, "keeps the road Valkyrie distinct from the race car");
                Equal("7-speed paddle shifters", roadValkyrie.ShiftType, "formats the road Valkyrie transmission");
                Equal("gt-formula", roadValkyrie.WheelRimShape, "uses the merged GT/Formula road Valkyrie rim");

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
                    Equal("gt-formula", renault.WheelRimShape, "uses the merged GT/Formula rim for " + renaultFormula);
                }

                GuidanceSnapshot audiGt4 = database.Match("Automobilista2", "Audi R8 LMS GT4");
                Equal("7-speed paddle shifters", audiGt4.ShiftType, "formats the tested Audi GT4 transmission");
                Equal("gt-formula", audiGt4.WheelRimShape, "uses the merged GT/Formula Audi GT-style rim");

                GuidanceSnapshot corvetteGt3 = database.Match("Automobilista2", "Chevrolet Corvette Z06 GT3.R");
                Equal("6-speed paddle shifters", corvetteGt3.ShiftType, "formats the tested Corvette GT3 transmission");
                Equal("gt-formula", corvetteGt3.WheelRimShape, "uses the merged GT/Formula Corvette GT-style rim");
                GuidanceSnapshot corvetteLowDownforce = database.Match(
                    "Automobilista2", "Chevrolet Corvette Z06 GT3.R - Low Downforce");
                Equal("chevrolet-corvette-z06-gt3r", corvetteLowDownforce.RecordId, "inherits Corvette controls for the aero package");

                GuidanceSnapshot huracanEvo2 = database.Match(
                    "Automobilista2", "Lamborghini Huracan Super Trofeo EVO2");
                Equal("gt-formula", huracanEvo2.WheelRimShape, "uses the merged GT/Formula Huracan GT-style rim");
                GuidanceSnapshot huracanPredecessor = database.Match(
                    "Automobilista2", "LamborghiniHuracanLP6202SuperTrofeo");
                False(huracanPredecessor.HasMatch, "does not silently match the earlier Huracan predecessor");

                GuidanceSnapshot vantageGt4 = database.Match("Automobilista2", "Aston Martin Vantage GT4 Evo");
                Equal("6-speed paddle shifters", vantageGt4.ShiftType, "reports the six usable Vantage GT4 ratios");
                Equal("gt-formula", vantageGt4.WheelRimShape, "uses the merged GT/Formula Vantage GT4 rim");

                GuidanceSnapshot vantageGte = database.Match("Automobilista2", "Aston Martin Vantage GTE");
                Equal("6-speed paddle shifters", vantageGte.ShiftType, "formats the tested Vantage GTE transmission");
                Equal("gt-formula", vantageGte.WheelRimShape, "uses the merged GT/Formula Vantage GTE rim");

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
                Equal("aston-martin-dbr9", dbr9LowDownforce.RecordId, "inherits DBR9 controls for the aero package");
                GuidanceSnapshot c5rLowDownforce = database.Match(
                    "Automobilista2", "Chevrolet Corvette C5-R - Low Downforce");
                Equal("chevrolet-corvette-c5-r", c5rLowDownforce.RecordId, "inherits C5-R controls for the aero package");

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
                Equal("gt-formula", dallaraSp1.WheelRimShape, "uses the merged GT/Formula Dallara display rim");

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
                Equal("lola-b05-40-v8", lolaV8LowDownforce.RecordId, "inherits Lola V8 controls for the aero package");

                GuidanceSnapshot murcielagoLowDownforce = database.Match(
                    "Automobilista2", "Lamborghini Murcielago R-GT - Low Downforce");
                Equal("lamborghini-murcielago-r-gt", murcielagoLowDownforce.RecordId, "inherits Murcielago controls for the aero package");
                Equal("telemetry-name", murcielagoLowDownforce.MatchKind, "keeps the Murcielago aero alias exact");

                GuidanceSnapshot mc12LowDownforce = database.Match(
                    "Automobilista2", "Maserati MC12 GT1 - Low Downforce");
                Equal("maserati-mc12-gt1", mc12LowDownforce.RecordId, "inherits MC12 controls for the aero package");
                Equal("telemetry-name", mc12LowDownforce.MatchKind, "keeps the MC12 aero alias exact");

                GuidanceSnapshot diablo = database.Match("Automobilista2", "Lamborghini Diablo SV-R");
                True(diablo.HasMatch, "matches the exact Diablo SV-R identity");
                Equal("lamborghini-diablo-sv-r", diablo.RecordId, "returns the curated Diablo record");
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
                    "Formula Ultimate Hybrid Gen2",
                    "Formula Ultimate Hybrid Gen3",
                    "Formula USA 2023"
                })
                {
                    GuidanceSnapshot formula = database.Match("Automobilista2", formulaCar);
                    True(formula.HasMatch, "matches curated Formula identity " + formulaCar);
                    Equal("gt-formula", formula.WheelRimShape, "uses the merged GT/Formula rim for " + formulaCar);
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
                    Equal("gt-formula", formula.WheelRimShape, "uses the merged GT/Formula rim for live variant " + liveFormulaVariant);
                }

                GuidanceSnapshot v8Gen3 = database.Match(
                    "Automobilista2", "Formula V8 Gen3 - High Downforce");
                True(v8Gen3.HasMatch, "matches the current Formula V8 Gen3 telemetry identity");
                Equal("formula-reiza", v8Gen3.RecordId, "maps Formula V8 Gen3 to the retained Formula Reiza record");
                Equal("Formula V8 Gen3", v8Gen3.DisplayName, "uses the current official Formula V8 Gen3 display name");

                GuidanceSnapshot hybridGen3 = database.Match(
                    "Automobilista2", "Formula Ultimate Hybrid Gen3 - High Downforce");
                True(hybridGen3.HasMatch, "matches the current Formula Hybrid Gen3 telemetry identity");
                Equal("formula-ultimate-2022", hybridGen3.RecordId, "maps Formula Hybrid Gen3 to the 2022 ground-effect record");
                Equal("Formula Hybrid Gen3", hybridGen3.DisplayName, "uses the current official Formula Hybrid Gen3 display name");

                // Retired identities must not match. Formula Ultimate Gen2 was
                // this car's pre-rename name, and the string is one digit away
                // from the separate Formula Ultimate Hybrid Gen2 car, so a
                // lingering alias would hand a driver the wrong car's guidance.
                GuidanceSnapshot retiredUltimate = database.Match(
                    "Automobilista2", "Formula Ultimate Gen2");
                False(retiredUltimate.HasMatch, "never matches the retired Formula Ultimate Gen2 identity");
                foreach (string retired in new[] {
                    "Lotus 98T", "McLaren MP4/8", "Porsche 911 RSR 74"
                })
                {
                    False(database.Match("Automobilista2", retired).HasMatch,
                        "never matches retired identity " + retired);
                }

                // "gt-style", "prototype" and "formula" split one rim three
                // ways by racing class. They are retired into "gt-formula" and
                // stay in the schema enum so older drafts still validate, but no
                // curated record may carry any of them.
                foreach (CarCatalogEntry car in database.Cars)
                {
                    GuidanceSnapshot shape = database.Preview("Automobilista2", car.RecordId);
                    foreach (string retired in new[] { "gt-style", "prototype", "formula" })
                    {
                        False(string.Equals(shape.WheelRimShape, retired, StringComparison.Ordinal),
                            "never curates the retired " + retired + " rim shape: " + car.RecordId);
                    }
                }

                // ---- preflight card wording -------------------------------
                // The card's words live in PreflightLabels rather than in a
                // dashboard formula, so they are asserted here and every
                // surface is guaranteed to say the same thing.
                Equal("Round rim", PreflightLabels.WheelRim("round"), "names a round rim");
                Equal("D-shaped rim", PreflightLabels.WheelRim("d-shaped"), "names a D-shaped rim");
                Equal("Yoke", PreflightLabels.WheelRim("yoke"), "names a yoke");
                Equal("Rim not recorded", PreflightLabels.WheelRim("unknown"),
                    "says the rim was not recorded rather than inventing one");
                foreach (string merged in new[] { "gt-formula", "gt-style", "prototype", "formula" })
                {
                    Equal("GT / Formula rim", PreflightLabels.WheelRim(merged),
                        "an older dataset's retired rim value still reads correctly: " + merged);
                }

                Equal("No display or shift lights", PreflightLabels.WheelFeatures("no", "no"),
                    "states plainly that the rim carries nothing");
                Equal("Display and shift lights", PreflightLabels.WheelFeatures("yes", "yes"),
                    "states both when both are present");
                Equal("Integrated display", PreflightLabels.WheelFeatures("yes", "no"), "display alone");
                Equal("Shift lights", PreflightLabels.WheelFeatures("no", "yes"), "lights alone");
                // Grey means "no evidence" everywhere else on the card, and this
                // line used to grey settled answers too. A rim that plainly
                // carries neither a display nor lights is a fact - it says fit
                // the plain rim - and only a genuine gap is greyed now.
                Equal("known", PreflightLabels.WheelFeatureTone("no", "no"),
                    "a rim with neither is a settled answer, not a gap");
                Equal("known", PreflightLabels.WheelFeatureTone("yes", "yes"),
                    "a rim with both is established");
                Equal("known", PreflightLabels.WheelFeatureTone("no", "yes"),
                    "shift lights alone are established");
                Equal("unknown", PreflightLabels.WheelFeatureTone("unknown", "no"),
                    "an unrecorded display is greyed");

                // The two fields are recorded independently, so a half-known rim
                // says which half is missing. Answering "Display not recorded"
                // for these denied a display that had been recorded, and where
                // the display was a yes it read as complete while dropping the
                // lights entirely. Both halves must be known to lose the grey.
                Equal("No display, lights unknown",
                    PreflightLabels.WheelFeatures("no", "unknown"),
                    "a recorded absent display is not called unrecorded");
                Equal("Display, lights unknown",
                    PreflightLabels.WheelFeatures("yes", "unknown"),
                    "a display with unrecorded lights does not read as complete");
                Equal("unknown", PreflightLabels.WheelFeatureTone("no", "unknown"),
                    "half an answer is still a gap");
                Equal("unknown", PreflightLabels.WheelFeatureTone("yes", "unknown"),
                    "a known display does not settle the lights");
                foreach (string half in new[]
                    { "No display, lights unknown", "Display, lights unknown" })
                {
                    True(half.Length <= 26, "half-known label fits the band: " + half);
                }
                Equal("Display not recorded", PreflightLabels.WheelFeatures("unknown", "no"),
                    "an unobserved modifier is never rendered as a no");

                Equal("5-speed H-pattern", PreflightLabels.Shifter(5, "h-pattern"), "names the shifter");
                Equal("6-speed paddles", PreflightLabels.Shifter(6, "sequential-paddles"), "names paddles");
                Equal("5-speed sequential", PreflightLabels.Shifter(5, "sequential-stick"), "names a stick");
                Equal("H-pattern", PreflightLabels.Shifter(0, "h-pattern"),
                    "omits the gear count when it is not known");

                Equal("Dogleg gate - 1st down and left",
                    PreflightLabels.Gate("h-pattern", "dogleg-h", "down-left"),
                    "says where first gear is on a dogleg");
                Equal("Dogleg gate - 1st down and right",
                    PreflightLabels.Gate("h-pattern", "dogleg-h", "down-right"),
                    "follows the record when the gate is mirrored, as on the McLaren MP4/4");
                Equal("Dogleg gate - 1st outside the plane",
                    PreflightLabels.Gate("h-pattern", "dogleg-h", "unknown"),
                    "never assumes a dogleg puts first on the left");
                Equal("Standard gate - 1st up and left", PreflightLabels.Gate("h-pattern", "standard-h"),
                    "says where first gear is on a standard gate");
                Equal("Gate not recorded", PreflightLabels.Gate("h-pattern", "unknown"),
                    "never guesses an unobserved gate");

                Equal("Clutch required", PreflightLabels.Launch("required"), "launch clutch");
                Equal("No clutch needed", PreflightLabels.Launch("not-required"), "clutch-free launch");
                Equal("Not established", PreflightLabels.Launch("unknown"), "unknown launch");
                Equal("Lift the throttle", PreflightLabels.Upshift("required", "no"), "lift upshift");
                Equal("Stay flat - car cuts", PreflightLabels.Upshift("not-required", "yes"),
                    "says the car cuts when it does");
                Equal("Stay flat", PreflightLabels.Upshift("not-required", "no"),
                    "does not claim an automatic cut that was not observed");
                Equal("Blip - rev-match", PreflightLabels.Downshift("required", "no"), "required blip");
                Equal("Blip optional", PreflightLabels.Downshift("optional", "no"),
                    "keeps optional as its own answer");
                Equal("Car blips for you", PreflightLabels.Downshift("not-required", "yes"), "auto blip");
                Equal("No blip needed", PreflightLabels.Downshift("not-required", "no"),
                    "no blip needed without claiming automation");

                // The tone decides colour, and an unresolved value must never
                // read as though the car handles it.
                Equal("you", PreflightLabels.LaunchTone("required"), "required launch is the driver's");
                Equal("car", PreflightLabels.LaunchTone("not-required"), "clutch-free launch is the car's");
                Equal("unknown", PreflightLabels.LaunchTone("unknown"), "unknown launch stays unresolved");
                Equal("optional", PreflightLabels.DownshiftTone("optional", "not-required"),
                    "an optional blip is neither demanded nor handled");
                Equal("you", PreflightLabels.BandTone("car", "car", "you"),
                    "one driver action turns the whole band");
                Equal("car", PreflightLabels.BandTone("car", "car", "car"), "all handled reads as the car");
                Equal("unknown", PreflightLabels.BandTone("car", "unknown", "car"),
                    "an unestablished moment leaves the band unresolved");

                // Three real records spanning the range the card must survive.
                GuidanceSnapshot dogBox = database.Match(
                    "Automobilista2", "Brabham BMW BT52 - High Downforce");
                True(dogBox.HasMatch, "matches the Brabham dog box");
                Equal("5-speed H-pattern", dogBox.ShifterLabel, "Brabham shifter");
                Equal("Clutch required", dogBox.LaunchLabel, "Brabham launch");
                Equal("Lift the throttle", dogBox.UpshiftLabel, "Brabham upshift");
                Equal("Blip - rev-match", dogBox.DownshiftLabel, "Brabham downshift");
                Equal("you", dogBox.UseBandTone, "every Brabham moment is the driver's");

                GuidanceSnapshot paddles = database.Match("Automobilista2", "Porsche 911 GT3 R");
                True(paddles.HasMatch, "matches the 911 GT3 R");
                Equal("6-speed paddles", paddles.ShifterLabel, "911 shifter");
                Equal("No clutch needed", paddles.LaunchLabel, "911 launch");
                Equal("Car blips for you", paddles.DownshiftLabel, "911 downshift");
                Equal("car", paddles.LaunchTone, "911 launch is handled");
                Equal("car", paddles.DownshiftTone, "911 downshift is handled");

                GuidanceSnapshot mixed = database.Match("Automobilista2", "ARC Camaro");
                True(mixed.HasMatch, "matches the ARC Camaro");
                Equal("you", mixed.LaunchTone, "Camaro launch is the driver's");
                Equal("car", mixed.UpshiftTone, "the Camaro gearbox cuts its own upshift");
                Equal("you", mixed.DownshiftTone, "the Camaro downshift blip is the driver's");
                Equal("you", mixed.UseBandTone,
                    "a mixed band still reads as the driver's, while its upshift cell does not");

                // "optional" is a settled answer, not a gap. Colouring it grey
                // would say the evidence is missing when the record states it.
                Equal("optional", PreflightLabels.DownshiftTone("optional", "not-required"),
                    "an optional blip has its own tone");
                Equal("unknown", PreflightLabels.DownshiftTone("unknown", "not-required"),
                    "only an unestablished blip reads as unknown");
                Equal("car", PreflightLabels.BandTone("car", "car", "optional"),
                    "a band whose only outstanding item is optional demands nothing");
                Equal("unknown", PreflightLabels.BandTone("car", "car", "unknown"),
                    "an unestablished moment leaves the band unresolved");
                // A summary must arrive pre-broken and never clipped mid-word:
                // the card draws one text item per line, so an unwrapped value
                // would simply disappear past the panel edge.
                GuidanceSnapshot dogBoxNote = database.Match("Automobilista2", "Brabham BT44");
                True(dogBoxNote.HasMatch, "matches the Brabham BT44");
                True(dogBoxNote.DriverSummary.Length > 90, "the dog box summary is long enough to wrap");
                // The BT44's record calls its dog-ring construction inferred rather
                // than sourced, so the summary the driver reads must hedge with it.
                // A summary firmer than its own evidence is the failure this
                // whole layer exists to avoid.
                True(dogBoxNote.DriverSummary.IndexOf("inferred", StringComparison.Ordinal) >= 0,
                    "an inferred mechanism is labelled as inference on the card");
                False(dogBoxNote.DriverSummary.IndexOf("The dog rings engage", StringComparison.Ordinal) >= 0,
                    "and is never asserted as settled fact");
                True(dogBoxNote.DriverSummaryLine2.Length > 0, "it wraps onto a second line");
                Equal(dogBoxNote.DriverSummary.Replace("  ", " "),
                    (dogBoxNote.DriverSummaryLine1 + " " + dogBoxNote.DriverSummaryLine2 + " "
                        + dogBoxNote.DriverSummaryLine3).Trim(),
                    "the wrapped lines rejoin into the original summary with nothing lost");
                False(dogBoxNote.DriverSummaryLine3.EndsWith("..."),
                    "a summary within the cap is never ellipsised");
                // The card shows effective behaviour, so a simulator deviation
                // would otherwise read as though it were authentic. Only the
                // record's own override can raise the marker.
                // A running shift always states its clutch. 222 of 224 records
                // read "not required", and saying so is the point: silence
                // there would be indistinguishable from never having checked.
                Equal("No clutch needed", PreflightLabels.RunningClutch("not-required"),
                    "states a clutch-free running shift outright");
                Equal("Clutch not established", PreflightLabels.RunningClutch("unknown"),
                    "an unchecked clutch says so rather than staying blank");
                Equal("No clutch fitted", PreflightLabels.RunningClutch("not-applicable"),
                    "a car with no clutch says that instead");
                Equal("you", PreflightLabels.UpshiftTone("not-required", "required"),
                    "a clutch the driver must work makes the shift theirs");
                Equal("you", PreflightLabels.DownshiftTone("not-required", "required"),
                    "on the downshift too");
                Equal("No clutch needed", dogBoxNote.UpshiftClutchLabel,
                    "the Brabham upshift is clutch-free and says so");
                Equal("No clutch needed", dogBoxNote.DownshiftClutchLabel,
                    "and its downshift too");
                // The steering lock moved to the simulator entry, because every
                // curated value for it came from the AMS2 spreadsheet. The
                // client must still read it, or the move would have silently
                // dropped a value the overlay shows.
                GuidanceSnapshot lockCar = database.Match("Automobilista2", "Dallara F301");
                if (lockCar.HasMatch)
                {
                    True(lockCar.HasSteeringDOR, "the F301 still reports a steering lock");
                    Equal(450, lockCar.SteeringDOR, "and reports the value it always had");
                }

                // Batch 23: the prototypes split on the two things the drive
                // tested, so the class alone never predicts the answer.
                foreach (string clutchFree in new[] {
                    "MetalMoro AJR Honda", "MetalMoro AJR Judd", "MetalMoro AJR Nissan",
                    "MetalMoro AJR Gen2 Honda", "MetalMoro AJR Gen2 Nissan",
                    "MetalMoro MRX Duratec Turbo P2", "MetalMoro MRX Honda P3"
                })
                {
                    GuidanceSnapshot car = database.Match("Automobilista2", clutchFree);
                    True(car.HasMatch, "matches " + clutchFree);
                    Equal("not-required", car.StandingStartClutch,
                        clutchFree + " pulls away without the clutch");
                }
                foreach (string needsClutch in new[] {
                    "Ginetta G58", "Ginetta G58 Gen2", "Sigma P1", "Sigma P1 G5",
                    "MCR S2000", "Roco 001", "MetalMoro MRX Duratec Turbo P3"
                })
                {
                    GuidanceSnapshot car = database.Match("Automobilista2", needsClutch);
                    True(car.HasMatch, "matches " + needsClutch);
                    Equal("required", car.StandingStartClutch,
                        needsClutch + " needs the clutch to pull away");
                }
                Equal(5, database.Match("Automobilista2", "MCR S2000").GearCount,
                    "the MCR is the batch's only five-speed");
                // Both P3 cars leave the blip to the driver. They were recorded
                // as disagreeing, which was the old blip measurement reading the
                // driver's throttle as the Honda's; a re-drive corrected it, and
                // the contrast this used to assert was the fault itself.
                Equal("no", database.Match("Automobilista2", "MetalMoro MRX Duratec Turbo P3").AutoBlip,
                    "the Duratec Turbo P3 does not blip for the driver");
                Equal("no", database.Match("Automobilista2", "MetalMoro MRX Honda P3").AutoBlip,
                    "and neither does its Honda classmate");
                // A gearbox no source names must not claim a blip requirement.
                Equal("unknown",
                    database.Match("Automobilista2", "Roco 001").ManualBlip,
                    "the Roco's blip requirement stays unknown, not inferred from the missing automation");

                GuidanceSnapshot untestedClutch = database.Match(
                    "Automobilista2", "Lamborghini Diablo SV-R");
                if (untestedClutch.HasMatch)
                {
                    Equal("Clutch not established", untestedClutch.UpshiftClutchLabel,
                        "the one car whose running clutch was never established says so");
                }

                GuidanceSnapshot lotus = database.Match(
                    "Automobilista2", "Lotus 98T - High Downforce");
                if (lotus.HasMatch)
                {
                    True(lotus.SimulatorDiffers, "the 98T records a simulator deviation");
                    True(lotus.ShifterDiffers, "its gear count is the overridden value");
                    False(lotus.LaunchDiffers, "and its launch clutch is not");
                    True(lotus.SimulatorDifference.Length > 0, "the reviewer's reason is carried");
                    Equal(5, lotus.GearCount, "the client shows the simulator's five gears");
                }
                GuidanceSnapshot cayman = database.Match(
                    "Automobilista2", "Porsche Cayman GT4 Clubsport MR");
                if (cayman.HasMatch)
                {
                    True(cayman.LaunchDiffers, "the Cayman overrides its standing-start clutch");
                    False(cayman.ShifterDiffers, "but not its shifter");
                }
                GuidanceSnapshot noOverride = database.Match("Automobilista2", "Brabham BT44");
                False(noOverride.SimulatorDiffers,
                    "a record with no override never claims the simulator differs");
                False(noOverride.ShifterDiffers, "and marks no row");

                GuidanceSnapshot noNote = database.Match("Automobilista2", "Porsche 911 GT3 R");
                Equal(string.Empty, noNote.DriverSummary, "a record without a summary carries none");
                Equal(string.Empty, noNote.DriverSummaryLine1, "and no wrapped lines either");

                GuidanceSnapshot chevette = database.Match("Automobilista2", "Chevrolet Chevette");
                if (chevette.HasMatch)
                {
                    Equal("Blip optional", chevette.DownshiftLabel, "Chevette downshift wording");
                    Equal("optional", chevette.DownshiftTone, "Chevette downshift tone");
                }


                GuidanceSnapshot wrongCase = database.Match("Automobilista2", "dallara f301");
                False(wrongCase.HasMatch, "matching is case-sensitive and exact");
                Equal("unmatched", wrongCase.MatchStatus, "reports unmatched telemetry");

                GuidanceSnapshot unsupported = database.Match("Other Simulator", "Dallara F301");
                Equal("unsupported-game", unsupported.MatchStatus, "gates by simulator");

                // The supported list is what the settings page shows before a
                // game is started, so it must come from the loaded records. A
                // simulator the matcher knows by name but has no data for is
                // not supported, and must say so instead of reporting every car
                // as unmatched.
                True(database.Simulators.Length > 0, "reports at least one supported simulator");
                foreach (SimulatorCoverage coverage in database.Simulators)
                {
                    True(coverage.RecordCount > 0,
                        "only lists a simulator that carries records: " + coverage.Id);
                    True(!string.IsNullOrEmpty(coverage.DisplayName),
                        "names the simulator for display: " + coverage.Id);
                }
                Equal("ams2", database.Simulators[0].Id, "lists the best-covered simulator first");
                Equal("Automobilista 2", database.Simulators[0].DisplayName,
                    "shows the product name rather than the SimHub game name");
                Equal(database.RecordCount, database.Simulators[0].RecordCount,
                    "the single curated simulator accounts for every record");
                True(database.Supports("Automobilista2"), "supports the curated simulator");
                True(database.Supports("AMS2"), "supports the curated simulator by short name");
                False(database.Supports("Other Simulator"), "does not support an unknown game");
                False(database.Supports("iRacing"),
                    "a recognized name without records is not supported");
                Equal("unsupported-game",
                    database.Match("iRacing", "Dallara F301").MatchStatus,
                    "a recognized game with no records reports unsupported, never unmatched");

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
                    // Reaching SimHub's suggested count must not end the test.
                    // That hint is CarSettings_MaxGears, which the project
                    // forbids from setting a gear count, and completing on it
                    // would make the drive confirm the hint instead of
                    // measuring the car.
                    False(guidedDrive.GetSnapshot().ResultReady, "never ends the gear count on the suggested number");
                    guidedDrive.Next();
                    True(guidedDrive.GetSnapshot().ResultReady, "records the highest gear reached when the driver ends the test");
                    True(guidedDrive.GetSnapshot().Result.Contains("Highest gear reached: 6"), "reports the gear actually reached");
                    guidedDrive.Next();
                    guidedDrive.AddSample(GuidedSample(now, 2, 55, 90, 5000, 70, 220, true));
                    guidedDrive.AddSample(GuidedSample(now.AddMilliseconds(50), 2, 70, 90, 5100, 72, 40, true));
                    guidedDrive.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 45, 90, 4200, 74, 35, true));
                    True(guidedDrive.GetSnapshot().ResultReady, "detects a full-throttle clutchless upshift");
                    guidedDrive.Next();
                    guidedDrive.AddSample(GuidedSample(now, 4, 60, 0, 4500, 80, 100, true));
                    guidedDrive.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 35, 25, 5200, 79, 90, true));
                    False(guidedDrive.GetSnapshot().ResultReady, "holds the downshift result until the gearbox proves it took drive");
                    guidedDrive.AddSample(GuidedSample(now.AddMilliseconds(700), 3, 0, 0, 6000, 78, 90, true));
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

                    // A driver still carrying throttle when the attempt begins
                    // must not have their own pedal reported as the car's blip.
                    // The measurement banked throttle from the whole attempt, so
                    // lifting into a downshift read as an automatic blip on any
                    // car. Only throttle after arming can be the car's.
                    {
                        GuidedVerificationDrive carried = new GuidedVerificationDrive();
                        carried.Start(6);
                        // Skip forward without answering: an unanswered phase
                        // advances on Next, which is what a driver skipping a
                        // test does.
                        for (int guard = 0; guard < 40
                            && carried.GetSnapshot().Title != "Downshift without pedal input"; guard++)
                        {
                            // The gear-count phase needs telemetry before it can
                            // conclude; everything else advances on Next alone.
                            carried.AddSample(GuidedSample(now, 4, 0, 0, 4000, 80, 100, true));
                            carried.Next();
                        }
                        Equal("Downshift without pedal input", carried.GetSnapshot().Title,
                            "reaches the coast-downshift test");
                        // Driving along on throttle, before any lift.
                        carried.AddSample(GuidedSample(now, 4, 0, 85, 5200, 80, 220, true));
                        // Lift, downshift, and no spike of the car's own.
                        carried.AddSample(GuidedSample(now.AddMilliseconds(100), 4, 0, 0, 4500, 80, 100, true));
                        carried.AddSample(GuidedSample(now.AddMilliseconds(200), 3, 0, 0, 5200, 79, 90, true));
                        carried.AddSample(GuidedSample(now.AddMilliseconds(800), 3, 0, 0, 6000, 78, 90, true));
                        True(carried.GetSnapshot().ResultReady, "accepts the clutchless downshift");
                        True(carried.GetSnapshot().Result.Contains("No automatic throttle spike"),
                            "never reports throttle carried in before the lift as the car's blip");
                    }

                    // Lifting and downshifting inside one telemetry sample is
                    // an ordinary way to drive the test. The baseline used to be
                    // captured at arming, so it landed on the gear already
                    // selected and the attempt timed out on a shift that plainly
                    // happened.
                    {
                        GuidedVerificationDrive prompt = new GuidedVerificationDrive();
                        prompt.Start(6);
                        for (int guard = 0; guard < 40
                            && prompt.GetSnapshot().Title != "Downshift without pedal input"; guard++)
                        {
                            prompt.AddSample(GuidedSample(now, 4, 0, 0, 4000, 80, 100, true));
                            prompt.Next();
                        }
                        // On throttle in fourth, then closed throttle and third
                        // in the very next sample.
                        prompt.AddSample(GuidedSample(now, 4, 0, 90, 5200, 80, 220, true));
                        prompt.AddSample(GuidedSample(now.AddMilliseconds(60), 3, 0, 0, 6100, 79, 90, true));
                        prompt.AddSample(GuidedSample(now.AddMilliseconds(700), 3, 0, 0, 6000, 78, 90, true));
                        True(prompt.GetSnapshot().ResultReady,
                            "detects a downshift taken immediately after the lift");
                        prompt.Next();
                        True(prompt.GetResults().ClutchlessDownshift == "yes",
                            "records the immediate lift-and-shift as a clutchless downshift");
                    }

                    // Getting back on the power before the result confirms is a
                    // driver timing miss, not a gearbox that failed to engage.
                    // Both used to report the same thing, which points the
                    // driver at recording a false negative.
                    {
                        GuidedVerificationDrive early = new GuidedVerificationDrive();
                        early.Start(6);
                        for (int guard = 0; guard < 40
                            && early.GetSnapshot().Title != "Downshift without pedal input"; guard++)
                        {
                            early.AddSample(GuidedSample(now, 4, 0, 0, 4000, 80, 100, true));
                            early.Next();
                        }
                        early.AddSample(GuidedSample(now, 4, 0, 90, 5200, 80, 220, true));
                        early.AddSample(GuidedSample(now.AddMilliseconds(60), 3, 0, 0, 6100, 79, 90, true));
                        // Back on the throttle well inside the confirm window.
                        early.AddSample(GuidedSample(now.AddMilliseconds(200), 3, 0, 80, 6300, 80, 210, true));
                        early.AddSample(GuidedSample(now.AddMilliseconds(3000), 3, 0, 80, 6500, 85, 210, true));
                        True(early.GetSnapshot().ResultReady, "concludes the attempt");
                        True(early.GetSnapshot().Result.Contains("throttle came back"),
                            "names the throttle rather than blaming the gearbox");
                    }

                    // Moving past a test with Next, having never attempted it,
                    // used to write the negative: a car that stalls, a gearbox
                    // that refuses. Nothing was measured, so nothing is recorded.
                    {
                        GuidedVerificationDrive untried = new GuidedVerificationDrive();
                        untried.Start(6);
                        // Reach the move-off test without concluding it: Next on
                        // an unfinished phase finishes it, so no sample may be
                        // fed after that point.
                        for (int guard = 0; guard < 5
                            && untried.GetSnapshot().Title != "Move-off clutch test"; guard++)
                        {
                            untried.Next();
                        }
                        Equal("Move-off clutch test", untried.GetSnapshot().Title, "reaches the move-off test");
                        // Sitting still, engine running, never asked to move.
                        untried.AddSample(GuidedSample(now, 0, 0, 0, 900, 0, 0, true));
                        untried.Next();
                        True(untried.GetSnapshot().Result.Contains("Nothing was measured"),
                            "says nothing was measured rather than recording a stall");
                        untried.Next();
                        Equal("not-tested", untried.GetResults().MoveOffWithoutPhysicalClutch,
                            "leaves an unattempted move-off unanswered");

                        for (int guard = 0; guard < 40
                            && untried.GetSnapshot().Title != "Full-throttle upshift"; guard++)
                        {
                            untried.AddSample(GuidedSample(now, 3, 0, 50, 4000, 80, 200, true));
                            untried.Next();
                        }
                        Equal("Full-throttle upshift", untried.GetSnapshot().Title, "reaches the upshift test");
                        // Driving along in one gear, never shifting.
                        untried.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 0, 90, 5000, 85, 220, true));
                        untried.AddSample(GuidedSample(now.AddMilliseconds(600), 3, 0, 90, 5200, 88, 220, true));
                        untried.Next();
                        True(untried.GetSnapshot().Result.Contains("no gear change was seen"),
                            "says no gear change was seen rather than recording a refusal");
                        untried.Next();
                        Equal("not-tested", untried.GetResults().ClutchlessUpshift,
                            "leaves an unattempted upshift unanswered");
                        Equal("not-tested", untried.GetResults().AutomaticCut,
                            "never infers an automatic cut from a test nobody ran");

                    // Sitting at the line in gear is where a driver waits, not
                    // an attempt to pull away. Counting the gear recorded a car
                    // that needs its clutch on a test nobody ran.
                    {
                        GuidedVerificationDrive waiting = new GuidedVerificationDrive();
                        waiting.Start(6);
                        for (int guard = 0; guard < 5
                            && waiting.GetSnapshot().Title != "Move-off clutch test"; guard++)
                        {
                            waiting.Next();
                        }
                        waiting.AddSample(GuidedSample(now, 1, 0, 0, 1200, 0, 40, true));
                        waiting.Next();
                        True(waiting.GetSnapshot().Result.Contains("Nothing was measured"),
                            "waiting in gear is not an attempt to pull away");
                        waiting.Next();
                        Equal("not-tested", waiting.GetResults().MoveOffWithoutPhysicalClutch,
                            "leaves the move-off unanswered when the car was never asked to move");

                        // And the gear count concludes instead of hanging when
                        // no gear was ever engaged.
                        Equal("Forward gears", waiting.GetSnapshot().Title, "reaches the gear count");
                        waiting.Next();
                        True(waiting.GetSnapshot().Result.Contains("no gear was ever engaged"),
                            "the gear count concludes rather than refusing to advance");
                        waiting.Next();
                        True(waiting.GetSnapshot().Title != "Forward gears", "the gear count advances");
                    }

                    // A shift taken at full throttle is not a lifted-throttle
                    // upshift, however long the driver coasted beforehand.
                    {
                    // An automatic cut is ignition-side, so the test reads torque
                    // rather than throttle. That makes a simulator publishing no
                    // torque indistinguishable from a car that does not cut,
                    // unless the draft says which happened - and only one of the
                    // two is worth re-driving for. Assetto Corsa EVO's first
                    // Huracan drive landed here.
                    {
                        GuidedVerificationDrive noTorque = new GuidedVerificationDrive();
                        noTorque.Start(6);
                        for (int guard = 0; guard < 40
                            && noTorque.GetSnapshot().Title != "Full-throttle upshift"; guard++)
                        {
                            noTorque.AddSample(GuidedSample(now, 3, 0, 0, 3000, 60, 0, true));
                            noTorque.Next();
                        }
                        Equal("Full-throttle upshift", noTorque.GetSnapshot().Title,
                            "reaches the upshift test with no torque channel");
                        noTorque.AddSample(GuidedSample(now, 3, 0, 95, 5400, 75, 0, true));
                        noTorque.AddSample(
                            GuidedSample(now.AddMilliseconds(200), 4, 0, 95, 4600, 77, 0, true));
                        True(noTorque.GetSnapshot().Result.Contains("published no engine torque"),
                            "names an absent torque channel instead of calling the trace inconclusive");
                        False(noTorque.GetSnapshot().Result.Contains("could not be established"),
                            "does not report an unmeasured cut as an inconclusive measurement");
                    }

                    // Torque present and holding through the change is a real
                    // negative reading, and says so with the numbers.
                    {
                        GuidedVerificationDrive held = new GuidedVerificationDrive();
                        held.Start(6);
                        for (int guard = 0; guard < 40
                            && held.GetSnapshot().Title != "Full-throttle upshift"; guard++)
                        {
                            held.AddSample(GuidedSample(now, 3, 0, 0, 3000, 60, 100, true));
                            held.Next();
                        }
                        held.AddSample(GuidedSample(now, 3, 0, 95, 5400, 75, 240, true));
                        held.AddSample(
                            GuidedSample(now.AddMilliseconds(200), 4, 0, 95, 4600, 77, 235, true));
                        True(held.GetSnapshot().Result.Contains("Engine torque held at"),
                            "reports a measured torque trace that shows no cut");
                    }

                        GuidedVerificationDrive noLift = new GuidedVerificationDrive();
                        noLift.Start(6);
                        for (int guard = 0; guard < 40
                            && noLift.GetSnapshot().Title != "Lifted-throttle upshift"; guard++)
                        {
                            noLift.AddSample(GuidedSample(now, 3, 0, 0, 3000, 60, 100, true));
                            noLift.Next();
                        }
                        Equal("Lifted-throttle upshift", noLift.GetSnapshot().Title, "reaches the lifted upshift");
                        // Coasting when the test arms, then full throttle through
                        // the shift without ever lifting for it.
                        noLift.AddSample(GuidedSample(now, 3, 0, 0, 4000, 70, 90, true));
                        noLift.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 0, 95, 5400, 75, 240, true));
                        noLift.AddSample(GuidedSample(now.AddMilliseconds(200), 4, 0, 95, 4600, 77, 235, true));
                        noLift.AddSample(GuidedSample(now.AddMilliseconds(900), 4, 0, 95, 4900, 82, 235, true));
                        False(noLift.GetSnapshot().ResultReady,
                            "never accepts a full-throttle shift as a lifted-throttle upshift");
                    }

                    // Changing gear while getting up to speed is not an attempt
                    // at the lifted-throttle test. Counting any gear change
                    // recorded a gearbox needing its clutch on a test the driver
                    // was skipping past.
                    {
                        GuidedVerificationDrive rolling = new GuidedVerificationDrive();
                        rolling.Start(6);
                        for (int guard = 0; guard < 40
                            && rolling.GetSnapshot().Title != "Lifted-throttle upshift"; guard++)
                        {
                            rolling.AddSample(GuidedSample(now, 3, 0, 0, 3000, 60, 100, true));
                            rolling.Next();
                        }
                        // Driving along, shifting up on the power, never lifting.
                        rolling.AddSample(GuidedSample(now, 3, 0, 95, 5400, 75, 240, true));
                        rolling.AddSample(GuidedSample(now.AddMilliseconds(120), 4, 0, 95, 4600, 78, 235, true));
                        rolling.Next();
                        True(rolling.GetSnapshot().Result.Contains("Nothing was measured"),
                            "a shift taken on the power is not an attempt at the lifted test");
                        rolling.Next();
                        Equal("not-tested", rolling.GetResults().ClutchlessUpshift,
                            "never records a clutch requirement from a test nobody ran");
                    }
                    }
                    // This car crept away with the clutch channel high and the
                    // result was accepted as clutch-free, which is the one
                    // combination worth questioning.
                    True(guidedResults.EvidenceNote.Contains("may be measuring the driver"), "warns when a clutch-free result was accepted with clutch input present");
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
                    skippedAutomaticTests.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 0, 25, 4800, 69, 115, true));
                    skippedAutomaticTests.AddSample(GuidedSample(now.AddMilliseconds(700), 3, 0, 0, 5600, 68, 115, true));
                    skippedAutomaticTests.Next();
                    GuidedDriveResults skippedResults = skippedAutomaticTests.GetResults();
                    Equal("not-tested", skippedResults.AutomaticCut, "does not infer no automatic cut when its test was skipped");
                    Equal("not-tested", skippedResults.AutomaticBlip, "does not infer no automatic blip when its test was skipped");

                    // A manual car will not even engage first without the
                    // clutch, so nothing happens for the test to detect and it
                    // used to wait forever. Sustained throttle against a
                    // stationary car settles it without the driver having to
                    // press anything.
                    var refusedMoveOff = new GuidedVerificationDrive();
                    refusedMoveOff.Start(null);
                    refusedMoveOff.AddSample(GuidedSample(now, 0, 0, 0, 1000, 0, 0, true));
                    refusedMoveOff.AddSample(GuidedSample(now.AddSeconds(1), 0, 0, 40, 1900, 0, 0, true));
                    False(refusedMoveOff.GetSnapshot().ResultReady, "gives the car time to pull away before concluding it cannot");
                    refusedMoveOff.AddSample(GuidedSample(now.AddSeconds(3), 0, 0, 40, 2000, 0, 0, true));
                    False(refusedMoveOff.GetSnapshot().ResultReady, "still waiting inside the window");
                    refusedMoveOff.AddSample(GuidedSample(now.AddSeconds(5.5), 0, 0, 40, 2000, 0, 0, true));
                    True(refusedMoveOff.GetSnapshot().ResultReady, "concludes on its own once the car has plainly refused to move");
                    True(refusedMoveOff.GetSnapshot().Result.Contains("standing-start clutch is required"), "states what the refusal means");
                    refusedMoveOff.Next();
                    Equal("no", refusedMoveOff.GetResults().MoveOffWithoutPhysicalClutch, "records that the car cannot pull away without the clutch");

                    // A running shift that will not go through leaves the box in
                    // neutral and grinds there. The test used to wait for a
                    // gear that could never arrive while the gearbox was
                    // destroyed, until the driver pressed Next.
                    var refusedUpshift = new GuidedVerificationDrive();
                    refusedUpshift.Start(null);
                    refusedUpshift.Skip();
                    refusedUpshift.Skip();
                    refusedUpshift.AddSample(GuidedSample(now, 3, 0, 90, 5000, 80, 150, true));
                    refusedUpshift.AddSample(GuidedSample(now.AddMilliseconds(200), 0, 0, 90, 5200, 80, 20, true));
                    False(refusedUpshift.GetSnapshot().ResultReady, "ignores the instant of neutral an ordinary shift passes through");
                    refusedUpshift.AddSample(GuidedSample(now.AddMilliseconds(1300), 0, 0, 90, 5300, 79, 20, true));
                    True(refusedUpshift.GetSnapshot().ResultReady, "concludes once the gearbox has plainly refused the gear");
                    True(refusedUpshift.GetSnapshot().Result.Contains("sat in neutral"), "says the gearbox would not take the gear");
                    refusedUpshift.Next();
                    Equal("not-tested", refusedUpshift.GetResults().ClutchlessUpshift, "moves to the lifted-throttle attempt rather than recording a failure");

                    var refusedDownshift = new GuidedVerificationDrive();
                    refusedDownshift.Start(null);
                    refusedDownshift.Skip();
                    refusedDownshift.Skip();
                    refusedDownshift.Skip();
                    refusedDownshift.Skip();
                    refusedDownshift.AddSample(GuidedSample(now, 4, 0, 0, 4300, 70, 120, true));
                    refusedDownshift.AddSample(GuidedSample(now.AddMilliseconds(200), 0, 0, 0, 4000, 69, 0, true));
                    False(refusedDownshift.GetSnapshot().ResultReady, "ignores a brief neutral on the way down");
                    refusedDownshift.AddSample(GuidedSample(now.AddMilliseconds(1300), 0, 0, 0, 3600, 68, 0, true));
                    True(refusedDownshift.GetSnapshot().ResultReady, "concludes a refused clutchless downshift without waiting for Next");
                    True(refusedDownshift.GetSnapshot().Result.Contains("sat in neutral"), "says the gearbox would not take the lower gear");

                    // A hint that understates the gearbox must not cap the
                    // count. This is how a real six-speed would have been
                    // recorded as a five-speed and never questioned.
                    var understatedHint = new GuidedVerificationDrive();
                    understatedHint.Start(5);
                    understatedHint.Skip();
                    for (int observedGear = 1; observedGear <= 6; observedGear++)
                    {
                        understatedHint.AddSample(GuidedSample(now, observedGear, 0, 30, 3000, 40, 100, true));
                    }
                    False(understatedHint.GetSnapshot().ResultReady, "keeps counting past a hint of five");
                    understatedHint.Next();
                    understatedHint.Next();
                    Equal(6, understatedHint.GetResults().ForwardGears.Value, "records the six gears observed, not the five suggested");

                    // The test asks the driver to hold the brake, so a car sat
                    // still under throttle against it has not refused anything
                    // yet. Concluding there would fail an automatic-clutch car
                    // for following the instructions.
                    var heldOnBrake = new GuidedVerificationDrive();
                    heldOnBrake.Start(null);
                    heldOnBrake.AddSample(GuidedSample(now, 0, 0, 0, 1000, 0, 0, true, 90.0));
                    heldOnBrake.AddSample(GuidedSample(now.AddSeconds(2), 1, 0, 30, 1500, 0, 40, true, 90.0));
                    heldOnBrake.AddSample(GuidedSample(now.AddSeconds(6), 1, 0, 30, 1500, 0, 40, true, 90.0));
                    False(heldOnBrake.GetSnapshot().ResultReady, "never counts time spent held on the brake as a refusal to move");
                    heldOnBrake.AddSample(GuidedSample(now.AddSeconds(7), 1, 0, 30, 1600, 4, 50, true));
                    heldOnBrake.AddSample(GuidedSample(now.AddSeconds(8), 1, 0, 30, 1700, 9, 55, true));
                    True(heldOnBrake.GetSnapshot().ResultReady, "accepts the car once the brake is released and it pulls away");
                    heldOnBrake.Next();
                    Equal("yes", heldOnBrake.GetResults().MoveOffWithoutPhysicalClutch, "records a clutch-free move-off after a braked hold");

                    // A slow automatic clutch must still reach the positive
                    // path rather than be judged by the refusal timeout.
                    var slowCreep = new GuidedVerificationDrive();
                    slowCreep.Start(null);
                    slowCreep.AddSample(GuidedSample(now, 0, 0, 0, 1000, 0, 0, true));
                    slowCreep.AddSample(GuidedSample(now.AddSeconds(1), 1, 0, 40, 1300, 0, 30, true));
                    slowCreep.AddSample(GuidedSample(now.AddSeconds(3), 1, 0, 40, 1500, 3, 45, true));
                    slowCreep.AddSample(GuidedSample(now.AddSeconds(4), 1, 0, 40, 1600, 6, 55, true));
                    True(slowCreep.GetSnapshot().ResultReady, "accepts a slow automatic clutch that eventually creeps away");
                    slowCreep.Next();
                    Equal("yes", slowCreep.GetResults().MoveOffWithoutPhysicalClutch, "does not fail a slow creep on the refusal timeout");

                    // A manual car needs the clutch to pull away, so the driver
                    // uses the pedal and the test correctly reports that a
                    // clutch is required. Clutch input is the expected finding
                    // here, not a doubt about it, so no warning is raised.
                    var manualMoveOff = new GuidedVerificationDrive();
                    manualMoveOff.Start(null);
                    manualMoveOff.AddSample(GuidedSample(now, 0, 0, 0, 1000, 0, 0, true));
                    manualMoveOff.AddSample(GuidedSample(now.AddMilliseconds(100), 1, 95, 30, 1400, 0, 20, true));
                    manualMoveOff.AddSample(GuidedSample(now.AddMilliseconds(900), 1, 20, 40, 1800, 12, 60, true));
                    manualMoveOff.Next();
                    manualMoveOff.Next();
                    Equal("no", manualMoveOff.GetResults().MoveOffWithoutPhysicalClutch, "records that this car needs the clutch to pull away");
                    Equal(string.Empty, manualMoveOff.GetResults().EvidenceNote ?? string.Empty, "stays quiet when needing the clutch is the result itself");

                    // A damaged dog box selects the lower gear and then sits in
                    // neutral. The simulator still reports the selected gear,
                    // so without an engagement check this reads as a successful
                    // clutchless downshift and writes a wrong record.
                    var damagedDownshift = new GuidedVerificationDrive();
                    damagedDownshift.Start(null);
                    damagedDownshift.Skip();
                    damagedDownshift.Skip();
                    damagedDownshift.Skip();
                    damagedDownshift.AddSample(GuidedSample(now, 2, 0, 80, 4500, 60, 150, true));
                    damagedDownshift.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 0, 20, 3900, 62, 140, true));
                    damagedDownshift.Next();
                    damagedDownshift.Skip();
                    damagedDownshift.AddSample(GuidedSample(now, 4, 0, 0, 4300, 70, 120, true));
                    damagedDownshift.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 0, 25, 4600, 69, 115, true));
                    False(damagedDownshift.GetSnapshot().ResultReady, "does not accept the selected gear on its own");
                    damagedDownshift.AddSample(GuidedSample(now.AddMilliseconds(400), 0, 0, 0, 3000, 68, 0, true));
                    True(damagedDownshift.GetSnapshot().ResultReady, "reports a result once the gearbox drops back to neutral");
                    True(damagedDownshift.GetSnapshot().Result.Contains("did not stay engaged"), "explains that the gear did not stay engaged");
                    damagedDownshift.Next();
                    Equal("no", damagedDownshift.GetResults().ClutchlessDownshift, "never records a failed engagement as a clutchless downshift");

                    // The gear index holds but the engine never takes drive, so
                    // engine speed per unit of road speed stays where it was.
                    var unengagedDownshift = new GuidedVerificationDrive();
                    unengagedDownshift.Start(null);
                    unengagedDownshift.Skip();
                    unengagedDownshift.Skip();
                    unengagedDownshift.Skip();
                    unengagedDownshift.AddSample(GuidedSample(now, 2, 0, 80, 4500, 60, 150, true));
                    unengagedDownshift.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 0, 20, 3900, 62, 140, true));
                    unengagedDownshift.Next();
                    unengagedDownshift.Skip();
                    unengagedDownshift.AddSample(GuidedSample(now, 4, 0, 0, 4300, 70, 120, true));
                    unengagedDownshift.AddSample(GuidedSample(now.AddMilliseconds(100), 3, 0, 25, 4400, 69, 115, true));
                    unengagedDownshift.AddSample(GuidedSample(now.AddMilliseconds(700), 3, 0, 0, 2000, 68, 0, true));
                    False(unengagedDownshift.GetSnapshot().ResultReady, "keeps waiting while engine speed stays decoupled from the wheels");
                    unengagedDownshift.AddSample(GuidedSample(now.AddMilliseconds(2600), 3, 0, 0, 1500, 65, 0, true));
                    True(unengagedDownshift.GetSnapshot().ResultReady, "gives up once the engine never takes drive");
                    True(unengagedDownshift.GetSnapshot().Result.Contains("never took drive"), "explains that the gearbox did not engage");

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
                GuidanceSnapshot retro = database.Preview("ams2", "formula-retro-v12");
                Equal("no", retro.AutoBlip, "Formula Retro V12 has no automatic blip in the simulator");
                Equal("unknown", retro.ManualBlip, "but its manual downshift blip is not established");
                GuidanceSnapshot brabham = database.Preview("ams2", "brabham-bt26a");
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
            // Nothing is composed into either line any more: the name is the
            // car's name and the class line is the class the simulator reports.
            AssertFittedPrefix(snapshot.DisplayName, snapshot.OverlayCarNameDetailed, label + " detailed car name");
            AssertFittedPrefix(snapshot.DisplayName, snapshot.OverlayCarNameCompact, label + " compact car name");
            AssertFittedPrefix(snapshot.DisplayName, snapshot.OverlayCarNameGlance, label + " glance car name");
            AssertFittedPrefix(snapshot.CarClass, snapshot.OverlayCarClassDetailed, label + " detailed car class");
            AssertFittedPrefix(snapshot.CarClass, snapshot.OverlayCarClassCompact, label + " compact car class");
            // The names an aero package used to lengthen were the ones that got
            // cut off. None of them carries one now, so none of them should be.
            False(snapshot.OverlayCarNameDetailed.EndsWith("...", StringComparison.Ordinal),
                label + " detailed car name is not truncated");
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
            bool engineStarted,
            double brake = 0.0)
        {
            return new GuidedTelemetrySample
            {
                TimestampUtc = timestamp,
                Gear = gear,
                Clutch = clutch,
                Throttle = throttle,
                Brake = brake,
                Rpm = rpm,
                SpeedKmh = speedKmh,
                EngineTorque = torque,
                EngineStarted = engineStarted
            };
        }
    }
}
