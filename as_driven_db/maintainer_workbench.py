from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import threading
from typing import Any
from urllib.parse import unquote, urlsplit
import webbrowser

from .release_finalize import finalize_release
from .research_handoff import (
    discover_research_results,
    generate_research_briefs,
    import_research_result,
)
from .review_feedback import (
    publication_blockers,
    publication_next_step,
    publish_review_result,
)
from .review_promotion import promote_review_case
from .review_proposal import prepare_review_proposal
from .review_submissions import (
    DEFAULT_LABEL,
    DEFAULT_REPOSITORY,
    list_review_cases,
    sync_submissions,
)


MAX_REQUEST_BYTES = 2_000_000
SAFE_ARTIFACT = re.compile(r"^[a-z0-9][a-z0-9_.-]*$", re.IGNORECASE)


class WorkbenchError(ValueError):
    pass


class LoopbackWorkbenchServer(ThreadingHTTPServer):
    # Windows' SO_REUSEADDR semantics can allow several processes to accept on
    # one port. A maintainer must never be left guessing which local process is
    # receiving approval actions.
    allow_reuse_address = False
    daemon_threads = True


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exception:
        raise WorkbenchError(f"could not read {path.name}: {exception}") from exception
    if not isinstance(payload, dict):
        raise WorkbenchError(f"{path.name} is not a JSON object")
    return payload


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


