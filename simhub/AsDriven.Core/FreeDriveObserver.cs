using System;
using System.Collections.Generic;

namespace AsDriven.Core
{
    /// <summary>
    /// What ordinary driving showed about the gearbox, as counts.
    /// </summary>
    public sealed class FreeDriveSummary
    {
        /// <summary>Clutchless upshifts taken with the throttle held open, and accepted.</summary>
        public int FullThrottleUpshifts { get; set; }
        /// <summary>Of those, how many published torque with the throttle still held through the change.</summary>
        public int CutMeasured { get; set; }
        /// <summary>Of the measured ones, how many showed the torque collapse of an automatic cut.</summary>
        public int WithTorqueCut { get; set; }
        /// <summary>
        /// Full-throttle upshifts whose torque fell because the engine ran
        /// free between gears, which measures nothing about a cut.
        /// </summary>
        public int EngineRanFree { get; set; }
        /// <summary>Clutchless upshifts taken on a lifted throttle, and accepted.</summary>
        public int LiftedUpshifts { get; set; }
        /// <summary>Clutchless downshifts taken on a closed throttle that took drive.</summary>
        public int CoastDownshifts { get; set; }
        /// <summary>Of those, how many were followed by a throttle spike.</summary>
        public int WithThrottleSpike { get; set; }
        /// <summary>The largest such spike, as a percentage after the resting offset.</summary>
        public double PeakThrottleSpike { get; set; }
        /// <summary>Shifts set aside because clutch input was present.</summary>
        public int ShiftsWithClutch { get; set; }
        /// <summary>
        /// Counted shifts during which the clutch channel moved, on a channel
        /// already known to report the car's own clutch rather than the pedal.
        /// </summary>
        public int CountedWithVehicleClutch { get; set; }
        /// <summary>
        /// Shifts that were none of the tests: taken on part throttle, or a
        /// lower gear that never took drive.
        /// </summary>
        public int OtherShifts { get; set; }
        /// <summary>The samples around the most recent counted full-throttle upshift.</summary>
        public GuidedTelemetrySample[] UpshiftExample { get; set; }
        /// <summary>The samples around the most recent counted coast downshift.</summary>
        public GuidedTelemetrySample[] DownshiftExample { get; set; }

        public FreeDriveSummary Clone()
        {
            return (FreeDriveSummary)MemberwiseClone();
        }

        public bool HasEvents
        {
            get
            {
                return FullThrottleUpshifts > 0 || LiftedUpshifts > 0
                    || CoastDownshifts > 0 || ShiftsWithClutch > 0 || OtherShifts > 0;
            }
        }
    }

    /// <summary>
    /// Reads the guided tests out of ordinary driving.
    ///
    /// Every upshift a driver takes flat and every downshift taken off the
    /// throttle is already one of the scripted tests, performed without being
    /// asked. Watching a lap collects several of each where the scripted test
    /// collects one, and a car that takes them all needs no scripted test at
    /// all.
    ///
    /// It can only see what the gearbox accepted. A refusal looks like a shift
    /// the driver never tried, so nothing here ever concludes that a lift, a
    /// blip or the clutch is required; that still takes the scripted test,
    /// where the driver is known to have asked. A shift with clutch input is
    /// set aside for the same reason: it says nothing about shifting without.
    /// </summary>
    public sealed class FreeDriveObserver
    {
        // The thresholds are the guided detector's own, so a shift counted
        // here is one the scripted test would also have accepted.
        private const double FullThrottle = 70.0;
        private const double LiftedThrottle = 45.0;
        private const double ClosedThrottle = 10.0;
        private const double BlipThrottle = 15.0;
        private const double ClutchPresent = 20.0;
        private const double EngagementRatioMargin = 1.05;
        private const double MinimumSpeedKmh = 20.0;

