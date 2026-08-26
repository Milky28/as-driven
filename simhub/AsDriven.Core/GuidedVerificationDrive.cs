using System;
using System.Globalization;

namespace AsDriven.Core
{
    public sealed class GuidedTelemetrySample
    {
        public DateTime TimestampUtc { get; set; }
        public int Gear { get; set; }
        public double Clutch { get; set; }
        public double Throttle { get; set; }
        public double Brake { get; set; }
        public double Rpm { get; set; }
        public double SpeedKmh { get; set; }
        public double EngineTorque { get; set; }
        public bool EngineStarted { get; set; }
    }

    public sealed class GuidedDriveResults
    {
        public string MoveOffWithoutPhysicalClutch { get; set; }
        public int? ForwardGears { get; set; }
        public string DirectGearSelection { get; set; }
        public string ClutchlessUpshift { get; set; }
        public string AutomaticCut { get; set; }
        public string AutomaticCutMethod { get; set; }
        public string ClutchlessDownshift { get; set; }
        public string AutomaticBlip { get; set; }
        public string AutomaticBlipMethod { get; set; }
        /// <summary>
        /// Whether the upshift went through at sustained full throttle, and
        /// whether the downshift went through on a closed throttle. They are
        /// the first attempt of a two-stage test, and the stage that failed is
        /// what establishes the technique: a lift or a blip the driver had to
        /// supply. Without them only the second stage survives, which shows the
        /// technique works and not that it was needed.
        /// </summary>
        public string FullThrottleUpshift { get; set; }
        public string CoastDownshift { get; set; }
        public string EvidenceNote { get; set; }

        public GuidedDriveResults()
        {
            MoveOffWithoutPhysicalClutch = "not-tested";
            DirectGearSelection = "not-tested";
            ClutchlessUpshift = "not-tested";
            AutomaticCut = "not-tested";
            ClutchlessDownshift = "not-tested";
            AutomaticBlip = "not-tested";
            AutomaticCutMethod = string.Empty;
            AutomaticBlipMethod = string.Empty;
            FullThrottleUpshift = "not-tested";
            CoastDownshift = "not-tested";
            EvidenceNote = string.Empty;
        }

        public GuidedDriveResults Clone()
        {
            return (GuidedDriveResults)MemberwiseClone();
        }
    }

    public sealed class GuidedDriveSnapshot
    {
        public bool Visible { get; set; }
        public bool Completed { get; set; }
        public bool ResultReady { get; set; }
        public bool ResultSuccessful { get; set; }
        public int StepNumber { get; set; }
        public int StepCount { get; set; }
        public string Title { get; set; }
        public string Prompt { get; set; }
        public string PromptLine1 { get; set; }
        public string PromptLine2 { get; set; }
        public string Status { get; set; }
        public string Result { get; set; }
        public string ResultSummary { get; set; }
        public string LiveValues { get; set; }
    }

    public sealed class GuidedVerificationDrive
    {
        private static readonly TimeSpan MoveOffConfirmationWindow =
            TimeSpan.FromMilliseconds(600.0);

        // Long enough that a slow automatic clutch still gets to creep away and
        // pass on the positive path before this concludes the opposite.
        private static readonly TimeSpan MoveOffRefusalWindow =
            TimeSpan.FromSeconds(4.0);

        // A running shift that will not go through without the clutch leaves
        // the gearbox in neutral with the car still moving, and it grinds for
        // as long as the driver holds it there. Long enough to ignore the
        // instant of neutral every ordinary shift passes through, short enough
        // to stop the grinding quickly.
        private static readonly TimeSpan RunningShiftRefusalWindow =
            TimeSpan.FromMilliseconds(900.0);

        private enum Phase
        {
            Idle,
            Intro,
            MoveOff,
            GearCount,
            FullThrottleUpshift,
            LiftedUpshift,
            CoastDownshift,
            ManualBlipDownshift,
            Complete,
            Cancelled
        }

        private readonly object _sync = new object();
        private Phase _phase = Phase.Idle;
        private GuidedDriveResults _results = new GuidedDriveResults();
        private GuidedTelemetrySample _lastSample;
        private int? _suggestedGears;
        private int _baselineGear;

