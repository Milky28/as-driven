using System;

namespace AuthenticControls.Core
{
    public sealed class GuidedTelemetrySample
    {
        public DateTime TimestampUtc { get; set; }
        public int Gear { get; set; }
        public double Clutch { get; set; }
        public double Throttle { get; set; }
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
        private int _maximumGear;
        private bool _armed;
        private bool _attemptAccepted;
        private bool _automaticActionObserved;
        private bool _resultReady;
        private bool _hasCompletedResults;
        private bool _fullThrottleTestFailed;
        private bool _coastDownshiftTestFailed;
        private bool _engineWasRunning;
        private DateTime? _moveOffMovementStartedUtc;
        private string _result = string.Empty;
        private double _maximumClutch;
        private double _minimumThrottle;
        private double _maximumThrottle;
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
                            _result = "Highest observed forward gear: " + _maximumGear + ".";
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
                    }
                    break;
                case Phase.GearCount:
                    if (_suggestedGears.HasValue && _maximumGear >= _suggestedGears.Value)
                    {
                        _attemptAccepted = true;
                        _resultReady = true;
                        _result = "Observed all " + _maximumGear + " suggested forward gears.";
                    }
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
            if (sample.Gear <= _baselineGear)
            {
                return;
            }
            bool liftObserved = _upshiftMinimumThrottle <= 45.0;
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
            bool briefThrottleInterruption = !requireLift
                && _upshiftMaximumThrottle >= 70.0
                && _upshiftMinimumThrottle <= 45.0
                && sample.Throttle >= 70.0
                && sample.TimestampUtc - _upshiftGearChangedUtc.Value
                    <= TimeSpan.FromMilliseconds(350.0);
            if (!requireLift
                && !torqueCut
                && _upshiftMinimumThrottle <= 45.0
                && sample.Throttle < 70.0
                && sample.TimestampUtc - _upshiftGearChangedUtc.Value
                    < TimeSpan.FromMilliseconds(350.0))
            {
                return;
            }
            bool automaticCut = torqueCut || briefThrottleInterruption;
            string message = requireLift
                ? "Clutchless upshift accepted after a throttle lift."
                : "Full-throttle clutchless upshift accepted. "
                    + (automaticCut
                        ? (briefThrottleInterruption
                            ? "A brief throttle interruption recovered immediately around the gear change."
                            : "A shift-local torque interruption was detected while throttle demand stayed high.")
                        : "Automatic cut could not be established confidently from this trace.")
                    + VehicleClutchSummary();
            SetResult(true, automaticCut, message);
        }

        private void DetectDownshift(GuidedTelemetrySample sample, bool manualBlip)
        {
            if (!_armed && sample.Gear > 1 && sample.SpeedKmh > 5.0
                && (!manualBlip ? sample.Throttle <= 10.0 : true))
            {
                _armed = true;
                _baselineGear = sample.Gear;
            }
            if (!_armed || sample.Gear <= 0 || sample.Gear >= _baselineGear)
            {
                return;
            }
            bool blip = _maximumThrottle >= 15.0;
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
                        + (blip ? "A throttle spike was detected." : "No automatic throttle spike was detected.")
                        + VehicleClutchSummary());
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
                        _results.AutomaticCut = _automaticActionObserved ? "yes" : "unknown";
                        _results.AutomaticCutMethod = _result;
                        MoveTo(Phase.CoastDownshift);
                    }
                    else
                    {
                        _fullThrottleTestFailed = true;
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
                        _results.AutomaticBlip = _automaticActionObserved ? "yes" : "no";
                        _results.AutomaticBlipMethod = _result;
                        MoveTo(Phase.Complete);
                    }
                    else
                    {
                        _coastDownshiftTestFailed = true;
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

        private string VehicleClutchSummary()
        {
            return _maximumClutch > 20.0
                ? " Vehicle clutch telemetry also actuated; it is treated as internal/automatic clutch state, not proof of pedal use."
                : string.Empty;
        }

        private void RememberVehicleClutchTelemetry()
        {
            if (_maximumClutch <= 20.0 || !string.IsNullOrEmpty(_results.EvidenceNote))
            {
                return;
            }
            _results.EvidenceNote =
                "Vehicle-reported clutch telemetry actuated during the guided drive even though the test instructions required no physical clutch input; treated as internal/automatic clutch state rather than proof of pedal use.";
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

        private void ResetTrace()
        {
            _baselineGear = 0;
            _maximumGear = 0;
            _armed = false;
            _attemptAccepted = false;
            _automaticActionObserved = false;
            _engineWasRunning = false;
            _moveOffMovementStartedUtc = null;
            _resultReady = false;
            _result = string.Empty;
            _maximumClutch = 0.0;
            _minimumThrottle = 100.0;
            _maximumThrottle = 0.0;
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
                case Phase.MoveOff: return "Engine on. Stop, select first, leave the clutch untouched.";
                case Phase.GearCount: return "Cycle through every forward gear.";
                case Phase.FullThrottleUpshift: return "While moving, keep throttle above 70%.";
                case Phase.LiftedUpshift: return "Leave the clutch untouched and lift the throttle.";
                case Phase.CoastDownshift: return "At safe RPM, release throttle and leave clutch untouched.";
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
                case Phase.MoveOff: return "Apply light throttle; keep moving briefly.";
                case Phase.GearCount: return "Direct H-pattern selection is reviewed in the form.";
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
                    return _attemptAccepted ? "Movement detected" : "No movement detected";
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
