# Touchstone API

`touchstone serve --port 8000` starts the API (FastAPI + uvicorn). CORS is open for local development. If a built website exists at `<repo>/web/dist` (or `--site DIR`), it is served at `/` with an `index.html` fallback; everything under `/api/` stays the API.

Jobs run one at a time from a queue, each in its own subprocess, so a bad input or a GPU memory spike cannot take the server down. Job state persists under `out/jobs/<id>/` (or `$TOUCHSTONE_JOBS`) and survives restarts: unfinished jobs are re-queued on startup. Uploaded inputs older than 7 days are deleted on startup.

## Appraisals

### `POST /api/appraise` → `202 {"job_id": str}`

Multipart form:

| field | required | values |
|---|---|---|
| `file` | yes | a `.jsonl` dataset, or a `.zip` / `.tar.gz` / `.tgz` environment folder containing `env.py` |
| `kind` | no | `dataset` or `env` (auto-detected from the file type) |
| `mode` | no | `quick` (default) or `full` |

Errors: `415` other file types; `413` larger than 50 MB (`TOUCHSTONE_MAX_UPLOAD_MB`) or an archive that expands beyond 200 MB; `400` empty file, bad `mode`/`kind`, an unreadable archive, unsafe paths or links in the archive, or no `env.py`. Content problems such as invalid JSON lines or a missing `ENV` surface as a job with `status: "error"` and a readable `error` that names the file and line.

### `POST /api/appraise/example/{id}` → `202 {"job_id": str}`

Runs a bundled demo input (see `/api/examples`). Optional query `?mode=quick|full`.

### `GET /api/examples` → `[{"id", "name", "kind", "description"}]`

| id | kind | expected result |
|---|---|---|
| `good-dataset` | dataset | measurable gain, no red flags |
| `contaminated-dataset` | dataset | `contaminated`, not priced |
| `noisy-dataset` | dataset | `noisy_labels`, not priced |
| `gameable-env` | env | `gameable_grader`, not priced |

### `GET /api/jobs/{job_id}`

```json
{
  "job_id": "3f2a9c1d0b7e",
  "status": "queued | running | done | error",
  "stage": "validate | seal | overlap | probe | train | measure | forecast | price | report",
  "progress": 0.42,
  "log": ["Appraising dataset good.jsonl: 400 examples; ...", "  135M seed 0 material: accuracy 31.7% ..."],
  "error": null,
  "report": null
}
```

`progress` runs from 0 to 1 and `log` holds the latest human-readable lines (up to 50). When `status` is `done`, `report` is the full `report.json` (below). When it is `error`, `error` is a one-line explanation.

### `GET /api/jobs/{job_id}/report.md` → `text/markdown`

The readable report. `404` until the job is done.

### `GET /api/health` → `{"ok": true, "device": "mps" | "cuda" | "mlx" | "cpu", "queued": int}`

## report.json (schema_version 1.0)

The top-level fields below are the stable contract. Everything else in the file is detail that may grow.

| field | type | meaning |
|---|---|---|
| `schema_version` | str | `"1.0"` |
| `kind` | str | `dataset` or `env` |
| `mode` | str | `quick` or `full` |
| `grade` | str | `A`-`F` (rubric in METHOD.md) |
| `fair_value_per_item` | number | dollars per unique item; `0` when any blocking flag fires |
| `flags` | list | `[{"code", "severity": "block" \| "discount" \| "info", "text"}]` |
| `overlap` | object | `{"suite": share of held-out items found in the material (or of the material matching the suite, whichever is larger), "public": share already in free public data, "duplicates": share of repeated items}`, each 0-1 |
| `probes` | object | `{probe name: reward earned 0-1}` from the grader audit (empty for datasets) |
| `gains_by_size` | object | `{"135M": {"net", "lo", "hi", "raw", "placebo"}, ...}`: held-out accuracy points; `net` = material minus placebo (only a helpful placebo is subtracted), `lo`/`hi` its 90% interval |
| `forecast` | object | `{"value", "lo", "hi", "method", "target", "source"}`: net gain at `target` (1.7B). `source` is `measured` in full mode (1.7B was trained) or `forecast`; `method` is e.g. `calibrated from 135M`, `rank_largest` or `measured` |
| `summary` | str | one paragraph in plain English |
| `material` | object | `{path, name, sha256, n_items, unique_items}` |
| `heldout` | object | `{name, domain, description, n_items, source, ...}` |
| `device` | str | backend the run used |

Flag codes: `gameable_grader`, `answer_leakage`, `contaminated`, `copied_from_public`, `duplicated`, `noisy_labels`, `off_topic`, `transfer_gap`, `no_measurable_gain`, `harmful`, `no_learning_signal`, `suppresses_reasoning`.

Detail fields: `rungs` (per-size measurements, seeds, training curves and sample outputs), `forecast_detail`, `overlap_detail` (match kinds and examples), `grader_audit`, `label_quality`, `relevance`, `fair_value` (with the formula inputs), `recipe`, `models`, `runtime_s`.

## Appraisal requests (website form)

### `POST /api/requests` → `201 {"id": str}`

JSON body:

```json
{"name": "Ada Lovelace", "email": "ada@lab.ai", "company": "Lab", "role": "RL lead",
 "material_kind": "rl_environment | dataset | other", "description": "What you want appraised",
 "budget": "optional free text", "consent": true}
```

`422 {"detail", "errors": {field: message}}` on missing fields, a bad email, length limits (name 120, email 254, company 160, role 120, description 4000, budget 120), an unknown `material_kind`, or `consent` not `true`. `429` after 5 requests per hour from one address (`TOUCHSTONE_REQUEST_RATE`). Stored in SQLite at `out/touchstone.db` (`TOUCHSTONE_DB`); stored data is never echoed back.

### `GET /api/requests`

Requires `Authorization: Bearer $TOUCHSTONE_ADMIN_TOKEN`. Returns `404` when the env var is unset (endpoint disabled) and `401` on a wrong token. Response: a list of `{id, created, name, email, company, role, material_kind, description, budget}`, newest first.

## Example

```bash
curl -F file=@examples/demo/good_word_problems.jsonl -F mode=quick localhost:8000/api/appraise
curl localhost:8000/api/jobs/<job_id>
curl localhost:8000/api/jobs/<job_id>/report.md
```