        // A downshift is not accepted on the gear index alone. The simulator
        // reports the gear the driver selected, so a gearbox that failed to
        // engage still reads as a successful shift. Engine speed per unit of
        // road speed settles it: a lower gear raises that ratio and holds it,
        // while a box left in neutral decays towards idle with the car still
        // moving.
        private const double EngagementRatioMargin = 1.05;
        private const double EngagementConfirmSeconds = 0.5;
        private const double EngagementTimeoutSeconds = 2.5;
        private int _downshiftCandidateGear;
        private DateTime _downshiftCandidateAtUtc;
        private double _baselineDriveRatio;
        private int _maximumGear;
        private bool _armed;
        /// <summary>
        /// Whether the gear ever changed during this attempt, including into
        /// neutral. It is the difference between a driver who tried and a car
        /// that refused, and a driver who never tried at all.
        /// </summary>
        private bool _gearChangeSeen;
        private int _previousGear;
        /// <summary>Nothing was measured, so the answer stays unrecorded.</summary>
        private bool _attemptNotTested;
        /// <summary>
        /// Throttle at the moment the gear went up. The lift check used the
        /// lowest throttle since arming, and arming only needs the car to be
        /// rolling, so coasting up to the test counted as the lift and a
        /// shift taken at full throttle passed as a lifted one.
        /// </summary>
        private double _upshiftThrottleAtChange;
        private bool _attemptAccepted;
        private bool _automaticActionObserved;
        private bool _resultReady;
        private bool _hasCompletedResults;
        private bool _fullThrottleTestFailed;
        private bool _coastDownshiftTestFailed;
        private bool _engineWasRunning;
        private DateTime? _moveOffMovementStartedUtc;
        private DateTime? _moveOffRefusalStartedUtc;
        private DateTime? _neutralWhileMovingSinceUtc;
        private string _result = string.Empty;
        private double _maximumClutch;
        /// <summary>Clutch reading with the car stopped, before the driver acted.</summary>
        private double _restingClutch;
        private bool _restingClutchSeen;
        /// <summary>Throttle reading at the same moment, for the same reason.</summary>
        private double _restingThrottle;
        private bool _restingThrottleSeen;
        private double _minimumThrottle;
        private double _maximumThrottle;
        /// <summary>
        /// Throttle seen since the downshift attempt armed, which is the only
        /// window in which a spike can be the car's. <see cref="_maximumThrottle"/>
        /// starts at the attempt, so it banks the throttle the driver was still
        /// carrying before lifting, and reading a blip from it reported the
        /// driver's own pedal as an automatic blip.
        /// </summary>
        private double _downshiftArmedThrottle;
        /// <summary>
        /// Whether the throttle came back while the attempt was waiting to
        /// confirm engagement. Confirmation needs a closed throttle, so this
        /// separates a driver who got back on the power from a gearbox that
        /// never took drive; the two used to report the same failure.
        /// </summary>
        private bool _downshiftThrottleReturned;
        private double _maximumTorque;
        private double _minimumTorque;
        private double _upshiftMaximumTorque;
        private double _upshiftMinimumTorque;
        private double _upshiftMaximumThrottle;
        private double _upshiftMinimumThrottle;
        private DateTime? _upshiftGearChangedUtc;

        public void Start(int? suggestedForwardGears)
        {
            lock (_sync)
            {
                _suggestedGears = suggestedForwardGears;
                _results = new GuidedDriveResults();
                _hasCompletedResults = false;
                _fullThrottleTestFailed = false;
                _coastDownshiftTestFailed = false;
                _phase = Phase.MoveOff;
                // Session-scoped, unlike the per-attempt trace: the clutch at
                // rest is read once during move-off and quoted by later phases,
                // and ResetTrace runs on every phase advance.
                _restingClutch = 0.0;
                _restingClutchSeen = false;
                _restingThrottle = 0.0;
                _restingThrottleSeen = false;
                ResetTrace();
            }
        }

        public void Cancel()
        {
            lock (_sync)
            {
                if (_phase != Phase.Complete)
                {
                    _hasCompletedResults = false;
                }
                _phase = Phase.Cancelled;
                ResetTrace();
            }
        }

        public void AddSample(GuidedTelemetrySample sample)
        {
            if (sample == null)
            {
                return;
            }
            lock (_sync)
            {
                _lastSample = sample;
                if (!IsTestPhase(_phase)
                    || (_resultReady && _phase != Phase.GearCount))
                {
                    return;
                }
                UpdateTrace(sample);
                DetectResult(sample);
            }
        }

        public void FinishAttempt()
        {
            lock (_sync)
            {
                if (!IsTestPhase(_phase) || _resultReady)
                {
                    return;
                }
                // Ending a phase that was never attempted used to write the
                // negative, so a driver moving on with Next recorded a car that
                // stalls, or a gearbox that refuses, having measured neither.
                // An unattempted phase now records nothing, the way Skip does.
                if (!WasAttempted())
                {
                    _attemptNotTested = true;
                    _resultReady = true;
                    _attemptAccepted = false;
                    _result = NothingMeasuredMessage(_phase);
                    return;
                }
                switch (_phase)
                {
                    case Phase.MoveOff:
                        SetResult(false, false, "No clutch-free movement was detected; record this as stalls/requires clutch.");
                        break;
                    case Phase.GearCount:
                        if (_maximumGear > 0)
                        {
                            _attemptAccepted = true;
                            _resultReady = true;
                            _result = "Highest gear reached: " + _maximumGear + ".";
                        }
                        break;
                    case Phase.FullThrottleUpshift:
                        SetResult(false, false, "No full-throttle clutchless upshift was detected. Accept to try again with a throttle lift.");
                        break;
                    case Phase.LiftedUpshift:
                        SetResult(false, false, "No lifted-throttle clutchless upshift was detected; physical clutch may be required for running upshifts.");
                        break;
                    case Phase.CoastDownshift:
                        SetResult(false, false, "No clutchless downshift was detected. Accept to retry with a manual throttle blip.");
                        break;
                    case Phase.ManualBlipDownshift:
                        SetResult(false, false, "No manually blipped clutchless downshift was detected; physical clutch may be required for running downshifts.");
                        break;
                }
            }
        }

        public void Next()
        {
            lock (_sync)
            {
                if (_phase == Phase.Complete)
                {
                    _phase = Phase.Idle;
                    ResetTrace();
                    return;
                }
                if (!_resultReady)
                {
                    FinishAttempt();
                    return;
                }
                AcceptResultAndAdvance();
            }
        }

        public void Retry()
        {
            lock (_sync)
            {
                if (IsTestPhase(_phase))
                {
                    ResetTrace();
                }
            }
        }

        public void Skip()
        {
            lock (_sync)
            {
                if (!IsTestPhase(_phase))
                {
                    return;
                }
                AdvanceAfterSkip();
            }
        }

        public GuidedDriveResults GetResults()
        {
            lock (_sync)
            {
                return _results.Clone();
            }
        }

