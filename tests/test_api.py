"""API tests: contract, validation, appraisal requests, and one quick example job end to end."""
import importlib
import io
import json
import time
import zipfile

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TOUCHSTONE_JOBS", str(tmp_path / "jobs"))
    monkeypatch.setenv("TOUCHSTONE_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("TOUCHSTONE_JOB_ARGS", "--suite-items 20 --steps 2")
    monkeypatch.setenv("TOUCHSTONE_MAX_UPLOAD_MB", "1")
    from fastapi.testclient import TestClient
    import touchstone.server as server
    server = importlib.reload(server)
    with TestClient(server.app) as c:
        yield c, server


def test_health_and_examples(client):
    c, _ = client
    h = c.get("/api/health").json()
    assert h["ok"] is True and h["device"] in ("mps", "mlx", "cpu", "cuda")
    ex = c.get("/api/examples").json()
    assert {e["id"] for e in ex} >= {"good-dataset", "contaminated-dataset", "noisy-dataset", "gameable-env"}
    assert set(ex[0]) == {"id", "name", "kind", "description"}


def test_upload_validation(client):
    c, _ = client
    r = c.post("/api/appraise", files={"file": ("x.xlsx", b"a,b\n", "application/octet-stream")})
    assert r.status_code == 415 and ".parquet" in r.json()["detail"]
    r = c.post("/api/appraise", files={"file": ("x.jsonl", b"", "application/json")})
    assert r.status_code == 400
    r = c.post("/api/appraise", files={"file": ("x.jsonl", b"x" * (2 * 1024 * 1024), "application/json")})
    assert r.status_code == 413
    r = c.post("/api/appraise", files={"file": ("x.jsonl", b"{}\n", "application/json")}, data={"mode": "slow"})
    assert r.status_code == 400
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("../evil.py", "x")
    r = c.post("/api/appraise", files={"file": ("e.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 400
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("readme.txt", "no env here")
    r = c.post("/api/appraise", files={"file": ("e.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 400 and "env.py" in r.json()["detail"]
    assert c.get("/api/jobs/zzz").status_code == 404
    assert c.post("/api/appraise/example/nope").status_code == 404


def test_csv_json_and_parquet_uploads_are_accepted_as_datasets(client):
    c, server = client
    for name in ("d.csv", "d.json", "d.parquet", "d.jsonl.gz", "d.tsv"):
        r = c.post("/api/appraise", files={"file": (name, b"prompt,completion\nx,y\n", "application/octet-stream")})
        assert r.status_code == 202, name
        c.post(f"/api/jobs/{r.json()['job_id']}/cancel")


def test_bad_dataset_job_reports_a_clear_error(client):
    c, _ = client
    r = c.post("/api/appraise", files={"file": ("bad.jsonl", b'{"text": "no prompt"}\n' * 30, "application/json")})
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    job = _wait(c, job_id, 120)
    assert job["status"] == "error" and "unrecognised format" in job["error"]


def test_requests_endpoint(client, monkeypatch):
    c, server = client
    good = {"name": "Ada", "email": "ada@example.com", "company": "Lab", "role": "RL lead",
            "material_kind": "rl_environment", "description": "Coding envs from two vendors.", "consent": True}
    r = c.post("/api/requests", json=good)
    assert r.status_code == 201 and len(r.json()["id"]) == 12
    no_role = {k: v for k, v in good.items() if k != "role"}  # role is optional on the website form
    assert c.post("/api/requests", json=dict(no_role, budget=None)).status_code == 201
    bad = dict(good, email="not-an-email", consent=False, material_kind="x")
    r = c.post("/api/requests", json=bad)
    assert r.status_code == 422 and set(r.json()["errors"]) >= {"email", "consent", "material_kind"}
    assert c.post("/api/requests", json=dict(good, description="x" * 5000)).status_code == 422
    # admin listing is disabled without a token, and needs the right bearer token when set
    assert c.get("/api/requests").status_code == 404
    monkeypatch.setenv("TOUCHSTONE_ADMIN_TOKEN", "s3cret")
    assert c.get("/api/requests").status_code == 401
    rows = c.get("/api/requests", headers={"Authorization": "Bearer s3cret"}).json()
    assert rows[0]["email"] == "ada@example.com" and "ip" not in rows[0]
    # rate limit: 5 per hour per address (two already used above)
    codes = [c.post("/api/requests", json=good).status_code for _ in range(4)]
    assert codes[:3] == [201] * 3 and codes[3] == 429


def _wait(c, job_id, timeout):
    t = time.time()
    while time.time() - t < timeout:
        job = c.get(f"/api/jobs/{job_id}").json()
        assert set(job) == {"job_id", "status", "stage", "progress", "log", "error", "report", "ahead"}
        if job["status"] in ("done", "error"):
            return job
        time.sleep(1)
    raise AssertionError(f"job {job_id} did not finish in {timeout}s: {job}")


@pytest.mark.slow
def test_example_job_end_to_end(client):
    c, server = client
    r = c.post("/api/appraise/example/contaminated-dataset")
    assert r.status_code == 202
    job = _wait(c, r.json()["job_id"], 900)
    assert job["status"] == "done", job["error"]
    assert job["stage"] == "report" and job["progress"] == 1.0 and job["log"]
    rep = job["report"]
    for k in ("grade", "fair_value_per_item", "flags", "overlap", "probes", "gains_by_size", "forecast", "summary"):
        assert k in rep
    assert set(rep["overlap"]) == {"suite", "public", "duplicates"}
    assert {"value", "lo", "hi", "method"} <= set(rep["forecast"])
    assert "contaminated" in [f["code"] for f in rep["flags"]]
    md = c.get(f"/api/jobs/{r.json()['job_id']}/report.md")
    assert md.status_code == 200 and md.headers["content-type"].startswith("text/markdown")
    assert md.text.startswith("# Touchstone appraisal")
    # responses never reveal the server's own folders
    root = str(server.ROOT)
    assert root not in json.dumps(job) and root not in md.text


def test_ahead_counts_the_queue_and_the_running_job():
    from touchstone import server
    for job_id in ("first", "second"):
        server._queue.put(job_id)
    try:
        assert server._ahead("first") == 0
        assert server._ahead("second") == 1
        server._busy.set()
        assert server._ahead("first") == 1
        assert server._ahead("second") == 2
    finally:
        server._busy.clear()
        while not server._queue.empty():
            server._queue.get()


def test_cancel_stops_a_queued_job_and_leaves_a_finished_one(client, monkeypatch):
    import queue
    c, server = client
    monkeypatch.setattr(server, "_queue", queue.Queue())  # out of the worker's reach
    server._write({"job_id": "aaaaaaaaaaaa", "status": "queued", "stage": "validate", "progress": 0.0, "log": []})
    server._queue.put("aaaaaaaaaaaa")
    assert c.post("/api/jobs/aaaaaaaaaaaa/cancel").json()["status"] == "cancelled"
    assert "aaaaaaaaaaaa" not in list(server._queue.queue)
    assert c.get("/api/jobs/aaaaaaaaaaaa").json()["status"] == "cancelled"
    server._write({"job_id": "bbbbbbbbbbbb", "status": "done", "stage": "report", "progress": 1.0, "log": []})
    assert c.post("/api/jobs/bbbbbbbbbbbb/cancel").json()["status"] == "done"
