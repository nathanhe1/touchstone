"""Touchstone web API and website host (FastAPI). Start with `touchstone serve --port 8000`.

Contract (documented in docs/API.md):
    POST /api/appraise                multipart: file (.jsonl, or .zip/.tar.gz env folder), kind?, mode? -> 202 {job_id}
    POST /api/appraise/example/{id}   run a bundled demo input -> 202 {job_id}
    GET  /api/jobs/{id}               status, stage, progress, log, error, report
    GET  /api/jobs/{id}/report.md     the readable report
    GET  /api/examples                bundled demo inputs
    GET  /api/health                  {ok, device}
    POST /api/requests                appraisal request from the website form -> 201 {id}
    GET  /api/requests                admin only (Authorization: Bearer $TOUCHSTONE_ADMIN_TOKEN)
    /                                 the built website (web/dist), if present

Jobs run one at a time from a queue, each in its own subprocess (`python -m touchstone.cli appraise`),
so a crash or a GPU memory spike in one job cannot take the server down. Job state persists under
out/jobs/<id>/ and survives restarts.
"""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import threading
import time
import uuid
import zipfile
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

ROOT = Path(__file__).resolve().parents[1]
JOBS = Path(os.environ.get("TOUCHSTONE_JOBS", ROOT / "out" / "jobs"))
DEMO = ROOT / "examples" / "demo"
MAX_UPLOAD = int(os.environ.get("TOUCHSTONE_MAX_UPLOAD_MB", "50")) * 1024 * 1024
MAX_UNPACKED = 200 * 1024 * 1024
INPUT_TTL_DAYS = 7
STAGES = ["validate", "seal", "overlap", "probe", "train", "measure", "forecast", "price", "report"]
STAGE_RE = re.compile(r"@stage (\w+) ([0-9.]+)")
LOG_KEEP = 200