        // A shift passes through neutral for an instant. Longer than this and
        // the gear that follows is a new selection, not the end of a shift.
        private const double NeutralPassageMilliseconds = 600.0;
        // How long the new gear has to hold before the shift is counted.
        private const double ConfirmMilliseconds = 600.0;
        // A driver going down through the gears for a corner does not wait
        // that long between shifts. A gear held at least this long before the
        // next shift began is judged on what it showed in that time, rather
        // than being dropped because it was not held for longer.
        private const double QuickShiftMilliseconds = 300.0;
        // Engine speed at the torque minimum, relative to when the gear was
        // left, above which the engine is taken to have run free.
        private const double FreeRevvingMargin = 1.03;
        // Time between the last sample in one gear and the first in the next
        // beyond which the box is taken to have passed through neutral.
        private const double NeutralSeenMilliseconds = 40.0;
        private const double BufferMilliseconds = 2500.0;
        private const int BufferMaximumSamples = 300;

        private sealed class PendingShift
        {
            public int From;
            public int To;
            public DateTime LeftAtUtc;
            public DateTime ArrivedAtUtc;
            public double BaselineRatio;
            /// <summary>The most recent sample still in the new gear.</summary>
            public GuidedTelemetrySample Latest;
        }

        private readonly Queue<GuidedTelemetrySample> _buffer = new Queue<GuidedTelemetrySample>();
        private FreeDriveSummary _summary = new FreeDriveSummary();
        private PendingShift _pending;
        private DateTime _coastDownshiftArrivedUtc = DateTime.MinValue;
        private int _engagedGear;
        private DateTime _engagedSeenUtc;
        private double _engagedRatio;

        /// <summary>
        /// What the throttle channel reads with the pedal released, which some
        /// telemetry readers never report as zero.
        /// </summary>
        public double ThrottleOffset { get; set; }

        /// <summary>
        /// True when the clutch channel is known not to follow the pedal: it
        /// already read as depressed with the car stopped and the driver doing
        /// nothing. Project Motor Racing reads 100% at rest and again through
        /// every downshift, as the car works its own clutch. Setting those
        /// shifts aside as the driver's left nothing to count at all, so on
        /// such a channel a shift is counted and the clutch movement recorded
        /// beside it, which is how the scripted test already treats it.
        /// </summary>
        public bool ClutchChannelReportsVehicle { get; set; }

        public void Reset()
        {
            _buffer.Clear();
            _summary = new FreeDriveSummary();
            _pending = null;
            _coastDownshiftArrivedUtc = DateTime.MinValue;
            _engagedGear = 0;
            _engagedRatio = 0.0;
        }

        public FreeDriveSummary GetSummary()
        {
            return _summary.Clone();
        }

        public void AddSample(GuidedTelemetrySample sample)
        {
            if (sample == null)
            {
                return;
            }
            _buffer.Enqueue(sample);
            while (_buffer.Count > BufferMaximumSamples
                || (sample.TimestampUtc - _buffer.Peek().TimestampUtc).TotalMilliseconds
                    > BufferMilliseconds)
            {
                _buffer.Dequeue();
            }
            if (_pending != null)
            {
                if (sample.Gear != _pending.To)
                {
                    // Left again before the full confirmation. Held long
                    // enough, it was a shift followed quickly by another;
                    // otherwise the gear did not hold and it was not an
                    // accepted shift at all.
                    if ((_pending.Latest.TimestampUtc - _pending.ArrivedAtUtc).TotalMilliseconds
                        >= QuickShiftMilliseconds)
                    {
                        Classify(_pending, _pending.Latest);
                    }
                    _pending = null;
                }
                else if ((sample.TimestampUtc - _pending.ArrivedAtUtc).TotalMilliseconds
                    >= ConfirmMilliseconds)
                {
                    Classify(_pending, sample);
                    _pending = null;
                }
                else
                {
                    _pending.Latest = sample;
                }
            }
            if (sample.Gear <= 0)
            {
                return;
            }
            if (_pending == null
                && _engagedGear > 0
                && Math.Abs(sample.Gear - _engagedGear) == 1
                && sample.SpeedKmh > MinimumSpeedKmh
                && (sample.TimestampUtc - _engagedSeenUtc).TotalMilliseconds
                    <= NeutralPassageMilliseconds)
            {
                _pending = new PendingShift
                {
                    From = _engagedGear,
                    To = sample.Gear,
                    LeftAtUtc = _engagedSeenUtc,
                    ArrivedAtUtc = sample.TimestampUtc,
                    BaselineRatio = _engagedRatio,
                    Latest = sample
                };
            }
            _engagedGear = sample.Gear;
            _engagedSeenUtc = sample.TimestampUtc;
            _engagedRatio = DriveRatio(sample);
        }