        public GuidedDriveSnapshot GetSnapshot()
        {
            lock (_sync)
            {
                int step = StepNumber(_phase);
                return new GuidedDriveSnapshot
                {
                    Visible = _phase != Phase.Idle && _phase != Phase.Cancelled,
                    Completed = _hasCompletedResults,
                    ResultReady = _resultReady,
                    ResultSuccessful = _resultReady && _attemptAccepted,
                    StepNumber = step,
                    StepCount = 6,
                    Title = Title(_phase),
                    Prompt = Prompt(_phase),
                    PromptLine1 = PromptLine1(_phase),
                    PromptLine2 = PromptLine2(_phase),
                    Status = Status(_phase),
                    Result = _result,
                    ResultSummary = ResultSummary(_phase),
                    LiveValues = LiveValues(_lastSample)
                };
            }
        }

        private void UpdateTrace(GuidedTelemetrySample sample)
        {
            if (_previousGear != int.MinValue && sample.Gear != _previousGear)
            {
                _gearChangeSeen = true;
            }
            _previousGear = sample.Gear;
            _maximumClutch = Math.Max(_maximumClutch, sample.Clutch);
            _minimumThrottle = Math.Min(_minimumThrottle, sample.Throttle);
            _maximumThrottle = Math.Max(_maximumThrottle, sample.Throttle);
            if (sample.EngineTorque > 0.0)
            {
                _maximumTorque = Math.Max(_maximumTorque, sample.EngineTorque);
                _minimumTorque = Math.Min(_minimumTorque, sample.EngineTorque);
            }
            if (sample.Gear > 0)
            {
                _maximumGear = Math.Max(_maximumGear, sample.Gear);
            }
        }

        private void DetectResult(GuidedTelemetrySample sample)
        {
            switch (_phase)
            {
                case Phase.MoveOff:
                    bool engineRunning = sample.EngineStarted && sample.Rpm >= 200.0;
                    if (engineRunning)
                    {
                        _engineWasRunning = true;
                    }
                    if (!_armed && _engineWasRunning && sample.SpeedKmh < 1.0)
                    {
                        _armed = true;
                        // The clutch reading with the car stopped and the driver
                        // not yet doing anything. Some simulators publish the
                        // car's own clutch actuation on this channel rather than
                        // the pedal - Assetto Corsa EVO shows it fully depressed
                        // at rest and feeding out under throttle - and knowing
                        // that turns a later "clutch input was present" caveat
                        // into evidence that the car works its own clutch.
                        _restingClutch = sample.Clutch;
                        _restingClutchSeen = true;
                        // And the throttle, which decides whether a later spike
                        // can be read as the car blipping. A channel already
                        // open with the car stopped and no foot on the pedal is
                        // not reporting the pedal, so a spike on it is not
                        // evidence of anything the driver can act on.
                        _restingThrottle = sample.Throttle;
                        _restingThrottleSeen = true;
                    }
                    if (_armed && _engineWasRunning && !engineRunning)
                    {
                        SetResult(
                            false,
                            false,
                            _moveOffMovementStartedUtc.HasValue || sample.SpeedKmh >= 1.0
                                ? "The car rolled briefly, but the engine stalled; standing-start clutch is required."
                                : "The engine stopped before the car moved; standing-start clutch is required.");
                    }
                    else if (_armed && engineRunning
                        && sample.Gear > 0 && sample.SpeedKmh >= 2.0)
                    {
                        if (!_moveOffMovementStartedUtc.HasValue)
                        {
                            _moveOffMovementStartedUtc = sample.TimestampUtc;
                        }
                        else if (sample.TimestampUtc - _moveOffMovementStartedUtc.Value
                            >= MoveOffConfirmationWindow)
                        {
                            SetResult(
                                true,
                                false,
                                "The car sustained movement with the engine running while the test required no physical clutch input."
                                    + VehicleClutchSummary());
                        }
                    }
                    else if (_armed && sample.SpeedKmh < 1.0)
                    {
                        _moveOffMovementStartedUtc = null;
                        // A car needing its clutch normally stalls the moment
                        // it is released in gear, which the stall branch above
                        // catches. This is the backstop for one that neither
                        // stalls nor pulls, so the test still settles instead
                        // of waiting for movement that cannot come.
                        // The prompt asks for light throttle, which is often
                        // well under fifteen percent, so the attempt has to
                        // count from a genuinely light application. Holding the
                        // brake is part of the test, not a refusal to move, so
                        // it never counts towards this.
                        if (engineRunning && sample.Throttle >= 8.0 && sample.Brake < 10.0)
                        {
                            if (!_moveOffRefusalStartedUtc.HasValue)
                            {
                                _moveOffRefusalStartedUtc = sample.TimestampUtc;
                            }
                            else if (sample.TimestampUtc - _moveOffRefusalStartedUtc.Value
                                >= MoveOffRefusalWindow)
                            {
                                SetResult(
                                    false,
                                    false,
                                    "Sustained throttle moved the car nowhere without the clutch, "
                                        + "so a standing-start clutch is required.");
                            }
                        }
                        else
                        {
                            _moveOffRefusalStartedUtc = null;
                        }
                    }
                    break;
                case Phase.GearCount:
                    // Deliberately never completes on its own. It used to stop
                    // as soon as the observed gear reached SimHub's suggested
                    // count, which is CarSettings_MaxGears: a hint the project
                    // treats as unreliable and forbids from setting a gear
                    // count, having seen it report 42, 119 and 150. Completing
                    // on it made the drive confirm the hint rather than measure
                    // the car, and told the driver they were finished at
                    // whatever the hint said. Only the driver can know that the
                    // gearbox will not go higher, so the driver ends this test.
                    break;
                case Phase.FullThrottleUpshift:
                    DetectUpshift(sample, requireLift: false);
                    break;
                case Phase.LiftedUpshift:
                    DetectUpshift(sample, requireLift: true);
                    break;
                case Phase.CoastDownshift:
                    DetectDownshift(sample, manualBlip: false);
                    break;
                case Phase.ManualBlipDownshift:
                    DetectDownshift(sample, manualBlip: true);
                    break;
            }
        }

