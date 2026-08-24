from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from as_driven_db.maintainer_workbench import (
    WorkbenchApplication,
    WorkbenchError,
    create_workbench_server,
    workbench_page,
)


class _FakeApplication:
    def __init__(self) -> None:
        self.synced = 0
        self.refreshed = 0

    def snapshot(self) -> dict:
        return {
            "repository": "example/project",
            "label": "observation-received",
            "repository_status": {
                "dataset_version": "1.2.3",
                "records": 2,
                "tracked_changes": False,
                "ahead_of_upstream": 0,
                "branch": "test",
            },
            "counts": {},
            "cases": [],
        }

    def sync(self) -> dict:
        self.synced += 1
        return {"processed": 0, "skipped": 0, "error": 0}

    def refresh_local_queue(self) -> dict:
        self.refreshed += 1
        return {
            "research_results": {"found": 1, "imported": [{"issue": 4}], "errors": []},
            "snapshot": self.snapshot(),
        }


class MaintainerWorkbenchTests(unittest.TestCase):
    def test_page_names_the_review_boundary_and_approval_gates(self) -> None:
        page = workbench_page("test-token")
        self.assertIn("Maintainer Workbench", page)
        self.assertIn("Nothing promotes or publishes merely because it appears here", page)
        self.assertIn("Approve and promote", page)
        self.assertIn("Publish response and close issue", page)
        self.assertIn("Promotion complete, publication pending", page)
        self.assertIn("actions.has('publish-result')&&!publicationBlocked", page)
        self.assertIn("Formatted review", page)
        self.assertIn("formatResearchResult", page)
        self.assertIn("[hidden]{display:none!important}", page)
        self.assertIn("data-filter", page)
        self.assertIn("['promoted','Promoted'", page)
        self.assertIn("queueFilter==='promoted'", page)
        self.assertIn('id="progress"', page)
        self.assertIn("Regenerating release outputs, validating the dataset", page)
        self.assertIn("beginProgress(button,'Finalizing release", page)
        self.assertIn("beginProgress(button,'Syncing...'", page)
        self.assertIn("Complete: dataset ${r.dataset_version} finalized", page)
        self.assertIn("Finalization failed: ${e.message}", page)
        self.assertIn("endProgress(button,outcome,failed)", page)
        self.assertIn(
            "if(action==='generate-research-brief')await loadArtifact('research_brief')",
            page,
        )
        self.assertIn("state-final-review", page)
        self.assertIn("state-identity-research", page)
        self.assertIn('const token="test-token"', page)

    def test_sync_requests_are_serialized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            application = WorkbenchApplication(Path(directory))
            first_entered = threading.Event()
            release_first = threading.Event()
            second_entered = threading.Event()
            calls_lock = threading.Lock()
            calls = 0

            def fake_sync(*_args, **_kwargs) -> dict:
                nonlocal calls
                with calls_lock:
                    calls += 1
                    call_number = calls
                if call_number == 1:
                    first_entered.set()
                    self.assertTrue(release_first.wait(timeout=5))
                else:
                    second_entered.set()
                return {"processed": 0, "skipped": 0, "error": 0}

            with patch(
                "as_driven_db.maintainer_workbench.sync_submissions",
                side_effect=fake_sync,
            ):
                first = threading.Thread(target=application.sync)
                second = threading.Thread(target=application.sync)
                first.start()
                self.assertTrue(first_entered.wait(timeout=5))
                second.start()
                self.assertFalse(second_entered.wait(timeout=0.2))
                release_first.set()
                first.join(timeout=5)
                second.join(timeout=5)

            self.assertFalse(first.is_alive())
            self.assertFalse(second.is_alive())
            self.assertTrue(second_entered.is_set())
            self.assertEqual(2, calls)

    def test_server_is_loopback_only_and_post_requests_require_its_token(self) -> None:
        with self.assertRaisesRegex(WorkbenchError, "loopback"):
            create_workbench_server(_FakeApplication(), host="0.0.0.0", port=0)

        application = _FakeApplication()
        server = create_workbench_server(application, port=0)
        with self.assertRaisesRegex(WorkbenchError, "already be running"):
            duplicate_server = create_workbench_server(
                _FakeApplication(), port=server.server_address[1]
            )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            page = urlopen(base + "/", timeout=5).read().decode("utf-8")
            token = re.search(r'const token="([^"]+)"', page).group(1)
            snapshot = json.loads(
                urlopen(base + "/api/snapshot", timeout=5).read().decode("utf-8")
            )
            self.assertEqual("1.2.3", snapshot["repository_status"]["dataset_version"])

            unauthorized = Request(
                base + "/api/actions/sync",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as refused:
                urlopen(unauthorized, timeout=5)
            self.assertEqual(403, refused.exception.code)
            refused.exception.close()

            authorized = Request(
                base + "/api/actions/sync",
                data=b"{}",
                headers={
                    "Content-Type": "application/json",
                    "X-As-Driven-Token": token,
                },
                method="POST",
            )
            result = json.loads(urlopen(authorized, timeout=5).read().decode("utf-8"))
            self.assertEqual(0, result["processed"])
            self.assertEqual(1, application.synced)

            refresh = Request(
                base + "/api/actions/refresh",
                data=b"{}",
                headers={
                    "Content-Type": "application/json",
                    "X-As-Driven-Token": token,
                },
                method="POST",
            )
            refreshed = json.loads(urlopen(refresh, timeout=5).read().decode("utf-8"))
            self.assertEqual(1, refreshed["research_results"]["found"])
            self.assertEqual(1, application.refreshed)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_artifacts_cannot_escape_the_case_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data" / "v1").mkdir(parents=True)
            (root / "data" / "v1" / "index.json").write_text(
                json.dumps({"dataset_version": "1.0.0", "records": []}),
                encoding="utf-8",
            )
            case_dir = root / "build" / "review-cases" / "issue-7"
            case_dir.mkdir(parents=True)
            (root / "build" / "review-cases" / "secret.json").write_text(
                "{}", encoding="utf-8"
            )
            case = {
                "state": "duplicate",
                "classification": "exact-resubmission",
                "issue": {"number": 7, "title": "test"},
                "observation": {"identity": {"telemetry_name": "test"}},
                "research": {"status": "not-required"},
                "artifacts": {"bad": "../secret.json"},
                "github_feedback": {"status": "published"},
            }
            (case_dir / "case.json").write_text(json.dumps(case), encoding="utf-8")
            application = WorkbenchApplication(root)
            self.assertEqual([], application.case_detail(7)["artifacts"])
            with self.assertRaisesRegex(WorkbenchError, "escapes"):
                application.artifact(7, "bad")


if __name__ == "__main__":
    unittest.main()
