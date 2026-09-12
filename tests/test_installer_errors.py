import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == "nt", "Windows PowerShell installer")
class InstallerErrorTests(unittest.TestCase):
    def test_folder_selection_validation_and_cancellation(self):
        script = Path(__file__).parents[1] / "simhub" / "install.ps1"
        for scenario in ("select", "cancel", "existing", "noninteractive"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                package = root / "package"
                package.mkdir()
                for name in ("AsDriven.Plugin.dll", "AsDriven.Core.dll"):
                    (package / name).write_text("test binary")
                for name in ("PluginsData", "DashTemplates", "OverlayLayouts"):
                    (package / name).mkdir()
                target = root / "Custom SimHub"
                target.mkdir()
                (target / "SimHubWPF.exe").touch()
                invalid = root / "wrong folder"
                invalid.mkdir()
                # A directory named like the executable must not pass validation.
                (invalid / "SimHubWPF.exe").mkdir()
                harness = root / "test.ps1"
                harness.write_text(r'''
$dialog = [pscustomobject]@{ Description = ''; ShowNewFolderButton = $true; SelectedPath = ''; Calls = 0 }
$dialog | Add-Member ScriptMethod ShowDialog {
    $this.Calls++
    if ($this.Calls -gt 2) { throw 'Unexpected extra folder prompt' }
    if ($this.Calls -eq 1) { $this.SelectedPath = $env:TEST_INVALID; return 1 }
    if ($env:TEST_SCENARIO -eq 'cancel') { return 2 }
    $this.SelectedPath = $env:TEST_TARGET
    return 1
}
$dialog | Add-Member ScriptMethod Dispose {}
function New-Object {
    param($TypeName)
    if ($TypeName -eq 'System.Windows.Forms.FolderBrowserDialog') {
        if ($env:TEST_SCENARIO -in @('existing', 'noninteractive')) { throw 'Unexpected folder picker' }
        return $dialog
    }
    Microsoft.PowerShell.Utility\New-Object $TypeName @args
}
$initial = $env:TEST_INVALID
if ($env:TEST_SCENARIO -eq 'existing') { $initial = $env:TEST_TARGET }
$global:LASTEXITCODE = 0
& $env:TEST_INSTALLER -PackagePath $env:TEST_PACKAGE -SimHubInstallPath $initial -Interactive:($env:TEST_SCENARIO -ne 'noninteractive')
exit $LASTEXITCODE
''', encoding="utf-8")
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File", str(harness)],
                    input="\n", capture_output=True, text=True, timeout=30,
                    env={**os.environ, "TEMP": folder, "TMP": folder,
                         "TEST_INSTALLER": str(script), "TEST_PACKAGE": str(package),
                         "TEST_INVALID": str(invalid), "TEST_TARGET": str(target),
                         "TEST_SCENARIO": scenario},
                )
                installed = target / "AsDriven.Plugin.dll"
                if scenario in ("select", "existing"):
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(installed.read_text(), "test binary")
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(installed.exists())
                self.assertFalse((invalid / "AsDriven.Plugin.dll").exists())

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