        /// <summary>
        /// True once the gearbox has sat in neutral with the car still moving
        /// for long enough to mean the shift was attempted and refused.
        ///
        /// A running shift that will not go through without the clutch leaves
        /// the box in neutral and grinds there for as long as the driver holds
        /// it. The test cannot see the shift request, only that no higher or
        /// lower gear ever arrives, so it used to wait indefinitely while the
        /// gearbox was destroyed. Every ordinary shift passes through neutral
        /// for an instant, which is why this needs to persist.
        /// </summary>
        private bool RefusedIntoNeutral(GuidedTelemetrySample sample)
        {
            if (sample.Gear > 0 || sample.SpeedKmh <= 5.0)
            {
                _neutralWhileMovingSinceUtc = null;
                return false;
            }
            if (!_neutralWhileMovingSinceUtc.HasValue)
            {
                _neutralWhileMovingSinceUtc = sample.TimestampUtc;
                return false;
            }
            return sample.TimestampUtc - _neutralWhileMovingSinceUtc.Value
                >= RunningShiftRefusalWindow;
        }

        private void DetectUpshift(GuidedTelemetrySample sample, bool requireLift)
        {
            if (!_armed && sample.Gear > 0 && sample.SpeedKmh > 5.0
                && (requireLift || sample.Throttle >= 70.0))
            {
                _armed = true;
                _baselineGear = sample.Gear;
                _upshiftMaximumTorque = sample.EngineTorque;
                _upshiftMinimumTorque = sample.EngineTorque;
                _upshiftMaximumThrottle = sample.Throttle;
                _upshiftMinimumThrottle = sample.Throttle;
            }
            if (!_armed)
            {
                return;
            }
            if (!double.IsNaN(sample.EngineTorque)
                && !double.IsInfinity(sample.EngineTorque))
            {
                _upshiftMaximumTorque = Math.Max(
                    _upshiftMaximumTorque,
                    sample.EngineTorque);
                _upshiftMinimumTorque = Math.Min(
                    _upshiftMinimumTorque,
                    sample.EngineTorque);
            }
            _upshiftMaximumThrottle = Math.Max(
                _upshiftMaximumThrottle,
                sample.Throttle);
            _upshiftMinimumThrottle = Math.Min(
                _upshiftMinimumThrottle,
                sample.Throttle);
            if (RefusedIntoNeutral(sample))
            {
                SetResult(
                    false,
                    false,
                    requireLift
                        ? "The gearbox sat in neutral and would not take the next gear without the "
                            + "clutch, so running upshifts need it."
                        : "The gearbox sat in neutral and would not take the next gear at full "
                            + "throttle. Accept to try again with a throttle lift.");
                return;
            }
            if (sample.Gear <= _baselineGear)
            {
                return;
            }
            if (double.IsNaN(_upshiftThrottleAtChange))
            {
                _upshiftThrottleAtChange = sample.Throttle;
            }
            bool liftObserved = _upshiftThrottleAtChange <= 45.0;
            if (requireLift && !liftObserved)
            {
                return;
            }
            bool torqueCut = !requireLift
                && _upshiftMaximumThrottle >= 70.0
                && _upshiftMaximumTorque > 20.0
                && _upshiftMinimumTorque <= (_upshiftMaximumTorque * 0.40);
            if (!_upshiftGearChangedUtc.HasValue)
            {
                _upshiftGearChangedUtc = sample.TimestampUtc;
            }
            if (!requireLift
                && !torqueCut
                && _upshiftMinimumThrottle <= 45.0
                && sample.Throttle < 70.0
                && sample.TimestampUtc - _upshiftGearChangedUtc.Value
                    < TimeSpan.FromMilliseconds(350.0))
            {
                return;
            }
            // A throttle dip is not cut evidence. It can be driver input,
            // traction-control intervention, or a simulator's telemetry
            // representation. A sequential upshift cut is ignition-side, so
            // only a torque collapse while throttle demand stays high uniquely
            // supports it.
            bool automaticCut = torqueCut;
            string message = requireLift
                ? "Clutchless upshift accepted after a throttle lift."
                : "Full-throttle clutchless upshift accepted. "
                    + (automaticCut
                        ? "A shift-local torque interruption was detected while throttle demand stayed high."
                        : CutEvidenceSummary())
                    + VehicleClutchSummary();
            SetResult(true, automaticCut, message);
        }