        private void Classify(PendingShift shift, GuidedTelemetrySample latest)
        {
            GuidedTelemetrySample[] samples = _buffer.ToArray();
            DateTime left = shift.LeftAtUtc;
            DateTime arrived = shift.ArrivedAtUtc;
            // Nothing after the last sample in this gear belongs to this
            // shift. When another followed quickly, what comes next is that
            // shift's cut or blip, not this one's.
            DateTime until = latest.TimestampUtc;

            bool clutchMoved = Maximum(
                samples, left.AddMilliseconds(-250.0), Earlier(arrived.AddMilliseconds(300.0), until),
                sample => sample.Clutch) > ClutchPresent;
            if (clutchMoved && !ClutchChannelReportsVehicle)
            {
                _summary.ShiftsWithClutch++;
                return;
            }

            // The car's own shift can show on the pedal channels just before
            // the gear index changes: a cut pulls the published throttle down
            // and a blip pushes it up. What the driver was doing is therefore
            // read from before that, and the last moments only have to not
            // contradict it.
            DateTime settled = left.AddMilliseconds(-150.0);
            GuidedTelemetrySample beforeShift = LastAtOrBefore(samples, settled)
                ?? LastAtOrBefore(samples, left);

            if (shift.To > shift.From)
            {
                double held = Minimum(samples, left.AddMilliseconds(-600.0), settled, Throttle);
                if (double.IsNaN(held))
                {
                    held = Throttle(beforeShift);
                }
                double atChange = Minimum(samples, settled, left, Throttle);
                if (held >= FullThrottle && atChange > LiftedThrottle)
                {
                    _summary.FullThrottleUpshifts++;
                    _summary.UpshiftExample = samples;
                    if (clutchMoved)
                    {
                        _summary.CountedWithVehicleClutch++;
                    }
                    DateTime to = Earlier(arrived.AddMilliseconds(300.0), until);
                    double highest = Maximum(
                        samples, left.AddMilliseconds(-600.0), to, Torque);
                    double lowest = Minimum(samples, settled, to, Torque);
                    // A cut is a torque collapse the driver did not ask for.
                    // With the throttle lifted during the change the collapse
                    // has an ordinary explanation, so that shift measures
                    // nothing about a cut either way.
                    if (highest > 0.0 && Minimum(samples, settled, to, Throttle) > LiftedThrottle)
                    {
                        bool collapsed = highest > 20.0 && lowest <= highest * 0.40;
                        // An engine held flat with no gear driving it runs
                        // away, and its torque falls as it climbs to the
                        // limiter. That is what an H-pattern box does between
                        // gears, and it is not a cut: a cut takes torque away
                        // while the engine holds its speed or slows. A live
                        // drive of such a car read as a cut on every upshift.
                        GuidedTelemetrySample leaving = LastAtOrBefore(samples, left);
                        GuidedTelemetrySample weakest = LowestTorque(samples, settled, to);
                        // Shifted at the limiter the engine has nowhere left
                        // to climb, so through neutral it only has to have
                        // held its speed: a cut with nothing driving the
                        // engine would let it fall.
                        bool throughNeutral = (arrived - left).TotalMilliseconds
                            >= NeutralSeenMilliseconds;
                        if (collapsed && leaving != null && weakest != null
                            && (weakest.Rpm > leaving.Rpm * FreeRevvingMargin
                                || (throughNeutral && weakest.Rpm >= leaving.Rpm * 0.99)))
                        {
                            _summary.EngineRanFree++;
                        }
                        else
                        {
                            _summary.CutMeasured++;
                            if (collapsed)
                            {
                                _summary.WithTorqueCut++;
                            }
                        }
                    }
                }
                else if (atChange <= LiftedThrottle)
                {
                    _summary.LiftedUpshifts++;
                }
                else
                {
                    _summary.OtherShifts++;
                }
                return;
            }

            // A blip can lead the reported gear change slightly, so the
            // throttle has to be closed before that and anything from there on
            // counts as the spike.
            DateTime spikeFrom = settled;
            double closedBefore;
            if ((left - _coastDownshiftArrivedUtc).TotalMilliseconds < ConfirmMilliseconds)
            {
                // This follows straight on from a downshift already counted
                // as taken off the throttle, and that one's blip is still
                // inside the usual window. A driver on the throttle would
                // still be on it now, so it only has to have closed again.
                closedBefore = Throttle(beforeShift);
            }
            else
            {
                closedBefore = Maximum(
                    samples, left.AddMilliseconds(-500.0), spikeFrom, Throttle);
            }
            // The gear index only says what was selected. A lower gear that
            // took drive holds the engine at a higher speed for the same road
            // speed, which a box left in neutral cannot do. The comparison is
            // with the engine before any blip began raising it.
            double baseline = beforeShift == null ? shift.BaselineRatio : DriveRatio(beforeShift);
            if (double.IsNaN(closedBefore) || closedBefore > ClosedThrottle
                || DriveRatio(latest) < baseline * EngagementRatioMargin)
            {
                _summary.OtherShifts++;
                return;
            }
            _summary.CoastDownshifts++;
            _coastDownshiftArrivedUtc = arrived;
            if (clutchMoved)
            {
                _summary.CountedWithVehicleClutch++;
            }
            _summary.DownshiftExample = samples;
            double spike = Maximum(
                samples, spikeFrom.AddMilliseconds(1.0),
                Earlier(arrived.AddMilliseconds(500.0), until), Throttle);
            if (!double.IsNaN(spike) && spike >= BlipThrottle)
            {
                _summary.WithThrottleSpike++;
                _summary.PeakThrottleSpike = Math.Max(_summary.PeakThrottleSpike, spike);
            }
        }

