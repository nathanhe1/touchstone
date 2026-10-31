"""One-minute diagnosis of the torch judge route. Prints raw generations under each setting.

    python scripts/debug_judge_torch.py

Self-contained: it needs only torch and transformers. A setting is healthy when `finite=True` and the
answers read 12 and 47 and the program lines compute them.
"""
import sys
import time

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

REPO = "Qwen/Qwen2.5-1.5B-Instruct"
SYS = "You are a careful solver. Think step by step, then give the final answer as \\boxed{answer}."
Q = ["Kim runs 4 laps every day for 3 days. How many laps does she run?",
     "A jar holds 50 marbles. Ben adds 3 marbles and then takes out 6. How many marbles are in the jar?",
     "What is 7 + 5? Show each step of your reasoning carefully, then state the result in a sentence."]
dev = "cuda" if torch.cuda.is_available() else "mps"
print("torch", torch.__version__, "transformers", transformers.__version__, "device", dev, flush=True)
tok = AutoTokenizer.from_pretrained(REPO, padding_side="left")
print("pad", repr(tok.pad_token), tok.pad_token_id, "eos", repr(tok.eos_token), tok.eos_token_id, flush=True)
texts = [tok.apply_chat_template([{"role": "system", "content": SYS}, {"role": "user", "content": p}], tokenize=False,
                                 add_generation_prompt=True) for p in Q]
print("template head:", repr(texts[0][:120]), flush=True)
kw = {"max_new_tokens": 90, "do_sample": False, "temperature": None, "top_p": None, "top_k": None}
for dtype in (torch.float16, torch.bfloat16, torch.float32):
    for attn in ("eager", "sdpa"):
        t0 = time.time()
        try:
            m = AutoModelForCausalLM.from_pretrained(REPO, dtype=dtype, attn_implementation=attn).to(dev).eval()
            enc = tok(texts, return_tensors="pt", padding=True).to(dev)
            with torch.no_grad():
                logits = m(**enc).logits
                finite = bool(torch.isfinite(logits).all())
                nan_rows = torch.isnan(logits).reshape(len(Q), -1).any(1).tolist()
                batched = m.generate(**enc, **kw)
                solo = m.generate(**tok(texts[:1], return_tensors="pt").to(dev), **kw)
            print(f"\n== {dtype} {attn} finite={finite} nan_rows={nan_rows} {time.time() - t0:.1f}s", flush=True)
            for g in tok.batch_decode(batched[:, enc.input_ids.shape[1]:], skip_special_tokens=True):
                print("  batch:", repr(g[-110:]))
            print("  solo :", repr(tok.decode(solo[0][tok(texts[:1], return_tensors='pt').input_ids.shape[1]:], skip_special_tokens=True)[-110:]))
            del m
            torch.cuda.empty_cache() if dev == "cuda" else None
        except Exception as e:
            print(f"\n== {dtype} {attn} ERROR {type(e).__name__}: {str(e)[:200]}", file=sys.stdout, flush=True)
