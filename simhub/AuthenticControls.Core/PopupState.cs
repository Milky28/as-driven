using System;

namespace AuthenticControls.Core
{
    public sealed class PopupState
    {
        private readonly object _sync = new object();
        private TimeSpan _automaticDuration;
        private DateTime _automaticVisibleUntilUtc;
        private bool _manuallyVisible;

        public PopupState(TimeSpan automaticDuration)
        {
            if (automaticDuration < TimeSpan.Zero)
            {
                throw new ArgumentOutOfRangeException("automaticDuration");
            }
            _automaticDuration = automaticDuration;
        }

        public double AutomaticDurationSeconds
        {
            get
            {
                lock (_sync)
                {
                    return _automaticDuration.TotalSeconds;
                }
            }
        }

        public void SetAutomaticDuration(TimeSpan automaticDuration)
        {
            if (automaticDuration < TimeSpan.Zero)
            {
                throw new ArgumentOutOfRangeException("automaticDuration");
            }
            lock (_sync)
            {
                _automaticDuration = automaticDuration;
            }
        }

        public void OnIdentityChanged(
            bool gameRunning,
            string carIdentifier,
            DateTime utcNow)
        {
            lock (_sync)
            {
                _manuallyVisible = false;
                _automaticVisibleUntilUtc = gameRunning
                    && !string.IsNullOrWhiteSpace(carIdentifier)
                    ? utcNow.Add(_automaticDuration)
                    : DateTime.MinValue;
            }
        }

        public void Show()
        {
            lock (_sync)
            {
                _manuallyVisible = true;
            }
        }

        public void Hide()
        {
            lock (_sync)
            {
                _manuallyVisible = false;
                _automaticVisibleUntilUtc = DateTime.MinValue;
            }
        }

        public void Toggle(DateTime utcNow)
        {
            lock (_sync)
            {
                if (_manuallyVisible || utcNow < _automaticVisibleUntilUtc)
                {
                    _manuallyVisible = false;
                    _automaticVisibleUntilUtc = DateTime.MinValue;
                }
                else
                {
                    _manuallyVisible = true;
                }
            }
        }

        public bool IsVisible(DateTime utcNow)
        {
            lock (_sync)
            {
                return _manuallyVisible || utcNow < _automaticVisibleUntilUtc;
            }
        }
    }
}