        private void DetectDownshift(GuidedTelemetrySample sample, bool manualBlip)
        {
            if (!_armed && sample.Gear > 1 && sample.SpeedKmh > 5.0)
            {
                bool throttleClosed = !manualBlip ? sample.Throttle <= 10.0 : true;
                // The gear to compare against is the one the driver was in
                // *before* lifting. Capturing it at arming meant a driver who
                // lifted and downshifted inside one telemetry sample armed on
                // the gear they had already selected, so the attempt waited for
                // something lower, found nothing, and timed out as "no
                // clutchless downshift" on a shift that plainly happened.
                if (!throttleClosed || _baselineGear == 0)
                {
                    _baselineGear = sample.Gear;
                    _baselineDriveRatio = DriveRatio(sample);
                }
                if (throttleClosed)
                {
                    _armed = true;
                }
            }
            if (!_armed)
            {
                return;
            }
            // Arming already required a closed throttle, so anything above it
            // from here is the car blipping or a pedal the driver was asked not
            // to touch. Either way it is not throttle carried in from before.
            _downshiftArmedThrottle = Math.Max(_downshiftArmedThrottle, sample.Throttle);

            if (_downshiftCandidateGear == 0)
            {
                if (RefusedIntoNeutral(sample))
                {
                    SetResult(
                        false,
                        false,
                        manualBlip
                            ? "The gearbox sat in neutral and would not take the lower gear even "
                                + "with a blip, so running downshifts need the clutch."
                            : "The gearbox sat in neutral and would not take the lower gear. "
                                + "Accept to retry with a manual throttle blip.");
                    return;
                }
                if (sample.Gear <= 0 || sample.Gear >= _baselineGear)
                {
                    return;
                }
                // A lower gear was selected. Hold the result until the gearbox
                // proves it took drive.
                _downshiftCandidateGear = sample.Gear;
                _downshiftCandidateAtUtc = sample.TimestampUtc;
                return;
            }

            if (sample.Gear <= 0 || sample.Gear >= _baselineGear)
            {
                SetResult(
                    false,
                    false,
                    "The selected gear did not stay engaged. The gearbox may be damaged and left in "
                        + "neutral, so this attempt proves nothing about clutchless downshifting. "
                        + "Retry after repairing, or skip and answer it in the form.");
                return;
            }

            double elapsed = (sample.TimestampUtc - _downshiftCandidateAtUtc).TotalSeconds;
            bool blip = _downshiftArmedThrottle >= 15.0;
            // Throttle after the shift means opposite things in the two phases.
            // The coast test asks for no pedal input at all, so throttle there is
            // the driver spoiling the attempt and confirmation waits for it to
            // close. The manual-blip test asks for throttle, and rev-matching
            // does not end at the gear change - the driver blips and drives away
            // on it - so requiring a closed throttle asked for the shift and then
            // for the technique to be abandoned mid-motion. It made the correct
            // input fail the test.
            //
            // Engagement is proven either way by the drive ratio: the gear holds
            // the engine to the wheels at a ratio the baseline cannot reach, and
            // that is a property of the gearbox rather than of the pedal. So the
            // blip phase confirms on ratio and gear stability alone.
            if (!manualBlip && sample.Throttle > 10.0)
            {
                _downshiftThrottleReturned = true;
            }
            if ((manualBlip || sample.Throttle <= 10.0) && elapsed >= EngagementConfirmSeconds)
            {
                if (DriveRatio(sample) >= _baselineDriveRatio * EngagementRatioMargin)
                {
                    if (manualBlip && !blip)
                    {
                        return;
                    }
                    SetResult(
                        true,
                        blip,
                        manualBlip
                            ? "Clutchless downshift accepted after the driver's manual throttle blip."
                            : "Clutchless downshift accepted with no pedal input. "
                                // Report how big it was, not just that it happened.
                                // A rev-matching blip is a large, brief opening;
                                // an idle-control or driveline artefact sits just
                                // over the threshold. Both read as "detected"
                                // and only the magnitude tells them apart, so a
                                // reviewer should not have to re-drive the car to
                                // learn which one this was.
                                + (blip
                                    ? "A throttle spike was detected, peaking at "
                                        + _downshiftArmedThrottle.ToString("0", CultureInfo.InvariantCulture)
                                        + "% (the threshold is 15%)."
                                        + RestingThrottleSummary()
                                    : "No automatic throttle spike was detected.")
                                + VehicleClutchSummary());
                    return;
                }
            }
            if (elapsed >= EngagementTimeoutSeconds)
            {
                string reason;
                if (manualBlip && !blip)
                {
                    // The one thing this phase needs and did not get. Saying so
                    // beats the generic engagement failure, which would send the
                    // driver to look at the gearbox instead of the pedal.
                    reason = "The downshift was seen, but no throttle blip was detected with it. "
                        + "Blip the throttle as you select the lower gear, then retry.";
                }
                else if (_downshiftThrottleReturned)
                {
                    reason = "The downshift was seen, but the throttle came back before the result "
                        + "was confirmed. Confirming needs a closed throttle, so stay off it until "
                        + "the result appears, then retry.";
                }
                else
                {
                    reason = "The lower gear was selected but the engine never took drive from the "
                        + "wheels, so the gearbox did not engage. Retry, or skip and answer it "
                        + "in the form.";
                }
                SetResult(false, false, reason);
            }
        }

        private void SetResult(bool accepted, bool automaticAction, string message)
        {
            _attemptAccepted = accepted;
            _automaticActionObserved = automaticAction;
            _resultReady = true;
            _result = message;
        }