        private double Throttle(GuidedTelemetrySample sample)
        {
            return sample == null ? double.NaN : Math.Max(0.0, sample.Throttle - ThrottleOffset);
        }

        private static double Torque(GuidedTelemetrySample sample)
        {
            return double.IsInfinity(sample.EngineTorque) ? double.NaN : sample.EngineTorque;
        }

        private static DateTime Earlier(DateTime first, DateTime second)
        {
            return first <= second ? first : second;
        }

        private static double DriveRatio(GuidedTelemetrySample sample)
        {
            return sample.Rpm / Math.Max(sample.SpeedKmh, 1.0);
        }

        private static GuidedTelemetrySample LastAtOrBefore(
            GuidedTelemetrySample[] samples, DateTime moment)
        {
            GuidedTelemetrySample found = null;
            foreach (GuidedTelemetrySample sample in samples)
            {
                if (sample.TimestampUtc <= moment)
                {
                    found = sample;
                }
            }
            return found;
        }

        /// <summary>NaN when no sample in the window carries a value.</summary>
        private static double Maximum(
            GuidedTelemetrySample[] samples,
            DateTime from,
            DateTime to,
            Func<GuidedTelemetrySample, double> channel)
        {
            double result = double.NaN;
            foreach (GuidedTelemetrySample sample in samples)
            {
                if (sample.TimestampUtc < from || sample.TimestampUtc > to)
                {
                    continue;
                }
                double value = channel(sample);
                if (!double.IsNaN(value) && (double.IsNaN(result) || value > result))
                {
                    result = value;
                }
            }
            return result;
        }

        private static GuidedTelemetrySample LowestTorque(
            GuidedTelemetrySample[] samples, DateTime from, DateTime to)
        {
            GuidedTelemetrySample result = null;
            foreach (GuidedTelemetrySample sample in samples)
            {
                if (sample.TimestampUtc < from || sample.TimestampUtc > to)
                {
                    continue;
                }
                double value = Torque(sample);
                if (!double.IsNaN(value) && (result == null || value < Torque(result)))
                {
                    result = sample;
                }
            }
            return result;
        }

        private static double Minimum(
            GuidedTelemetrySample[] samples,
            DateTime from,
            DateTime to,
            Func<GuidedTelemetrySample, double> channel)
        {
            double result = double.NaN;
            foreach (GuidedTelemetrySample sample in samples)
            {
                if (sample.TimestampUtc < from || sample.TimestampUtc > to)
                {
                    continue;
                }
                double value = channel(sample);
                if (!double.IsNaN(value) && (double.IsNaN(result) || value < result))
                {
                    result = value;
                }
            }
            return result;
        }
    }
}
