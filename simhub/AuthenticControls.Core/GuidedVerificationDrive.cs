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
        public int StepNumber { get; set; }
        public int StepCount { get; set; }
        public string Title { get; set; }
        public string Prompt { get; set; }
        public string Status { get; set; }
        public string Result { get; set; }
        public string LiveValues { get; set; }
    }

    public sealed class GuidedVerificationDrive
    {
        private enum Phase
        {
            Idle,
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
        private int _previousPositiveGear;
        private bool _directJumpObserved;
        private bool _armed;
        private bool _attemptAccepted;
        private bool _automaticActionObserved;
        private bool _resultReady;
        private bool _hasCompletedResults;
        private bool _fullThrottleTestFailed;
        private bool _coastDownshiftTestFailed;
        private bool _engineWasRunning;
        private string _result = string.Empty;
        private double _maximumClutch;
        private double _minimumThrottle;
        private double _maximumThrottle;
        private double _maximumTorque;
        private double _minimumTorque;

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
                            _result = "Highest observed forward gear: " + _maximumGear
                                + (_directJumpObserved ? ". Direct non-adjacent selection was observed." : ".");
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
                    StepNumber = step,
                    StepCount = 6,
                    Title = Title(_phase),
                    Prompt = Prompt(_phase),
                    Status = Status(_phase),
                    Result = _result,
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
                if (_previousPositiveGear > 0
                    && Math.Abs(sample.Gear - _previousPositiveGear) > 1)
                {
                    _directJumpObserved = true;
                }
                _previousPositiveGear = sample.Gear;
            }
        }

        private void DetectResult(GuidedTelemetrySample sample)
        {
            switch (_phase)
            {
                case Phase.MoveOff:
                    if (sample.EngineStarted && sample.Rpm >= 200.0)
                    {
                        _engineWasRunning = true;
                    }
                    if (!_armed && _engineWasRunning && sample.SpeedKmh < 1.0)
                    {
                        _armed = true;
                    }
                    if (_armed && sample.Gear > 0 && sample.SpeedKmh >= 2.0)
                    {
                        SetResult(
                            true,
                            false,
                            "The car moved from rest while the test required no physical clutch input."
                                + VehicleClutchSummary());
                    }
                    else if (_armed && _engineWasRunning
                        && (!sample.EngineStarted || sample.Rpm < 200.0))
                    {
                        SetResult(false, false, "The engine stopped before the car moved; standing-start clutch is required.");
                    }
                    break;
                case Phase.GearCount:
                    if (_suggestedGears.HasValue && _maximumGear >= _suggestedGears.Value)
                    {
                        _attemptAccepted = true;
                        _resultReady = true;
                        _result = "Observed all " + _maximumGear + " suggested forward gears"
                            + (_directJumpObserved ? " and a direct non-adjacent gear selection." : ".");
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
            }
            if (!_armed || sample.Gear <= _baselineGear)
            {
                return;
            }
            bool liftObserved = _minimumThrottle <= 45.0;
            if (requireLift && !liftObserved)
            {
                return;
            }
            bool torqueCut = !requireLift
                && _maximumThrottle >= 70.0
                && _minimumThrottle >= 60.0
                && _maximumTorque > 20.0
                && _minimumTorque <= (_maximumTorque * 0.35);
            string message = requireLift
                ? "Clutchless upshift accepted after a throttle lift."
                : "Full-throttle clutchless upshift accepted. "
                    + (torqueCut
                        ? "A torque interruption was detected while pedal input stayed high."
                        : "Automatic cut could not be established confidently from this trace.")
                    + VehicleClutchSummary();
            SetResult(true, torqueCut, message);
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
                    _results.DirectGearSelection = _directJumpObserved ? "yes" : "not-tested";
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
            _previousPositiveGear = 0;
            _directJumpObserved = false;
            _armed = false;
            _attemptAccepted = false;
            _automaticActionObserved = false;
            _engineWasRunning = false;
            _resultReady = false;
            _result = string.Empty;
            _maximumClutch = 0.0;
            _minimumThrottle = 100.0;
            _maximumThrottle = 0.0;
            _maximumTorque = 0.0;
            _minimumTorque = double.MaxValue;
        }

        private static bool IsTestPhase(Phase phase)
        {
            return phase >= Phase.MoveOff && phase <= Phase.ManualBlipDownshift;
        }

        private static int StepNumber(Phase phase)
        {
            if (phase >= Phase.MoveOff && phase <= Phase.ManualBlipDownshift)
            {
                return ((int)phase);
            }
            return phase == Phase.Complete ? 6 : 0;
        }

        private string Status(Phase phase)
        {
            if (phase == Phase.Complete)
            {
                return "Drive complete - return to SimHub to review cockpit details and save the draft.";
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
            switch (phase)
            {
                case Phase.MoveOff: return "Start the engine, stop completely, select first, do not press the clutch, then apply light throttle.";
                case Phase.GearCount: return "Cycle through every forward gear. For an H-pattern, include a non-adjacent direct selection.";
                case Phase.FullThrottleUpshift: return "While moving, keep the throttle above 70%, do not use the clutch, and request one upshift.";
                case Phase.LiftedUpshift: return "Without using the clutch, lift the throttle and request one upshift.";
                case Phase.CoastDownshift: return "At safe RPM, release the throttle, do not use the clutch, and request one downshift.";
                case Phase.ManualBlipDownshift: return "Without using the clutch, manually blip the throttle while requesting one downshift.";
                case Phase.Complete: return "The driving results are ready. Use Next to close this overlay after reading the summary.";
                default: return string.Empty;
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
