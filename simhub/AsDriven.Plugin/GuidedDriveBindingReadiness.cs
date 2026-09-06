using System;
using System.Collections.Generic;
using System.Linq;

namespace AsDriven.Plugin
{
    /// <summary>
    /// Tracks a deliberate, per-session check of the controls used to progress
    /// a guided drive. SimHub does not expose its stored binding configuration
    /// to plugins, but it does report the input that invoked an action. Asking
    /// the contributor to press each control is therefore an honest readiness
    /// check instead of a guess based on registered action names.
    /// </summary>
    internal sealed class GuidedDriveBindingReadiness
    {
        internal static readonly string[] RequiredActions = new[]
        {
            "VerificationDriveNext",
            "VerificationDriveRetry",
            "VerificationDriveSkip",
            "VerificationDriveCancel",
        };

        private readonly object _lock = new object();
        private readonly Dictionary<string, string> _detectedInputs =
            new Dictionary<string, string>(StringComparer.Ordinal);
        private bool _checking;

        internal void Restore(IDictionary<string, string> detectedInputs)
        {
            lock (_lock)
            {
                _detectedInputs.Clear();
                if (detectedInputs != null)
                {
                    foreach (KeyValuePair<string, string> entry in detectedInputs)
                    {
                        if (RequiredActions.Contains(entry.Key)
                            && !string.IsNullOrWhiteSpace(entry.Value))
                        {
                            _detectedInputs[entry.Key] = entry.Value;
                        }
                    }
                }
            }
        }

        internal void Start()
        {
            lock (_lock)
            {
                _checking = true;
            }
        }

        internal string Observe(string input, string action)
        {
            if (string.IsNullOrWhiteSpace(input))
            {
                return null;
            }
            string requiredAction = RequiredActions.FirstOrDefault(
                candidate => IsAction(action, candidate));
            if (requiredAction == null)
            {
                return null;
            }
            lock (_lock)
            {
                if (_checking)
                {
                    _detectedInputs[requiredAction] = input;
                    return requiredAction;
                }
            }
            return null;
        }

        internal GuidedDriveBindingReadinessSnapshot GetSnapshot()
        {
            lock (_lock)
            {
                return new GuidedDriveBindingReadinessSnapshot(
                    _checking,
                    RequiredActions.Where(action => !_detectedInputs.ContainsKey(action)).ToArray(),
                    new Dictionary<string, string>(_detectedInputs, StringComparer.Ordinal));
            }
        }

        private static bool IsAction(string action, string requiredAction)
        {
            return string.Equals(action, requiredAction, StringComparison.Ordinal)
                || (!string.IsNullOrWhiteSpace(action)
                    && action.EndsWith("." + requiredAction, StringComparison.Ordinal));
        }
    }

    internal sealed class GuidedDriveBindingReadinessSnapshot
    {
        private readonly Dictionary<string, string> _detectedInputs;

        internal GuidedDriveBindingReadinessSnapshot(
            bool checking, string[] missingActions, Dictionary<string, string> detectedInputs)
        {
            Checking = checking;
            MissingActions = missingActions ?? new string[0];
            _detectedInputs = detectedInputs ?? new Dictionary<string, string>(StringComparer.Ordinal);
        }

        internal bool Checking { get; private set; }
        internal string[] MissingActions { get; private set; }
        internal bool IsReady { get { return Checking && MissingActions.Length == 0; } }

        internal string HintFor(string action)
        {
            string input;
            return _detectedInputs.TryGetValue(action ?? string.Empty, out input)
                ? DisplayInputName(input)
                : "UNBOUND";
        }

        private static string DisplayInputName(string input)
        {
            if (string.IsNullOrWhiteSpace(input))
            {
                return "UNBOUND";
            }

            // SimHub reports the action provider before the actual control,
            // such as ``JoystickPlugin.Button_3``. The provider is implementation
            // detail and makes the compact driving overlay needlessly noisy.
            int separator = input.LastIndexOf('.');
            return separator >= 0 && separator + 1 < input.Length
                ? input.Substring(separator + 1)
                : input;
        }
    }
}
