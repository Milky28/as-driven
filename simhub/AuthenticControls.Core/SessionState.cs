namespace AuthenticControls.Core
{
    public sealed class SessionState
    {
        private readonly AuthenticControlsDatabase _database;
        private string _lastIdentityKey;
        private int _popupRevision;

        public SessionState(AuthenticControlsDatabase database)
        {
            _database = database;
            Current = GuidanceSnapshot.Empty(
                "no-data", string.Empty, string.Empty, database.DatasetVersion);
        }

        public GuidanceSnapshot Current { get; private set; }

        public bool Update(bool gameRunning, string gameName, string carIdentifier)
        {
            string identityKey = (gameRunning ? "1" : "0") + "\u001f"
                + (gameName ?? string.Empty) + "\u001f" + (carIdentifier ?? string.Empty);
            if (identityKey == _lastIdentityKey)
            {
                return false;
            }
            _lastIdentityKey = identityKey;

            if (!gameRunning)
            {
                Current = GuidanceSnapshot.Empty(
                    "game-not-running", gameName, carIdentifier, _database.DatasetVersion)
                    .WithPopupRevision(_popupRevision);
                return true;
            }

            GuidanceSnapshot next = _database.Match(gameName, carIdentifier);
            if (next.HasMatch)
            {
                _popupRevision++;
            }
            Current = next.WithPopupRevision(_popupRevision);
            return true;
        }
    }
}