app = FastAPI(title="Touchstone API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_queue: "queue.Queue[str]" = queue.Queue()
_lock = threading.Lock()
_settings = {"device": "auto", "extra_args": []}


# ---------------------------------------------------------------- job store

def _job_dir(job_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{12}", job_id):
        raise HTTPException(404, "no such job")
    return JOBS / job_id


def _read(job_id: str) -> dict:
    f = _job_dir(job_id) / "job.json"
    if not f.exists():
        raise HTTPException(404, "no such job")
    return json.loads(f.read_text())


def _write(job: dict):
    d = JOBS / job["job_id"]
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "job.json.tmp"
    tmp.write_text(json.dumps(job, indent=1))
    tmp.replace(d / "job.json")


def _update(job_id: str, **kw):
    with _lock:
        job = json.loads((JOBS / job_id / "job.json").read_text())
        job.update(kw)
        _write(job)
        return job


def _new_job(input_path: Path, kind: str, mode: str, label: str, job_id: str | None = None) -> str:
    job_id = job_id or uuid.uuid4().hex[:12]
    _write({"job_id": job_id, "status": "queued", "stage": "validate", "progress": 0.0, "log": [],
            "error": None, "report": None, "kind": kind, "mode": mode, "input": str(input_path), "label": label,
            "created": time.time()})
    _queue.put(job_id)
    return job_id


# ---------------------------------------------------------------- worker

def _run_job(job_id: str):
    job = _update(job_id, status="running", started=time.time())
    out = JOBS / job_id / "result"
    cmd = [sys.executable, "-u", "-m", "touchstone.cli", "appraise", job["input"], "--kind", job["kind"],
           "--out", str(out), "--device", _settings["device"]] + (["--quick"] if job["mode"] == "quick" else [])
    cmd += _settings["extra_args"]
    log: deque = deque(maxlen=LOG_KEEP)
    env = dict(os.environ, PYTHONWARNINGS="ignore", TOKENIZERS_PARALLELISM="false")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT, env=env)
    last_write = 0.0
    stage, progress = "validate", 0.0
    for line in proc.stdout:
        line = line.rstrip()
        m = STAGE_RE.search(line)
        if m:
            stage, progress = m.group(1), float(m.group(2))
        elif line and "Warning" not in line and "warnings.warn" not in line and "MallocStackLogging" not in line:
            log.append(re.sub(r"^\[\d\d:\d\d:\d\d\] ", "", line))
        if time.time() - last_write > 0.5 or m:
            _update(job_id, stage=stage, progress=round(progress, 3), log=list(log)[-50:])
            last_write = time.time()
    rc = proc.wait()
    report = out / "report.json"
    if rc == 0 and report.exists():
        _update(job_id, status="done", stage="report", progress=1.0, log=list(log)[-50:],
                report=json.loads(report.read_text()), finished=time.time())
    else:
        err = next((x for x in reversed(log) if x.startswith("error:")), None) or \
            (list(log)[-1] if log else f"appraisal failed (exit code {rc})")
        _update(job_id, status="error", error=err.replace("error: ", "", 1), log=list(log)[-50:], finished=time.time())


def _worker():
    while True:
        job_id = _queue.get()
        try:
            _run_job(job_id)
        except Exception as e:  # never let one job kill the worker
            try:
                _update(job_id, status="error", error=f"internal error: {type(e).__name__}: {e}")
            except Exception:
                pass


def _recover_and_clean():
    """On startup: requeue unfinished jobs and delete uploaded inputs older than 7 days."""
    JOBS.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - INPUT_TTL_DAYS * 86400
    for d in sorted(JOBS.iterdir()):
        f = d / "job.json"
        if not f.exists():
            continue
        try:
            job = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        upload = d / "input"
        if upload.exists() and job.get("created", 0) < cutoff:
            shutil.rmtree(upload, ignore_errors=True)
        if job["status"] in ("queued", "running"):
            if Path(job["input"]).exists():
                job.update(status="queued", stage="validate", progress=0.0)
                _write(job)
                _queue.put(job["job_id"])
            else:
                job.update(status="error", error="server restarted and the input is gone")
                _write(job)


@app.on_event("startup")
def _startup():
    _recover_and_clean()
    init_db()
    threading.Thread(target=_worker, daemon=True).start()


# ---------------------------------------------------------------- uploads

def _safe_extract(archive: Path, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                target = (dest / info.filename).resolve()
                if not str(target).startswith(str(dest.resolve())) or info.filename.startswith("/"):
                    raise HTTPException(400, "archive contains unsafe paths")
                total += info.file_size
                if total > MAX_UNPACKED:
                    raise HTTPException(413, "archive expands beyond 200 MB")
            z.extractall(dest)
    else:
        with tarfile.open(archive, "r:gz") as t:
            members = []
            for mem in t.getmembers():
                target = (dest / mem.name).resolve()
                if not str(target).startswith(str(dest.resolve())) or mem.issym() or mem.islnk() or mem.isdev():
                    raise HTTPException(400, "archive contains unsafe paths or links")
                total += mem.size
                if total > MAX_UNPACKED:
                    raise HTTPException(413, "archive expands beyond 200 MB")
                members.append(mem)
            t.extractall(dest, members=members)


def _find_env(root: Path) -> Path:
    cands = [p.parent for p in root.rglob("env.py") if "__MACOSX" not in p.parts and "__pycache__" not in p.parts]
    if not cands:
        raise HTTPException(400, "the archive has no env.py; an environment folder must contain env.py defining ENV")
    return min(cands, key=lambda p: len(p.parts))


@app.post("/api/appraise", status_code=202)
async def appraise(file: UploadFile = File(...), kind: str | None = Form(None), mode: str = Form("quick")):
    if mode not in ("quick", "full"):
        raise HTTPException(400, "mode must be 'quick' or 'full'")
    if kind not in (None, "", "dataset", "env"):
        raise HTTPException(400, "kind must be 'dataset' or 'env'")
    name = Path(file.filename or "upload").name
    low = name.lower()
    if low.endswith(".jsonl"):
        detected = "dataset"
    elif low.endswith((".zip", ".tar.gz", ".tgz")):
        detected = "env"
    else:
        raise HTTPException(415, "upload a .jsonl dataset or a .zip / .tar.gz environment folder")
    kind = kind or detected
    if kind != detected:
        raise HTTPException(400, f"a {name} upload is a {detected}, not a {kind}")
    job_id = uuid.uuid4().hex[:12]
    d = JOBS / job_id / "input"
    d.mkdir(parents=True, exist_ok=True)
    raw = d / name
    size = 0
    with raw.open("wb") as fh:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            if size > MAX_UPLOAD:
                fh.close()
                shutil.rmtree(JOBS / job_id, ignore_errors=True)
                raise HTTPException(413, f"upload exceeds {MAX_UPLOAD // (1024 * 1024)} MB")
            fh.write(chunk)
    if size == 0:
        shutil.rmtree(JOBS / job_id, ignore_errors=True)
        raise HTTPException(400, "empty upload")
    target = raw
    if kind == "env":
        try:
            if low.endswith(".tgz"):
                raw = raw.rename(raw.with_name(raw.name[:-4] + ".tar.gz"))
            _safe_extract(raw, d / "unpacked")
            target = _find_env(d / "unpacked")
        except HTTPException:
            shutil.rmtree(JOBS / job_id, ignore_errors=True)
            raise
        except (zipfile.BadZipFile, tarfile.TarError, OSError):
            shutil.rmtree(JOBS / job_id, ignore_errors=True)
            raise HTTPException(400, "could not read the archive")
    return {"job_id": _new_job(target, kind, mode, name, job_id)}


# ---------------------------------------------------------------- examples

def _examples() -> list[dict]:
    f = DEMO / "index.json"
    return json.loads(f.read_text()) if f.exists() else []


@app.get("/api/examples")
def examples():
    return [{k: e[k] for k in ("id", "name", "kind", "description")} for e in _examples()]


@app.post("/api/appraise/example/{example_id}", status_code=202)
def appraise_example(example_id: str, mode: str = "quick"):
    if mode not in ("quick", "full"):
        raise HTTPException(400, "mode must be 'quick' or 'full'")
    ex = next((e for e in _examples() if e["id"] == example_id), None)
    if ex is None:
        raise HTTPException(404, "no such example")
    return {"job_id": _new_job(DEMO / ex["path"], ex["kind"], mode, ex["name"])}


# ---------------------------------------------------------------- jobs

@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = _read(job_id)
    return {k: job.get(k) for k in ("job_id", "status", "stage", "progress", "log", "error", "report")}


@app.get("/api/jobs/{job_id}/report.md")
def job_report_md(job_id: str):
    f = _job_dir(job_id) / "result" / "report.md"
    if not f.exists():
        raise HTTPException(404, "report not ready")
    return PlainTextResponse(f.read_text(), media_type="text/markdown")


@app.get("/api/health")
def health():
    if _settings["device"] == "mlx":
        dev = "mlx"
    elif _settings["device"] == "cpu":
        dev = "cpu"
    else:
        import torch
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
    return {"ok": True, "device": dev, "queued": _queue.qsize()}


# ---------------------------------------------------------------- appraisal requests (website form)

EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$")
KINDS = {"rl_environment", "dataset", "other"}
LIMITS = {"name": 120, "email": 254, "company": 160, "role": 120, "description": 4000, "budget": 120}
RATE = int(os.environ.get("TOUCHSTONE_REQUEST_RATE", "5"))  # per IP per hour
_hits: dict[str, deque] = defaultdict(deque)


def _db_path() -> Path:
    return Path(os.environ.get("TOUCHSTONE_DB", ROOT / "out" / "touchstone.db"))


def init_db():
    p = _db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(p) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS requests (
            id TEXT PRIMARY KEY, created REAL, name TEXT, email TEXT, company TEXT, role TEXT,
            material_kind TEXT, description TEXT, budget TEXT, consent INTEGER, ip TEXT)""")


@app.post("/api/requests", status_code=201)
async def create_request(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= RATE:
        raise HTTPException(429, "too many requests from this address; try again later")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "send a JSON body")
    if not isinstance(body, dict):
        raise HTTPException(400, "send a JSON object")
    errors = {}
    clean = {}
    for k in ("name", "email", "company", "role", "description"):
        v = body.get(k)
        if not isinstance(v, str) or not v.strip():
            errors[k] = "required"
        elif len(v) > LIMITS[k]:
            errors[k] = f"at most {LIMITS[k]} characters"
        else:
            clean[k] = v.strip()
    if "email" in clean and not EMAIL.match(clean["email"]):
        errors["email"] = "not a valid email address"
    if body.get("material_kind") not in KINDS:
        errors["material_kind"] = "one of rl_environment, dataset, other"
    budget = body.get("budget")
    if budget is not None and (not isinstance(budget, (str, int, float)) or len(str(budget)) > LIMITS["budget"]):
        errors["budget"] = "optional; text up to 120 characters"
    if body.get("consent") is not True:
        errors["consent"] = "must be true"
    if errors:
        return JSONResponse(status_code=422, content={"detail": "invalid request", "errors": errors})
    q.append(now)
    rid = uuid.uuid4().hex[:12]
    with sqlite3.connect(_db_path()) as c:
        c.execute("INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  (rid, now, clean["name"], clean["email"], clean["company"], clean["role"], body["material_kind"],
                   clean["description"], None if budget is None else str(budget), 1, ip))
    return {"id": rid}


@app.get("/api/requests")
def list_requests(request: Request):
    token = os.environ.get("TOUCHSTONE_ADMIN_TOKEN")
    if not token:
        raise HTTPException(404, "not found")
    if request.headers.get("authorization") != f"Bearer {token}":
        raise HTTPException(401, "unauthorized")
    with sqlite3.connect(_db_path()) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT id, created, name, email, company, role, material_kind, description, budget "
                         "FROM requests ORDER BY created DESC").fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- website

def mount_site(site: Path | None):
    if site is None or not (site / "index.html").exists():
        return

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "not found")
        f = (site / path).resolve()
        if path and str(f).startswith(str(site.resolve())) and f.is_file():
            return FileResponse(f)
        return FileResponse(site / "index.html")


def serve(port: int = 8000, host: str = "127.0.0.1", device: str = "auto", site: str | None = None):
    import uvicorn
    _settings["device"] = device
    site_dir = Path(site) if site else ROOT / "web" / "dist"
    mount_site(site_dir)
    uvicorn.run(app, host=host, port=port, log_level="info")