class WorkbenchApplication:
    """A local-only adapter over the reviewed contribution workflow."""

    def __init__(
        self,
        root: Path,
        *,
        repository: str = DEFAULT_REPOSITORY,
        label: str = DEFAULT_LABEL,
        cases_directory: Path = Path("build") / "review-cases",
        inbox: Path = Path("build") / "observation-intake",
    ) -> None:
        self.root = root.resolve()
        self.repository = repository
        self.label = label
        self.cases_directory = (
            cases_directory.resolve()
            if cases_directory.is_absolute()
            else (self.root / cases_directory).resolve()
        )
        self.inbox = inbox.resolve() if inbox.is_absolute() else (self.root / inbox).resolve()
        self._sync_lock = threading.Lock()

    def _case_path(self, issue: int) -> Path:
        if issue < 1:
            raise WorkbenchError("issue number must be positive")
        return self.cases_directory / f"issue-{issue}" / "case.json"

    def _case(self, issue: int) -> dict[str, Any]:
        path = self._case_path(issue)
        if not path.is_file():
            raise WorkbenchError(f"review case for issue #{issue} does not exist")
        return _read_json(path)

    def repository_status(self) -> dict[str, Any]:
        index = _read_json(self.root / "data" / "v1" / "index.json")
        status = _git(self.root, "status", "--porcelain", "--untracked-files=no")
        ahead = _git(self.root, "rev-list", "--count", "@{upstream}..HEAD")
        branch = _git(self.root, "branch", "--show-current")
        return {
            "dataset_version": index.get("dataset_version"),
            "records": len(index.get("records") or []),
            "tracked_changes": (
                None if status.returncode else bool(status.stdout.strip())
            ),
            "ahead_of_upstream": (
                None
                if ahead.returncode
                else int(ahead.stdout.strip() or "0")
            ),
            "branch": branch.stdout.strip() if not branch.returncode else None,
        }

    def snapshot(self) -> dict[str, Any]:
        cases = list_review_cases(self.cases_directory)
        counts: dict[str, int] = {}
        for case in cases:
            state = str(case.get("display_state") or "unknown")
            counts[state] = counts.get(state, 0) + 1
        return {
            "repository": self.repository,
            "label": self.label,
            "repository_status": self.repository_status(),
            "counts": counts,
            "cases": cases,
        }

    def case_detail(self, issue: int) -> dict[str, Any]:
        case = self._case(issue)
        case_dir = self._case_path(issue).parent
        artifacts: list[dict[str, Any]] = []
        for key, relative in (case.get("artifacts") or {}).items():
            if not isinstance(key, str) or not isinstance(relative, str):
                continue
            path = (case_dir / relative).resolve()
            try:
                path.relative_to(case_dir.resolve())
            except ValueError:
                continue
            artifacts.append(
                {
                    "key": key,
                    "name": path.name,
                    "exists": path.is_file(),
                    "kind": "markdown" if path.suffix.lower() == ".md" else "json",
                }
            )
        summary = next(
            (
                item
                for item in list_review_cases(self.cases_directory)
                if item.get("issue") == issue
            ),
            None,
        )
        blockers: list[str] = []
        if case.get("state") in {"promoted", "released", "duplicate"} and (
            case.get("github_feedback") or {}
        ).get("status") != "published":
            blockers = publication_blockers(self.root, case)
        return {
            "summary": summary,
            "case": case,
            "artifacts": artifacts,
            "publication_blockers": blockers,
            "publication_next_step": publication_next_step(blockers),
        }

    def artifact(self, issue: int, key: str) -> dict[str, Any]:
        if not SAFE_ARTIFACT.fullmatch(key):
            raise WorkbenchError("invalid artifact key")
        case = self._case(issue)
        relative = (case.get("artifacts") or {}).get(key)
        if not isinstance(relative, str):
            raise WorkbenchError(f"case #{issue} has no {key!r} artifact")
        case_dir = self._case_path(issue).parent.resolve()
        path = (case_dir / relative).resolve()
        try:
            path.relative_to(case_dir)
        except ValueError as exception:
            raise WorkbenchError("artifact path escapes its review case") from exception
        if not path.is_file():
            raise WorkbenchError(f"artifact {path.name} does not exist")
        if path.stat().st_size > MAX_REQUEST_BYTES:
            raise WorkbenchError(f"artifact {path.name} is too large to display")
        return {
            "key": key,
            "name": path.name,
            "kind": "markdown" if path.suffix.lower() == ".md" else "json",
            "content": path.read_text(encoding="utf-8-sig"),
        }

    def sync(self) -> dict[str, Any]:
        # The loopback server is threaded, and the workbench may be open in
        # several browser tabs. Serialize synchronization so two requests can
        # never intake the same attachment while its case is still being
        # written.
        with self._sync_lock:
            return sync_submissions(
                self.root,
                repository=self.repository,
                label=self.label,
                cases_directory=self.cases_directory,
                inbox=self.inbox,
            )

    def refresh_local_queue(self) -> dict[str, Any]:
        research_results = discover_research_results(
            self.root,
            self.cases_directory,
        )
        return {
            "research_results": research_results,
            "snapshot": self.snapshot(),
        }

    def perform(self, issue: int, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        allowed = set((self.case_detail(issue)["summary"] or {}).get("allowed_actions") or [])
        if action not in allowed:
            raise WorkbenchError(f"action {action!r} is not available for issue #{issue}")
        if action == "generate-research-brief":
            generated = generate_research_briefs(self.root, self.cases_directory, {issue})
            return {"action": action, "result": generated}
        if action == "import-research":
            result = payload.get("research_result")
            if not isinstance(result, dict):
                raise WorkbenchError("research_result must be a JSON object")
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                dir=self._case_path(issue).parent,
                encoding="utf-8",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                json.dump(result, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            try:
                imported = import_research_result(
                    self.root,
                    self.cases_directory,
                    issue,
                    temporary,
                    replace=payload.get("replace") is True,
                )
            finally:
                temporary.unlink(missing_ok=True)
            return {"action": action, "result": imported}
        if action == "prepare-review":
            prepared = prepare_review_proposal(
                self.root,
                self.cases_directory,
                issue,
                dataset_version=payload.get("dataset_version"),
            )
            return {"action": action, "result": prepared}
        if action == "promote":
            if payload.get("approved") is not True:
                raise WorkbenchError("promotion requires explicit approval")
            promoted = promote_review_case(
                self.root,
                self.cases_directory,
                issue,
                approved=True,
            )
            return {"action": action, "result": promoted}
        if action in {"preview-publication", "publish-result"}:
            approved = action == "publish-result" and payload.get("approved") is True
            if action == "publish-result" and not approved:
                raise WorkbenchError("GitHub publication requires explicit approval")
            published = publish_review_result(
                self.root,
                self.cases_directory,
                issue,
                approved=approved,
            )
            return {"action": action, "result": published}
        raise WorkbenchError(f"unsupported action {action!r}")

    def finalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("run_tests") is not True:
            raise WorkbenchError("release finalization requires the full test gate")
        return finalize_release(self.root, run_tests=True)


WORKBENCH_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>As Driven · Maintainer Workbench</title>
<style>
:root{--bg:#0d1015;--panel:#151a22;--panel2:#1b222c;--line:#2b3440;--text:#f1f5fa;--muted:#9aaac0;--blue:#40c9ff;--amber:#ffb52e;--green:#54d6b0;--red:#ff7272;--shadow:0 18px 50px #0007;font:15px/1.45 Inter,Segoe UI,sans-serif}
*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;background:var(--bg);color:var(--text)}button,input{font:inherit}button{color:inherit;background:var(--panel2);border:1px solid var(--line);padding:.62rem .85rem;border-radius:5px;cursor:pointer}button:hover{border-color:var(--blue)}button:disabled{opacity:.55;cursor:wait}.primary{background:#073f54;border-color:#1685aa}.danger{background:#50230a;border-color:var(--amber)}.ghost{background:transparent}.shell{max-width:1500px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;gap:24px;align-items:flex-start}.eyebrow,.label{font:700 .72rem/1.2 Consolas,monospace;text-transform:uppercase;letter-spacing:.09em;color:var(--muted)}h1{font-size:2rem;margin:.2rem 0}.subtitle{color:var(--muted);max-width:720px}.dataset{border-left:3px solid var(--amber);padding:.7rem 1rem;background:var(--panel);min-width:210px}.toolbar{display:flex;gap:8px;margin:24px 0 10px}.progress{border-left:3px solid var(--blue);background:var(--panel);color:var(--text);margin:0 0 14px;padding:10px 13px}.progress:before{content:'';display:inline-block;width:.8rem;height:.8rem;margin-right:.65rem;border:2px solid var(--line);border-top-color:var(--blue);border-radius:50%;animation:spin .8s linear infinite}.progress.complete{border-left-color:var(--green)}.progress.failed{border-left-color:var(--red)}.progress.complete:before,.progress.failed:before{display:none}@keyframes spin{to{transform:rotate(360deg)}}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}.stat{background:var(--panel);border:1px solid var(--line);padding:12px;text-align:left;width:100%}.stat:hover,.stat.active{background:var(--panel2);border-color:var(--blue)}.stat.active{box-shadow:inset 0 -3px var(--blue)}.stat strong{display:block;font-size:1.35rem}.layout{display:grid;grid-template-columns:360px minmax(0,1fr);gap:14px;min-height:650px}.queue,.detail{border:1px solid var(--line);background:var(--panel);box-shadow:var(--shadow)}.queue-head,.detail-head{padding:16px;border-bottom:1px solid var(--line)}.case-list{max-height:720px;overflow:auto}.case{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid var(--line);border-radius:0;background:transparent;padding:15px}.case:hover,.case.selected{background:var(--panel2)}.case.selected{box-shadow:inset 3px 0 var(--state-color,var(--amber))}.case-title{font-weight:700;margin:.2rem 0}.case-meta{color:var(--muted);font-size:.85rem}.state-published{--state-color:var(--green)}.state-identity-research{--state-color:var(--amber)}.state-final-review{--state-color:var(--blue)}.state-manifest-review{--state-color:#c997ff}.state-promoted,.state-released{--state-color:#5ad6df}.state-duplicate{--state-color:#aab4c3}
/* The revisit block is deliberately quiet: it is available at every
   post-research state and is the forward action at none of them. */
.revisit{margin-top:14px;padding:12px;border:1px dashed #3a4757;border-radius:8px;display:flex;flex-direction:column;gap:8px}
.revisit span{opacity:.72;font-size:13px}
/* Retired: the issue is gone, so the case is history rather than work. */
.state-withdrawn{--state-color:#6b7480}
/* Waiting on the project to register a simulator, not on the reviewer. */
.state-blocked-on-simulator{--state-color:#c997ff}/* Reviewer's turn, before the final gate. */
.state-review-needed{--state-color:#7fb8e8}
/* Something in the submission disagrees with itself. */
.state-needs-clarification,.state-research-blocked,.state-intake-error{--state-color:var(--red)}.pill{display:inline-block;border:1px solid var(--state-color,var(--line));color:var(--state-color,var(--muted));padding:2px 6px;border-radius:10px;font:700 .68rem Consolas,monospace;text-transform:uppercase}.detail-body{padding:20px}.empty{display:grid;place-items:center;min-height:500px;color:var(--muted);text-align:center}.identity{display:flex;justify-content:space-between;gap:15px;align-items:start}.identity h2{margin:.25rem 0}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:18px 0}.field{background:var(--panel2);padding:11px;border:1px solid var(--line)}.field span{display:block;color:var(--muted);font-size:.82rem}.actions{border-top:1px solid var(--line);padding-top:18px;margin-top:18px}.action-row{display:flex;gap:8px;flex-wrap:wrap}.approval{display:flex;gap:8px;align-items:start;color:var(--muted);margin:12px 0}.approval input{margin-top:4px}.blockers{border-left:3px solid var(--red);background:#281719;padding:10px 14px;margin:14px 0}.artifacts{display:flex;gap:6px;flex-wrap:wrap;margin:18px 0}.artifact-toolbar{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px}.view-toggle{display:flex}.view-toggle button{border-radius:0}.view-toggle button:first-child{border-radius:5px 0 0 5px}.view-toggle button:last-child{border-radius:0 5px 5px 0}.view-toggle button.active{border-color:var(--blue);background:#073f54}.artifact-view{white-space:pre-wrap;background:#090c10;border:1px solid var(--line);padding:15px;max-height:620px;overflow:auto;font:12px/1.55 Consolas,monospace;color:#d7e5f8}.research-review{background:#10151c;border:1px solid var(--line);padding:18px;max-height:760px;overflow:auto}.research-review h3{margin:0 0 10px}.research-review h4{margin:20px 0 8px}.review-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.review-card,.claim,.source{background:var(--panel2);border:1px solid var(--line);padding:12px}.review-card strong{display:block;margin-top:3px}.review-prose{color:#d4dfed;max-width:95ch}.review-list{margin:.4rem 0;padding-left:1.25rem}.claims{display:grid;gap:8px}.claim-head{display:grid;grid-template-columns:minmax(180px,1fr) auto auto;gap:10px;align-items:start}.claim-path{font-weight:700;overflow-wrap:anywhere}.claim-value{font:700 .82rem Consolas,monospace;color:#dceaff}.finding{font:700 .68rem Consolas,monospace;text-transform:uppercase;color:var(--state-color,var(--muted))}.finding.established{--state-color:var(--green)}.finding.not-established{--state-color:var(--amber)}.finding.conflicting{--state-color:var(--red)}.claim details,.source details{margin-top:8px}.claim summary,.source summary{cursor:pointer;color:var(--blue)}.source{margin-bottom:8px}.source a{color:#ffc15a}.quote{border-left:3px solid var(--blue);margin:8px 0;padding:4px 10px;color:#d4dfed}.source-ref{font:12px Consolas,monospace;color:var(--muted)}.toast{position:fixed;right:25px;bottom:25px;max-width:520px;padding:14px 18px;background:var(--panel2);border:1px solid var(--blue);box-shadow:var(--shadow);display:none}.toast.error{border-color:var(--red)}input[type=file]{max-width:100%}@media(max-width:900px){.layout{grid-template-columns:1fr}.case-list{max-height:300px}.stats{grid-template-columns:repeat(2,1fr)}.top{display:block}.dataset{margin-top:16px}.grid,.review-summary{grid-template-columns:1fr}.claim-head{grid-template-columns:1fr}.artifact-toolbar{align-items:stretch;flex-direction:column}.view-toggle button{flex:1}}
</style>
</head>
<body>
<main class="shell">
  <header class="top"><div><div class="eyebrow">Local review tools</div><h1>As Driven <span style="color:var(--amber)">Maintainer Workbench</span></h1><div class="subtitle">Synchronize contributions, hand off research, inspect proposals, and cross explicit release gates. Nothing promotes or publishes merely because it appears here.</div></div><div class="dataset"><div class="label">Current dataset</div><strong id="dataset">Loading…</strong><div id="repoState" class="case-meta"></div></div></header>
  <div class="toolbar"><button id="sync" class="primary">Sync GitHub submissions</button><button id="refresh">Refresh local queue</button><button id="finalize" class="ghost">Finalize release + run tests</button></div>
  <div id="progress" class="progress" role="status" aria-live="polite" hidden></div>
  <section class="stats" id="stats"></section>
  <section class="layout"><aside class="queue"><div class="queue-head"><div class="label">Contribution queue</div><strong id="queueCount">0 cases</strong></div><div id="caseList" class="case-list"></div></aside><article class="detail" id="detail"><div class="empty"><div><strong>Select a contribution</strong><br>Its evidence, artifacts, and permitted next actions will appear here.</div></div></article></section>
</main>
<div id="toast" class="toast"></div>
<script>
const token=__TOKEN__;let snapshot=null;let selected=null;let queueFilter='all';let currentArtifact=null;let artifactMode='formatted';
const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function toast(message,error=false){const el=$('#toast');el.textContent=message;el.className='toast'+(error?' error':'');el.style.display='block';setTimeout(()=>el.style.display='none',6000)}
function beginProgress(button,label,message){document.body.classList.add('busy');document.body.setAttribute('aria-busy','true');document.querySelectorAll('.toolbar button').forEach(item=>item.disabled=true);button.dataset.idleLabel=button.textContent;button.textContent=label;const progress=$('#progress');progress.classList.remove('complete','failed');progress.textContent=message;progress.hidden=false}
function endProgress(button,message='',failed=false){button.textContent=button.dataset.idleLabel||button.textContent;delete button.dataset.idleLabel;document.querySelectorAll('.toolbar button').forEach(item=>item.disabled=false);const progress=$('#progress');progress.textContent=message;progress.classList.toggle('complete',Boolean(message)&&!failed);progress.classList.toggle('failed',Boolean(message)&&failed);progress.hidden=!message;document.body.classList.remove('busy');document.body.removeAttribute('aria-busy')}
async function api(path,options={}){const response=await fetch(path,{...options,headers:{'Content-Type':'application/json','X-As-Driven-Token':token,...options.headers}});const body=await response.json();if(!response.ok)throw new Error(body.error||`Request failed (${response.status})`);return body}
function stateClass(state){return `state-${String(state||'unknown').replace(/[^a-z0-9]+/gi,'-').toLowerCase()}`}
function casesForFilter(cases){const filtered=cases.filter(c=>queueFilter==='all'&&c.display_state!=='withdrawn'||queueFilter==='withdrawn'&&c.display_state==='withdrawn'||queueFilter==='research'&&['identity-research','research-blocked'].includes(c.display_state)||queueFilter==='review'&&['final-review','manifest-review'].includes(c.display_state)||queueFilter==='promoted'&&c.display_state==='promoted'||queueFilter==='published'&&c.publication_status==='published');const rank={'manifest-review':0,'final-review':1,'research-blocked':2,'blocked-on-simulator':3,'identity-research':4,'promoted':5,'released':6,'duplicate':7,'published':8,'withdrawn':9};return [...filtered].sort((a,b)=>(rank[a.display_state]??6)-(rank[b.display_state]??6)||(a.issue??0)-(b.issue??0))}
function emptyDetail(message='Select a contribution'){currentArtifact=null;$('#detail').innerHTML=`<div class="empty"><div><strong>${esc(message)}</strong><br>Its evidence, artifacts, and permitted next actions will appear here.</div></div>`}
function renderSnapshot(data){snapshot=data;const r=data.repository_status;$('#dataset').textContent=`${r.dataset_version} · ${r.records} records`;$('#repoState').textContent=`${r.branch||'no branch'} · ${r.tracked_changes?'uncommitted changes':r.ahead_of_upstream?'push required':'release clean'}`;const totals=[['all','Cases',data.cases.filter(c=>c.display_state!=='withdrawn').length],['research','Needs research',data.cases.filter(c=>['identity-research','research-blocked'].includes(c.display_state)).length],['review','Ready to review',data.cases.filter(c=>['final-review','manifest-review'].includes(c.display_state)).length],['promoted','Promoted',data.cases.filter(c=>c.display_state==='promoted').length],['published','Published',data.cases.filter(c=>c.publication_status==='published').length],['withdrawn','Withdrawn',data.cases.filter(c=>c.display_state==='withdrawn').length]];$('#stats').innerHTML=totals.map(([key,label,value])=>`<button class="stat ${queueFilter===key?'active':''}" data-filter="${key}"><span class="label">${esc(label)}</span><strong>${value}</strong></button>`).join('');document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>applyQueueFilter(b.dataset.filter));const visible=casesForFilter(data.cases);if(selected&&!visible.some(c=>c.issue===selected)){selected=null;emptyDetail('Select a contribution')}$('#queueCount').textContent=visible.length===data.cases.length?`${visible.length} case${visible.length===1?'':'s'}`:`${visible.length} of ${data.cases.length} cases`;$('#caseList').innerHTML=visible.map(c=>`<button class="case ${stateClass(c.display_state)} ${selected===c.issue?'selected':''}" data-issue="${c.issue}"><span class="pill ${stateClass(c.display_state)}">${esc(c.display_state)}</span><div class="case-title">#${c.issue} ${esc(c.telemetry_name||c.title)}</div><div class="case-meta">${esc((c.simulator||'').toUpperCase())} · ${esc(c.classification||'unclassified')}</div></button>`).join('');document.querySelectorAll('.case').forEach(b=>b.onclick=()=>selectCase(Number(b.dataset.issue)))}
async function applyQueueFilter(filter){queueFilter=filter;renderSnapshot(snapshot);const visible=casesForFilter(snapshot.cases);if(visible.length)await selectCase(visible[0].issue);else emptyDetail('No cases in this view')}
async function refresh(keep=true){const data=await api('/api/snapshot');renderSnapshot(data);if(keep&&selected&&data.cases.some(c=>c.issue===selected))await selectCase(selected,false)}
function actionButton(id,label,klass=''){return `<button class="${klass}" data-action="${id}">${label}</button>`}
function renderDetail(d){const s=d.summary,c=d.case,obs=c.observation||{},id=obs.identity||{},answers=(c.issue||{}).answers||{},actions=new Set(s.allowed_actions||[]),publicationBlocked=Boolean(d.publication_blockers?.length);currentArtifact=null;let buttons='';const researchDone=c.research?.status==='complete';if(actions.has('generate-research-brief')&&!researchDone)buttons+=actionButton('generate-research-brief','Generate research brief','primary');if(actions.has('import-research')&&!researchDone)buttons+=`<label class="field" style="cursor:pointer">Import completed research JSON<input id="researchFile" type="file" accept=".json,application/json"></label>`;if(actions.has('prepare-review'))buttons+=actionButton('prepare-review','Prepare final review','primary');if(actions.has('promote'))buttons+=`<label class="approval"><input id="promoteApproval" type="checkbox">I reviewed the identity, real-car baseline, simulator overrides, and source wording.</label>${actionButton('promote','Approve and promote','danger')}`;if(researchDone&&actions.has('generate-research-brief'))buttons+=`<div class="revisit"><span>Research is complete. Regenerating the brief does not discard it; importing a new result replaces it.</span>${actionButton('generate-research-brief','Regenerate research brief','ghost')}<label class="field" style="cursor:pointer">Import replacement research JSON<input id="researchFile" type="file" accept=".json,application/json"></label></div>`;if(actions.has('preview-publication'))buttons+=actionButton('preview-publication','Preview GitHub response');if(actions.has('publish-result')&&!publicationBlocked)buttons+=`<label class="approval"><input id="publishApproval" type="checkbox">The release is finalized, committed, pushed, and this response is ready to publish.</label>${actionButton('publish-result','Publish response and close issue','danger')}`;const blockers=publicationBlocked?`<div class="blockers"><strong>Promotion complete, publication pending</strong><ul>${d.publication_blockers.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><p>${esc(d.publication_next_step||'')}</p></div>`:'';const artifacts=d.artifacts.filter(a=>a.exists).map(a=>`<button class="ghost artifact" data-key="${esc(a.key)}">${esc(a.key.replaceAll('_',' '))}</button>`).join('');const idle=s.publication_status==='published'?'No action required for this case.':'This routing state needs a manual maintainer decision.';$('#detail').innerHTML=`<div class="detail-head"><div class="identity"><div><span class="pill ${stateClass(s.display_state)}">${esc(s.display_state)}</span><h2>#${s.issue} ${esc(id.telemetry_name||c.issue?.title)}</h2><div class="case-meta">${esc(obs.simulator?.toUpperCase())} ${esc(obs.game_version||'')} · observed against dataset ${esc(obs.dataset_version||'unknown')}</div></div><a href="${esc(c.issue?.url)}" target="_blank" rel="noreferrer">Open GitHub issue</a></div></div><div class="detail-body"><div class="grid"><div class="field"><span>Contributor’s proposed identity</span>${esc(answers.proposed_identity||'Not supplied')}</div><div class="field"><span>Routing decision</span>${esc(c.classification||'Unclassified')}</div><div class="field"><span>Research</span>${esc(c.research?.status||'Not required')}</div><div class="field"><span>Publication</span>${esc(s.publication_status)}</div></div>${answers.uncertainty?`<div class="field"><span>Contributor notes</span>${esc(answers.uncertainty)}</div>`:''}${blockers}<div class="actions"><div class="label">Permitted next actions</div><div class="action-row" style="margin-top:10px">${buttons||`<span class="case-meta">${idle}</span>`}</div></div><div class="artifacts">${artifacts}</div><div id="artifactToolbar" class="artifact-toolbar" hidden><button id="copyArtifact" class="ghost">Copy displayed artifact</button><div id="artifactToggle" class="view-toggle" hidden><button data-artifact-mode="formatted">Formatted review</button><button data-artifact-mode="json">JSON</button></div></div><div id="artifactFormatted" class="research-review" hidden></div><pre id="artifactView" class="artifact-view" hidden></pre></div>`;document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>runAction(b.dataset.action));document.querySelectorAll('.artifact').forEach(b=>b.onclick=()=>loadArtifact(b.dataset.key));const file=$('#researchFile');if(file)file.onchange=importResearch;$('#copyArtifact').onclick=copyArtifact;document.querySelectorAll('[data-artifact-mode]').forEach(b=>b.onclick=()=>showArtifactMode(b.dataset.artifactMode))}
async function selectCase(issue,rerender=true){selected=issue;if(rerender)renderSnapshot(snapshot);const detail=await api(`/api/cases/${issue}`);renderDetail(detail)}
function displayValue(value){if(value===null||value===undefined||value==='')return 'Not supplied';if(typeof value==='object')return JSON.stringify(value);return String(value)}
function humanPath(path){return String(path||'').replace(/^\//,'').split('/').map(part=>part.replaceAll('_',' ')).join(' › ')}
function renderList(items,empty='None recorded'){return Array.isArray(items)&&items.length?`<ul class="review-list">${items.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`:`<div class="case-meta">${esc(empty)}</div>`}
function formatResearchResult(result){const identity=result.identity||{},researcher=result.researcher||{},claims=Array.isArray(result.claims)?result.claims:[],sources=Array.isArray(result.sources)?result.sources:[],sourceById=new Map(sources.map(source=>[source.source_id,source]));const year=identity.year?.label||[identity.year?.from,identity.year?.to].filter(Boolean).join(' to ')||'Not established';const claimCounts={established:0,'not-established':0,conflicting:0};claims.forEach(claim=>claimCounts[claim.finding]=(claimCounts[claim.finding]||0)+1);const claimHtml=claims.map(claim=>{const refs=(claim.source_refs||[]).map(ref=>{const source=sourceById.get(ref);return `<span class="source-ref">${esc(source?.title||ref)}</span>`}).join(', ');return `<article class="claim"><div class="claim-head"><div class="claim-path">${esc(humanPath(claim.path))}</div><div class="finding ${esc(claim.finding)}">${esc(claim.finding)}</div><div class="claim-value">${esc(displayValue(claim.proposed_value))}</div></div><div class="case-meta">Confidence: ${esc(claim.confidence)} · ${refs||'No source references'}</div><details><summary>Basis and exact field path</summary><p class="review-prose">${esc(claim.basis)}</p><div class="source-ref">${esc(claim.path)}</div></details></article>`}).join('');const sourceHtml=sources.map(source=>{const url=/^https?:\/\//i.test(source.url||'')?source.url:null;const locators=(source.locators||[]).map(locator=>`<div class="quote"><div class="source-ref">${esc(locator.locator)}</div>${locator.quote?`<p>${esc(locator.quote)}</p>`:''}<div class="case-meta">Supports: ${esc((locator.supports||[]).map(humanPath).join(', '))}</div></div>`).join('');return `<article class="source"><strong>${url?`<a href="${esc(url)}" target="_blank" rel="noreferrer">${esc(source.title)}</a>`:esc(source.title)}</strong><div class="case-meta">${esc(source.publisher)} · ${esc(source.source_type)} · retrieved ${esc(source.retrieved_at)}</div><p class="review-prose">${esc(source.exact_scope)}</p><details><summary>${(source.locators||[]).length} locator${(source.locators||[]).length===1?'':'s'} and source notes</summary>${locators}<p class="review-prose">${esc(source.notes||'No additional notes.')}</p><div class="source-ref">${esc(source.source_id)}</div></details></article>`}).join('');return `<h3>${esc(identity.display_name||identity.record_id||'Research result')}</h3><div class="case-meta">${esc(result.research_status)} research by ${esc(researcher.name||'Unknown researcher')} · ${esc(result.researched_at)}</div><div class="review-summary" style="margin-top:14px"><div class="review-card"><span class="label">Identity</span><strong>${esc(identity.status)}</strong><div class="case-meta">${esc(identity.record_action)} · ${esc(identity.confidence)} confidence</div></div><div class="review-card"><span class="label">Proposed record</span><strong>${esc(identity.record_id||'Undetermined')}</strong><div class="case-meta">${esc(identity.manufacturer||'Unknown')} ${esc(identity.model||'')}</div></div><div class="review-card"><span class="label">Year and class</span><strong>${esc(year)}</strong><div class="case-meta">${esc(identity.class||'Class not established')}</div></div></div><h4>Identity basis</h4><p class="review-prose">${esc(identity.basis||'No basis supplied.')}</p>${identity.real_world_identity_notes?`<p class="review-prose">${esc(identity.real_world_identity_notes)}</p>`:''}<h4>Confusion risks</h4>${renderList(identity.confusion_risks,'No confusion risks recorded')}<h4>Field findings</h4><div class="case-meta" style="margin-bottom:8px">${claimCounts.established||0} established · ${claimCounts['not-established']||0} not established · ${claimCounts.conflicting||0} conflicting</div><div class="claims">${claimHtml||'<div class="case-meta">No field findings supplied.</div>'}</div><h4>Reviewed sources</h4>${sourceHtml||'<div class="case-meta">No sources supplied.</div>'}<h4>Open questions</h4>${renderList(result.open_questions,'No open questions')}<h4>Research notes</h4><p class="review-prose">${esc(result.notes||'No additional notes.')}</p>`}
function showArtifactMode(mode){const formatted=$('#artifactFormatted'),raw=$('#artifactView'),isResearch=currentArtifact?.key==='research_result';if(!isResearch)mode='json';artifactMode=mode;formatted.hidden=mode!=='formatted';raw.hidden=mode!=='json';document.querySelectorAll('[data-artifact-mode]').forEach(button=>button.classList.toggle('active',button.dataset.artifactMode===mode))}
async function loadArtifact(key){const a=await api(`/api/cases/${selected}/artifacts/${encodeURIComponent(key)}`);currentArtifact=a;const toolbar=$('#artifactToolbar'),toggle=$('#artifactToggle'),view=$('#artifactView'),formatted=$('#artifactFormatted');toolbar.hidden=false;view.textContent=a.content;formatted.textContent='';toggle.hidden=true;artifactMode='json';if(key==='research_result'){try{formatted.innerHTML=formatResearchResult(JSON.parse(a.content));toggle.hidden=false;artifactMode='formatted'}catch(e){toast('The result could not be formatted; showing its JSON instead.',true)}}showArtifactMode(artifactMode);toolbar.scrollIntoView({behavior:'smooth',block:'nearest'})}
async function copyArtifact(){try{const content=artifactMode==='formatted'&&!$('#artifactFormatted').hidden?$('#artifactFormatted').innerText:currentArtifact?.content||'';await navigator.clipboard.writeText(content);toast('Displayed artifact copied to clipboard')}catch(e){toast('Could not access the clipboard; select the text and copy it manually.',true)}}
async function runAction(action){let payload={};if(action==='promote'){if(!$('#promoteApproval')?.checked)return toast('Review and check the approval statement first.',true);payload.approved=true}if(action==='publish-result'){if(!$('#publishApproval')?.checked)return toast('Confirm the publication statement first.',true);payload.approved=true}document.body.classList.add('busy');try{const result=await api(`/api/cases/${selected}/actions/${action}`,{method:'POST',body:JSON.stringify(payload)});if(action==='preview-publication'){const content=result.result.comment+(result.result.blockers.length?'\n\nPublication blockers:\n- '+result.result.blockers.join('\n- '):'\n\nReady to publish.');currentArtifact={key:'publication_preview',content};$('#artifactToolbar').hidden=false;$('#artifactToggle').hidden=true;$('#artifactView').textContent=content;showArtifactMode('json');toast('GitHub response previewed below')}else toast(`${action.replaceAll('-',' ')} completed`);if(action!=='preview-publication'){await refresh();if(action==='generate-research-brief')await loadArtifact('research_brief')}}catch(e){toast(e.message,true)}finally{document.body.classList.remove('busy')}}
async function importResearch(event){const file=event.target.files[0];if(!file)return;document.body.classList.add('busy');try{const parsed=JSON.parse(await file.text());await api(`/api/cases/${selected}/actions/import-research`,{method:'POST',body:JSON.stringify({research_result:parsed})});toast('Research result imported');await refresh()}catch(e){toast(e.message,true)}finally{document.body.classList.remove('busy')}}
async function refreshLocalQueue(){document.body.classList.add('busy');try{const r=await api('/api/actions/refresh',{method:'POST',body:'{}'});renderSnapshot(r.snapshot);if(selected&&r.snapshot.cases.some(c=>c.issue===selected))await selectCase(selected,false);const imported=r.research_results.imported.length,errors=r.research_results.errors;if(errors.length)toast(`Found ${r.research_results.found} research result(s), but issue #${errors[0].issue} could not be imported: ${errors[0].error}`,true);else if(imported)toast(`Imported ${imported} completed research result${imported===1?'':'s'}`);else toast('Local queue is up to date')}catch(e){toast(e.message,true)}finally{document.body.classList.remove('busy')}}
$('#refresh').onclick=refreshLocalQueue;$('#sync').onclick=async()=>{const button=$('#sync');let outcome='';let failed=false;beginProgress(button,'Syncing...','Downloading and classifying GitHub submissions.');try{const r=await api('/api/actions/sync',{method:'POST',body:'{}'});outcome=`Sync complete: ${r.processed} processed, ${r.skipped} unchanged.`;toast(outcome);await refresh(false)}catch(e){failed=true;outcome=`Sync failed: ${e.message}`;toast(e.message,true)}finally{endProgress(button,outcome,failed)}};$('#finalize').onclick=async()=>{if(!confirm('Regenerate release outputs, validate, and run the full test suite?'))return;const button=$('#finalize');let outcome='';let failed=false;beginProgress(button,'Finalizing release...','Regenerating release outputs, validating the dataset, and running the full test suite. This can take a few minutes.');try{const r=await api('/api/actions/finalize',{method:'POST',body:JSON.stringify({run_tests:true})});outcome=`Complete: dataset ${r.dataset_version} finalized. Validation and the full test suite passed.`;toast(`Dataset ${r.dataset_version} finalized; tests passed`);await refresh()}catch(e){failed=true;outcome=`Finalization failed: ${e.message}`;toast(e.message,true)}finally{endProgress(button,outcome,failed)}};
refresh(false).catch(e=>toast(e.message,true));
</script>
</body></html>'''


def workbench_page(token: str) -> str:
    return WORKBENCH_HTML.replace("__TOKEN__", json.dumps(token))


def create_workbench_server(
    application: WorkbenchApplication,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "localhost"}:
        raise WorkbenchError("the maintainer workbench may bind only to loopback")
    token = secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        server_version = "AsDrivenWorkbench/1"

        def log_message(self, format: str, *args: object) -> None:
            return

        def _json(self, status: HTTPStatus, payload: object) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _payload(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exception:
                raise WorkbenchError("invalid request length") from exception
            if length < 0 or length > MAX_REQUEST_BYTES:
                raise WorkbenchError("request is too large")
            raw = self.rfile.read(length)
            if not raw:
                return {}
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exception:
                raise WorkbenchError("request body must be valid JSON") from exception
            if not isinstance(payload, dict):
                raise WorkbenchError("request body must be a JSON object")
            return payload

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            try:
                if path == "/":
                    body = workbench_page(token).encode("utf-8")
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if path == "/api/snapshot":
                    self._json(HTTPStatus.OK, application.snapshot())
                    return
                artifact_match = re.fullmatch(r"/api/cases/(\d+)/artifacts/([^/]+)", path)
                if artifact_match:
                    self._json(
                        HTTPStatus.OK,
                        application.artifact(
                            int(artifact_match.group(1)), unquote(artifact_match.group(2))
                        ),
                    )
                    return
                case_match = re.fullmatch(r"/api/cases/(\d+)", path)
                if case_match:
                    self._json(HTTPStatus.OK, application.case_detail(int(case_match.group(1))))
                    return
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            except Exception as exception:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exception)})

        def do_POST(self) -> None:
            if self.headers.get("X-As-Driven-Token") != token:
                self._json(HTTPStatus.FORBIDDEN, {"error": "invalid workbench token"})
                return
            path = urlsplit(self.path).path
            try:
                payload = self._payload()
                if path == "/api/actions/refresh":
                    self._json(HTTPStatus.OK, application.refresh_local_queue())
                    return
                if path == "/api/actions/sync":
                    self._json(HTTPStatus.OK, application.sync())
                    return
                if path == "/api/actions/finalize":
                    self._json(HTTPStatus.OK, application.finalize(payload))
                    return
                match = re.fullmatch(r"/api/cases/(\d+)/actions/([a-z-]+)", path)
                if match:
                    self._json(
                        HTTPStatus.OK,
                        application.perform(int(match.group(1)), match.group(2), payload),
                    )
                    return
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            except Exception as exception:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exception)})

    try:
        return LoopbackWorkbenchServer((host, port), Handler)
    except OSError as exception:
        label = f"{host}:{port}" if port else host
        raise WorkbenchError(
            f"could not start the workbench on {label}; another local workbench "
            "may already be running"
        ) from exception


def run_workbench(
    application: WorkbenchApplication,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    server = create_workbench_server(application, host=host, port=port)
    actual_host, actual_port = server.server_address[:2]
    browser_host = "127.0.0.1" if actual_host in {"0.0.0.0", "::"} else actual_host
    url = f"http://{browser_host}:{actual_port}/"
    print(f"As Driven maintainer workbench: {url}")
    print("Localhost only. Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