        private void AcceptResultAndAdvance()
        {
            RememberVehicleClutchTelemetry();
            if (_attemptNotTested)
            {
                // Nothing was measured, so every downstream flag stays as it
                // was and the answer is left for the form.
                AdvanceAfterSkip();
                return;
            }
            switch (_phase)
            {
                case Phase.MoveOff:
                    _results.MoveOffWithoutPhysicalClutch = _attemptAccepted ? "yes" : "no";
                    MoveTo(Phase.GearCount);
                    break;
                case Phase.GearCount:
                    _results.ForwardGears = _maximumGear > 0 ? (int?)_maximumGear : null;
                    _results.DirectGearSelection = "not-tested";
                    MoveTo(Phase.FullThrottleUpshift);
                    break;
                case Phase.FullThrottleUpshift:
                    if (_attemptAccepted)
                    {
                        _results.ClutchlessUpshift = "yes";
                        _results.FullThrottleUpshift = "yes";
                        _results.AutomaticCut = _automaticActionObserved ? "yes" : "unknown";
                        _results.AutomaticCutMethod = _result;
                        MoveTo(Phase.CoastDownshift);
                    }
                    else
                    {
                        _fullThrottleTestFailed = true;
                        _results.FullThrottleUpshift = "no";
                        MoveTo(Phase.LiftedUpshift);
                    }
                    break;
                case Phase.LiftedUpshift:
                    _results.ClutchlessUpshift = _attemptAccepted ? "yes" : "no";
                    _results.AutomaticCut = _fullThrottleTestFailed ? "no" : "not-tested";
                    _results.AutomaticCutMethod = _result;
                    MoveTo(Phase.CoastDownshift);
                    break;
                case Phase.CoastDownshift:
                    if (_attemptAccepted)
                    {
                        _results.ClutchlessDownshift = "yes";
                        _results.CoastDownshift = "yes";
                        // The message already says a spike on a channel that
                        // does not follow the pedal is no evidence of a blip.
                        // The recorded value has to say the same thing, or the
                        // record asserts a blip its own explanation disowns.
                        // "no" is not available either: on a channel like that
                        // the absence of a spike would be equally meaningless.
                        // This mirrors the automatic cut, which already answers
                        // unknown rather than no when nothing could be measured.
                        _results.AutomaticBlip = ThrottleChannelFollowsPedal()
                            ? (_automaticActionObserved ? "yes" : "no")
                            : "unknown";
                        _results.AutomaticBlipMethod = _result;
                        MoveTo(Phase.Complete);
                    }
                    else
                    {
                        _coastDownshiftTestFailed = true;
                        _results.CoastDownshift = "no";
                        MoveTo(Phase.ManualBlipDownshift);
                    }
                    break;
                case Phase.ManualBlipDownshift:
                    _results.ClutchlessDownshift = _attemptAccepted ? "yes" : "no";
                    _results.AutomaticBlip = _coastDownshiftTestFailed ? "no" : "not-tested";
                    _results.AutomaticBlipMethod = _result;
                    MoveTo(Phase.Complete);
                    break;
            }
        }

        /// <summary>
        /// True when a test that assumes no clutch was nonetheless accepted
        /// while clutch input was present.
        ///
        /// The telemetry is SimHub's clutch channel, which cannot be separated
        /// into pedal movement and any clutch the car works itself. That
        /// ambiguity only matters when the result claims the car did something
        /// without a clutch, because then the reading may be measuring the
        /// driver instead. A rejected attempt is unremarkable: needing the
        /// clutch is exactly what it found.
        /// </summary>
        private bool ClutchContradictsAcceptedResult()
        {
            if (_maximumClutch <= 20.0 || !_attemptAccepted)
            {
                return false;
            }
            return _phase == Phase.MoveOff
                || _phase == Phase.FullThrottleUpshift
                || _phase == Phase.LiftedUpshift
                || _phase == Phase.CoastDownshift
                || _phase == Phase.ManualBlipDownshift;
        }

        private string VehicleClutchSummary()
        {
            if (_maximumClutch <= 20.0)
            {
                return string.Empty;
            }
            // The caution stands: a driver resting a foot on the pedal looks
            // the same as a car working its own clutch, which is the mistake it
            // exists to catch. What the resting reading adds is where to look -
            // a channel already high with the car stopped is either the car's
            // own actuation or a held pedal, and the driver knows which.
            string caution =
                " Clutch input was present; confirm it was the car and not the pedal.";
            if (_restingClutchSeen && _restingClutch > 20.0)
            {
                caution += " It already read " + Math.Round(_restingClutch)
                    + "% with the car stopped before any test began, so if the pedal was"
                    + " untouched then this simulator reports the car's own clutch on"
                    + " this channel.";
            }
            return caution;
        }

        /// <summary>
        /// Whether a throttle reading can be attributed to the driver's pedal.
        ///
        /// RaceRoom reads 24% with the car stopped and nobody touching anything,
        /// so on that channel a spike is engine or idle state and says nothing
        /// about a blip. Where the drive never saw the car at rest it cannot
        /// disqualify anything, and the reading is taken at face value as it
        /// always was.
        /// </summary>
        private bool ThrottleChannelFollowsPedal()
        {
            return !_restingThrottleSeen || _restingThrottle <= 5.0;
        }

        /// <summary>
        /// What the throttle channel read before anyone touched anything.
        ///
        /// A detected spike means the car blipped only if this channel follows
        /// the pedal. Some simulators publish engine or vehicle state here, the
        /// way RaceRoom's clutch channel reads fully depressed at rest, and on
        /// such a channel every car appears to blip. Reporting the resting value
        /// beside the peak lets a reviewer tell those apart without driving the
        /// car again, and without knowing in advance which simulators do it.
        /// </summary>
        private string RestingThrottleSummary()
        {
            if (!_restingThrottleSeen)
            {
                return string.Empty;
            }
            if (_restingThrottle > 5.0)
            {
                return " The throttle already read "
                    + Math.Round(_restingThrottle)
                    + "% with the car stopped before any test began, so this channel is not"
                    + " reporting the pedal alone and the spike is not evidence that the car"
                    + " blipped.";
            }
            return " The throttle read "
                + Math.Round(_restingThrottle)
                + "% with the car stopped, so this channel does follow the pedal: the spike"
                + " was either the car's own blip or the driver's foot.";
        }

        /// <summary>
        /// Why the automatic-cut test could not answer.
        ///
        /// It read torque, not throttle: an automatic cut on a sequential
        /// gearbox is ignition-side, so the throttle plate stays open and the
        /// throttle channel never shows it. That makes an absent torque channel
        /// indistinguishable from a car that does not cut, unless the draft says
        /// which happened - and only one of the two is worth re-driving for.
        /// </summary>
        private string CutEvidenceSummary()
        {
            if (_upshiftMaximumTorque <= 0.0)
            {
                return "This simulator published no engine torque during the shift, and the"
                    + " test reads torque rather than throttle because the cut is"
                    + " ignition-side. Nothing was measured, so the car may or may not cut;"
                    + " re-driving will not change that without a torque channel.";
            }
            return "Engine torque held at "
                + Math.Round(_upshiftMinimumTorque) + " of "
                + Math.Round(_upshiftMaximumTorque)
                + " through the change while throttle demand stayed high, which is not the"
                + " collapse an automatic cut produces.";
        }

