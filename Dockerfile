# Touchstone API + appraisal engine.
#
#   CPU:   docker build -t touchstone .
#   CUDA:  docker build -t touchstone:cuda --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu128 .
#   Run:   docker run -p 8000:8000 -v touchstone-data:/app/out -v hf-cache:/root/.cache touchstone
#          (add --gpus all for the CUDA image)
#
# Python 3.9 matches requirements.lock exactly. Model weights download from Hugging Face on first
# use into /root/.cache (mount a volume so they persist); set PRELOAD_MODELS=1 to bake them in.
FROM python:3.9-slim

ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
ARG PRELOAD_MODELS=0
ENV PYTHONUNBUFFERED=1 PYTHONWARNINGS=ignore TOKENIZERS_PARALLELISM=false PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.lock ./
RUN pip install --index-url ${TORCH_INDEX} torch==2.8.0 \
 && grep -v '^torch==' requirements.lock > /tmp/req.txt \
 && pip install -r /tmp/req.txt

COPY pyproject.toml README.md METHOD.md ./
COPY touchstone ./touchstone
COPY envs ./envs
COPY examples ./examples
COPY scripts ./scripts
RUN pip install --no-deps -e .

RUN if [ "$PRELOAD_MODELS" = "1" ]; then python -c "from huggingface_hub import snapshot_download as s; \
[s(r, allow_patterns=['*.json','*.safetensors','*.txt','tokenizer*']) for r in \
['HuggingFaceTB/SmolLM2-135M-Instruct','HuggingFaceTB/SmolLM2-360M-Instruct','HuggingFaceTB/SmolLM2-1.7B-Instruct', \
'sentence-transformers/all-MiniLM-L6-v2']]"; fi

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
# Serve the API (and a built website if one is copied to /app/web/dist).
CMD ["touchstone", "serve", "--host", "0.0.0.0", "--port", "8000"]
