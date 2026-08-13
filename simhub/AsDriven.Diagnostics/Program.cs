using System;
using System.IO;
using AsDriven.Core;

namespace AsDriven.Diagnostics
{
    internal static class Program
    {
        private static int Main(string[] args)
        {
            if (args.Length < 3)
            {
                Console.Error.WriteLine(
                    "Usage: AsDriven.Diagnostics.exe <data/v1> <game> <car identifier>");
                return 2;
            }

            try
            {
                AsDrivenDatabase database = AsDrivenDatabase.Load(
                    Path.GetFullPath(args[0]));
                GuidanceSnapshot result = database.Match(args[1], args[2]);
                Write("MatchStatus", result.MatchStatus);
                Write("RawGameName", result.RawGameName);
                Write("RawCarIdentifier", result.RawCarIdentifier);
                Write("DatasetVersion", result.DatasetVersion);
                Write("RecordId", result.RecordId);
                Write("DisplayName", result.DisplayName);
                Write("CarClass", result.CarClass);
                Write("ShiftType", result.ShiftType);
                Write("UpshiftGuidance", result.UpshiftGuidance);
                Write("DownshiftGuidance", result.DownshiftGuidance);
                Write("AutoBlip", result.AutoBlip);
                Write("ShiftCut", result.ShiftCut);
                Write("WheelRimShape", result.WheelRimShape);
                Write("SteeringDOR", result.HasSteeringDOR ? result.SteeringDOR.ToString() : string.Empty);
                Write("VerifiedGameVersion", result.VerifiedGameVersion);
                Write("Confidence", result.Confidence);
                Write("GuidanceSummary", result.GuidanceSummary);
                return result.HasMatch ? 0 : 1;
            }
            catch (Exception exception)
            {
                Console.Error.WriteLine("Database error: " + exception.Message);
                return 2;
            }
        }

        private static void Write(string name, string value)
        {
            Console.WriteLine(name + "=" + (value ?? string.Empty));
        }
    }
}