        private void RememberVehicleClutchTelemetry()
        {
            if (!ClutchContradictsAcceptedResult() || !string.IsNullOrEmpty(_results.EvidenceNote))
            {
                return;
            }
            _results.EvidenceNote =
                "Clutch input was detected during a test that was accepted as needing no clutch. "
                + "The telemetry does not separate the pedal from a clutch the car works itself, so "
                + "this result may be measuring the driver. Re-run the test, or confirm the reading "
                + "before relying on it."
                + (_restingClutchSeen && _restingClutch > 20.0
                    ? " The channel already read " + Math.Round(_restingClutch)
                        + "% with the car stopped before any test began; if the pedal was untouched "
                        + "then this simulator reports the car's own clutch here, which would make "
                        + "the clutch-free results correct."
                    : string.Empty);
        }

        /// <summary>
        /// Whether this phase saw enough to conclude anything. A move-off needs
        /// the driver to have asked the car to move; a shift test needs a gear
        /// to have changed, which a refusal into neutral also satisfies.
        /// </summary>
        private bool WasAttempted()
        {
            switch (_phase)
            {
                case Phase.MoveOff:
                    // Being in gear is where a driver waits, not something they
                    // did. Only asking the car to move counts, by throttle or by
                    // a car that creeps away without any.
                    return _maximumThrottle >= 5.0 || _moveOffMovementStartedUtc.HasValue;
                case Phase.GearCount:
                    // With no gear ever seen there is nothing to report, and the
                    // phase used to sit there refusing to conclude or advance.
                    return _maximumGear > 0;
                case Phase.FullThrottleUpshift:
                    // A shift the test would have counted: one taken with the
                    // throttle where the phase asks for it. Any gear change at
                    // all is too loose, because a driver getting up to speed
                    // changes gear on the way, and that recorded a gearbox
                    // needing its clutch on a test nobody ran.
                    return !double.IsNaN(_upshiftThrottleAtChange)
                        && _upshiftThrottleAtChange >= 70.0;
                case Phase.LiftedUpshift:
                    return !double.IsNaN(_upshiftThrottleAtChange)
                        && _upshiftThrottleAtChange <= 45.0;
                case Phase.CoastDownshift:
                case Phase.ManualBlipDownshift:
                    // A lower gear has to have been selected. A refusal into
                    // neutral settles the attempt on its own and never reaches
                    // here.
                    return _downshiftCandidateGear > 0;
                default:
                    return _gearChangeSeen;
            }
        }

        private static string NothingMeasuredMessage(Phase phase)
        {
            if (phase == Phase.GearCount)
            {
                return "Nothing was measured: no gear was ever engaged, so no gear count is recorded. "
                    + "Retry, or answer it in the form.";
            }
            if (phase == Phase.MoveOff)
            {
                return "Nothing was measured: the car was never asked to pull away. This is left "
                    + "unanswered rather than recorded as needing a clutch. Retry, or answer it in "
                    + "the form.";
            }
            return "Nothing was measured: no gear change was seen during this test. This is left "
                + "unanswered rather than recorded as a gearbox that refused. Retry, or answer it "
                + "in the form.";
        }

        private void AdvanceAfterSkip()
        {
            switch (_phase)
            {
                case Phase.MoveOff: MoveTo(Phase.GearCount); break;
                case Phase.GearCount: MoveTo(Phase.FullThrottleUpshift); break;
                case Phase.FullThrottleUpshift: MoveTo(Phase.LiftedUpshift); break;
                case Phase.LiftedUpshift: MoveTo(Phase.CoastDownshift); break;
                case Phase.CoastDownshift: MoveTo(Phase.ManualBlipDownshift); break;
                case Phase.ManualBlipDownshift: MoveTo(Phase.Complete); break;
            }
        }

        private void MoveTo(Phase phase)
        {
            _phase = phase;
            if (phase == Phase.Complete)
            {
                _hasCompletedResults = true;
            }
            ResetTrace();
        }

        private static double DriveRatio(GuidedTelemetrySample sample)
        {
            return sample.Rpm / Math.Max(sample.SpeedKmh, 1.0);
        }

        private void ResetTrace()
        {
            _baselineGear = 0;
            _downshiftCandidateGear = 0;
            _downshiftCandidateAtUtc = DateTime.MinValue;
            _neutralWhileMovingSinceUtc = null;
            _baselineDriveRatio = 0.0;
            _maximumGear = 0;
            _armed = false;
            _gearChangeSeen = false;
            _previousGear = int.MinValue;
            _attemptNotTested = false;
            _upshiftThrottleAtChange = double.NaN;
            _attemptAccepted = false;
            _automaticActionObserved = false;
            _engineWasRunning = false;
            _moveOffMovementStartedUtc = null;
            _moveOffRefusalStartedUtc = null;
            _resultReady = false;
            _result = string.Empty;
            _maximumClutch = 0.0;
            _minimumThrottle = 100.0;
            _maximumThrottle = 0.0;
            _downshiftArmedThrottle = 0.0;
            _downshiftThrottleReturned = false;
            _maximumTorque = 0.0;
            _minimumTorque = double.MaxValue;
            _upshiftMaximumTorque = 0.0;
            _upshiftMinimumTorque = double.MaxValue;
            _upshiftMaximumThrottle = 0.0;
            _upshiftMinimumThrottle = 100.0;
            _upshiftGearChangedUtc = null;
        }

