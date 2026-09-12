import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == "nt", "Windows PowerShell installer")
class InstallerErrorTests(unittest.TestCase):
    def test_failure_is_visible_logged_and_still_fails(self):
        script = Path(__file__).parents[1] / "simhub" / "install.ps1"
        with tempfile.TemporaryDirectory(prefix="AsDriven error test ") as folder:
            for interactive in (False, True):
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                     "-File", str(script), "-PackagePath", str(Path(folder) / "missing"),
                     *(["-Interactive"] if interactive else [])],
                    input="\n", capture_output=True, text=True, timeout=30,
                    env={**os.environ, "TEMP": folder, "TMP": folder},
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("The built As Driven package was not found",
                              result.stdout + result.stderr)
                logs = list(Path(folder).glob("AsDriven-install-error-*.txt"))
                if interactive:
                    self.assertIn("Press Enter to close", result.stdout)
                    self.assertEqual(len(logs), 1)
                    self.assertIn("The built As Driven package was not found",
                                  logs[0].read_text(encoding="utf-8-sig"))
                else:
                    self.assertNotIn("Press Enter to close", result.stdout)
                    self.assertEqual(logs, [])
