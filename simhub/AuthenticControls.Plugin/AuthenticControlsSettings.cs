namespace AuthenticControls.Plugin
{
    public sealed class AuthenticControlsSettings
    {
        public double PopupDurationSeconds { get; set; }
        public string PopupSize { get; set; }
        public string VerificationObserver { get; set; }

        public AuthenticControlsSettings()
        {
            PopupDurationSeconds = 10.0;
            PopupSize = "compact";
            VerificationObserver = string.Empty;
        }
    }
}
