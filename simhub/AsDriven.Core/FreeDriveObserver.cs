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
                    || CoastDownshifts > 0 || ShiftsWithClutch > 0;
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
        private const double BufferMilliseconds = 2500.0;
        private const int BufferMaximumSamples = 300;

        private sealed class PendingShift
        {
            public int From;
            public int To;
            public DateTime LeftAtUtc;
            public DateTime ArrivedAtUtc;
            public double BaselineRatio;
        }

        private readonly Queue<GuidedTelemetrySample> _buffer = new Queue<GuidedTelemetrySample>();
        private FreeDriveSummary _summary = new FreeDriveSummary();
        private PendingShift _pending;
        private int _engagedGear;
        private DateTime _engagedSeenUtc;
        private double _engagedRatio;

        /// <summary>
        /// What the throttle channel reads with the pedal released, which some
        /// telemetry readers never report as zero.
        /// </summary>
        public double ThrottleOffset { get; set; }

        public void Reset()
        {
            _buffer.Clear();
            _summary = new FreeDriveSummary();
            _pending = null;
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
                    // The gear did not hold, so whatever this was, it was not
                    // an accepted shift.
                    _pending = null;
                }
                else if ((sample.TimestampUtc - _pending.ArrivedAtUtc).TotalMilliseconds
                    >= ConfirmMilliseconds)
                {
                    Classify(_pending, sample);
                    _pending = null;
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
                    BaselineRatio = _engagedRatio
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

            if (Maximum(samples, left.AddMilliseconds(-250.0), arrived.AddMilliseconds(300.0),
                    sample => sample.Clutch) > ClutchPresent)
            {
                _summary.ShiftsWithClutch++;
                return;
            }

            if (shift.To > shift.From)
            {
                // The sample the old gear was last seen in is always inside
                // this window, so it is never empty however slow the telemetry.
                double before = Minimum(samples, left.AddMilliseconds(-250.0), left, Throttle);
                if (before >= FullThrottle)
                {
                    _summary.FullThrottleUpshifts++;
                    _summary.UpshiftExample = samples;
                    DateTime from = left.AddMilliseconds(-100.0);
                    DateTime to = arrived.AddMilliseconds(300.0);
                    double highest = Maximum(
                        samples, left.AddMilliseconds(-600.0), to, Torque);
                    double lowest = Minimum(samples, from, to, Torque);
                    // A cut is a torque collapse the driver did not ask for.
                    // With the throttle eased during the change the collapse
                    // has an ordinary explanation, so that shift measures
                    // nothing about a cut either way.
                    if (highest > 0.0 && Minimum(samples, from, to, Throttle) >= FullThrottle)
                    {
                        _summary.CutMeasured++;
                        if (highest > 20.0 && lowest <= highest * 0.40)
                        {
                            _summary.WithTorqueCut++;
                        }
                    }
                }
                else if (Throttle(LastAtOrBefore(samples, left)) <= LiftedThrottle)
                {
                    _summary.LiftedUpshifts++;
                }
                return;
            }

            // A blip can lead the reported gear change slightly, so the
            // throttle has to be closed before that and anything from there on
            // counts as the spike.
            DateTime spikeFrom = left.AddMilliseconds(-150.0);
            double closedBefore = Maximum(
                samples, left.AddMilliseconds(-500.0), spikeFrom, Throttle);
            if (double.IsNaN(closedBefore) || closedBefore > ClosedThrottle)
            {
                return;
            }
            // The gear index only says what was selected. A lower gear that
            // took drive holds the engine at a higher speed for the same road
            // speed, which a box left in neutral cannot do.
            if (DriveRatio(latest) < shift.BaselineRatio * EngagementRatioMargin)
            {
                return;
            }
            _summary.CoastDownshifts++;
            _summary.DownshiftExample = samples;
            double spike = Maximum(
                samples, spikeFrom.AddMilliseconds(1.0), arrived.AddMilliseconds(500.0), Throttle);
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
