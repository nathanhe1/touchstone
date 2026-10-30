# Deploying Touchstone

The API and engine run as one process (`touchstone serve`). Jobs run one at a time, so one GPU is enough. Nothing here creates accounts or deploys on its own.

## Local (Mac, Apple silicon)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-mac.txt && .venv/bin/pip install --no-deps -e .
.venv/bin/touchstone serve --port 8000            # API at :8000/api, website at :8000/ if web/dist is built
```

## Docker

```bash
docker build -t touchstone .                                                  # CPU
docker build -t touchstone:cuda --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu128 .   # NVIDIA GPU
docker run -p 8000:8000 -v touchstone-out:/app/out -v hf-cache:/root/.cache touchstone
docker run --gpus all -p 8000:8000 -v touchstone-out:/app/out -v hf-cache:/root/.cache touchstone:cuda
```

- Add `--build-arg PRELOAD_MODELS=1` to bake the model weights (about 4.5 GB) into the image, so the first job doesn't wait for downloads.
- To serve the website from the same container, build it first (`web/dist`) and add `COPY web/dist ./web/dist` before `CMD`, or mount it: `-v $PWD/web/dist:/app/web/dist`.
- Persist `/app/out` (jobs, SQLite requests database) and `/root/.cache` (model weights).
- Environment: `TOUCHSTONE_ADMIN_TOKEN` (enables `GET /api/requests`), `TOUCHSTONE_DB`, `TOUCHSTONE_JOBS`, `TOUCHSTONE_MAX_UPLOAD_MB`, `TOUCHSTONE_REQUEST_RATE`.

## Cloud GPU

Any single-GPU VM with 16 GB or more of GPU memory runs the full mode comfortably (an L4 or A10G is plenty; a T4 works for quick mode). The engine picks CUDA automatically (`/api/health` reports `"device": "cuda"`).

**Plain GPU VM** (for example a GCP g2-standard-4 with an L4, or an AWS g5.xlarge): install Docker and the NVIDIA container toolkit, then run the CUDA image as above behind a TLS-terminating proxy (Caddy or nginx) on 443.

**Modal:** wrap the image in a `modal.Image.from_dockerfile("Dockerfile", build_args={"TORCH_INDEX": "https://download.pytorch.org/whl/cu128"})`, mount a `modal.Volume` at `/app/out` and another at `/root/.cache`, and expose `touchstone.server:app` with `@modal.asgi_app()` on a `gpu="L4"` function with `concurrency_limit=1` (jobs are sequential anyway). Call `touchstone.server._startup()` inside the function if you bypass `touchstone serve`.

**Fly.io:** `fly launch --no-deploy`, set `[[vm]] size = "l40s"` (or `a10`) in `fly.toml`, attach a volume at `/app/out`, set `TOUCHSTONE_ADMIN_TOKEN` with `fly secrets set`, then `fly deploy`.

## Security notes

- Vendor environment code (`env.py`) runs inside the job subprocess with the server's permissions. For untrusted vendors, run jobs in a separate sandbox (gVisor or Firecracker, with no network and a read-only filesystem except the job folder) before exposing uploads publicly.
- Uploads are capped (50 MB, or 200 MB unpacked), checked for path traversal and links, and only `.jsonl`, `.zip` and `.tar.gz` are accepted.
- `GET /api/requests` is disabled unless `TOUCHSTONE_ADMIN_TOKEN` is set. Use a long random token.
- Rate limiting is in-memory and per process. Behind a proxy, make sure the client IP is forwarded (`--proxy-headers` in uvicorn) or limit at the proxy.