        private static bool IsTestPhase(Phase phase)
        {
            return phase >= Phase.MoveOff && phase <= Phase.ManualBlipDownshift;
        }

        private static int StepNumber(Phase phase)
        {
            if (phase >= Phase.MoveOff && phase <= Phase.ManualBlipDownshift)
            {
                return ((int)phase) - ((int)Phase.MoveOff) + 1;
            }
            return phase == Phase.Complete ? 6 : 0;
        }

        private string Status(Phase phase)
        {
            if (phase == Phase.Complete)
            {
                return "Drive complete - return to SimHub to review cockpit details and save the draft.";
            }
            if (phase == Phase.Intro)
            {
                return "Press Next to begin the first maneuver.";
            }
            if (_resultReady)
            {
                return "Result ready - Next accepts it; Retry repeats this test.";
            }
            return "Perform the maneuver. Press Next when finished if no result is detected automatically.";
        }

        private static string Title(Phase phase)
        {
            switch (phase)
            {
                case Phase.Intro: return "Before you begin";
                case Phase.MoveOff: return "Move-off clutch test";
                case Phase.GearCount: return "Forward gears";
                case Phase.FullThrottleUpshift: return "Full-throttle upshift";
                case Phase.LiftedUpshift: return "Lifted-throttle upshift";
                case Phase.CoastDownshift: return "Downshift without pedal input";
                case Phase.ManualBlipDownshift: return "Manual-blip downshift";
                case Phase.Complete: return "Guided drive complete";
                default: return "Guided verification";
            }
        }

        private static string Prompt(Phase phase)
        {
            string line1 = PromptLine1(phase);
            string line2 = PromptLine2(phase);
            return string.IsNullOrEmpty(line2) ? line1 : line1 + " " + line2;
        }

        private static string PromptLine1(Phase phase)
        {
            switch (phase)
            {
                case Phase.Intro: return "Prepare, perform the maneuver, then wait for CAPTURED.";
                // The clutch may be used to engage first. The question is only
                // whether the car can pull away once it is released, and asking
                // for the gear without the clutch made the driver grind a
                // manual gearbox to destruction, which also ended the drive.
                // Stalling is how such a car answers, so the prompt says so
                // rather than reading as an instruction that failed.
                //
                // The brake is what makes the answer unambiguous. Released
                // gently against a free car, a manual clutch can be slipped
                // into a creep instead of a stall, which would read as moving
                // off without one. Held against the brake there is nowhere for
                // that creep to go, so the engine either stalls or it does not.
                case Phase.MoveOff: return "Stopped in 1st, brake on. Release the clutch fully.";
                case Phase.GearCount: return "Shift up until the gearbox will not go higher.";
                case Phase.FullThrottleUpshift: return "While moving, keep throttle above 70%.";
                case Phase.LiftedUpshift: return "Leave the clutch untouched and lift the throttle.";
                case Phase.CoastDownshift: return "At safe RPM, release the throttle, then downshift. Stay off the throttle until the result appears, and leave the clutch untouched.";
                case Phase.ManualBlipDownshift: return "Leave clutch untouched and manually blip the throttle.";
                case Phase.Complete: return "Driving results are ready for review.";
                default: return string.Empty;
            }
        }

        private static string PromptLine2(Phase phase)
        {
            switch (phase)
            {
                case Phase.Intro: return "Next accepts; use Retry or Skip when needed.";
                case Phase.MoveOff: return "Stall = clutch required. If not, brake off, throttle.";
                case Phase.GearCount: return "Then press NEXT. Only you can see the top gear.";
                case Phase.FullThrottleUpshift: return "Leave clutch untouched and request one upshift.";
                case Phase.LiftedUpshift: return "Then request one upshift.";
                case Phase.CoastDownshift: return "Then request one downshift.";
                case Phase.ManualBlipDownshift: return "Then request one downshift.";
                case Phase.Complete: return "Press Next to close this overlay.";
                default: return string.Empty;
            }
        }

        private string ResultSummary(Phase phase)
        {
            if (!_resultReady)
            {
                return string.Empty;
            }
            switch (phase)
            {
                case Phase.MoveOff:
                    return _attemptAccepted
                        ? "Moved off without the clutch"
                        : "No movement without the clutch; this car needs it";
                case Phase.GearCount:
                    return _maximumGear > 0
                        ? "Forward gears recorded: " + _maximumGear
                        : "No forward gears recorded";
                case Phase.FullThrottleUpshift:
                    return _attemptAccepted
                        ? "Full-throttle upshift detected"
                        : "No full-throttle upshift detected";
                case Phase.LiftedUpshift:
                    return _attemptAccepted
                        ? "Lifted-throttle upshift detected"
                        : "No lifted-throttle upshift detected";
                case Phase.CoastDownshift:
                    if (!_attemptAccepted) return "No clutchless downshift detected";
                    return _automaticActionObserved
                        ? "Downshift and automatic blip detected"
                        : "Downshift detected; no automatic blip";
                case Phase.ManualBlipDownshift:
                    return _attemptAccepted
                        ? "Manual-blip downshift detected"
                        : "No manual-blip downshift detected";
                default:
                    return string.Empty;
            }
        }

        private static string LiveValues(GuidedTelemetrySample sample)
        {
            if (sample == null)
            {
                return "Waiting for live telemetry";
            }
            return "Gear " + (sample.Gear == 0 ? "N" : sample.Gear.ToString())
                + "  |  Vehicle clutch " + Math.Round(sample.Clutch) + "%"
                + "  |  Throttle " + Math.Round(sample.Throttle) + "%"
                + "  |  " + Math.Round(sample.SpeedKmh) + " km/h";
        }
    }
}
