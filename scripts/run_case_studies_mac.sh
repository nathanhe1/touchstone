#!/bin/sh
# Case-study appraisals on a 16 GB Mac: one at a time, quick mode, CPU, killed above MAX_MB of resident memory.
cd "$(dirname "$0")/.."
I=${CASE_INPUTS:-$HOME/.cache/touchstone/case_studies/inputs}
MAX_MB=${MAX_MB:-7000}
export PYTHONPATH=$PWD CASE_INPUTS=$I
mkdir -p out/case_studies
git rev-parse HEAD > out/case_studies/ENGINE_COMMIT
run() {
  n=$1; shift; s=$(date +%s); peak=0
  .venv/bin/python "$@" > out/case_studies/$n.stdout 2>&1 &
  pid=$!
  while kill -0 $pid 2>/dev/null; do
    mb=$(( $(ps -o rss= -p $pid 2>/dev/null || echo 0) / 1024 ))
    [ "$mb" -gt "$peak" ] && peak=$mb
    if [ "$mb" -gt "$MAX_MB" ]; then kill -9 $pid; echo "$n KILLED at ${mb} MB" | tee -a out/case_studies/timing_mac.txt; fi
    sleep 5
  done
  wait $pid; echo "$n exit=$? $(($(date +%s)-s))s peak_rss=${peak}MB" | tee -a out/case_studies/timing_mac.txt
}
A="-m touchstone.cli appraise"
run code_alpaca_quick $A $I/code_alpaca_20k.json --kind dataset --suite $I/humaneval_suite.jsonl --quick --device cpu --out out/case_studies/code_alpaca_quick
run math_train_quick $A $I/math_train.jsonl --kind dataset --suite $I/math_test_suite.jsonl --quick --device cpu --out out/case_studies/math_train_quick
run math_full_suite_overlap scripts/case_full_suite_overlap.py
run mathinstruct_quick $A $I/mathinstruct.jsonl --kind dataset --suite $I/math_test_suite.jsonl --quick --device cpu --out out/case_studies/mathinstruct_quick
echo ALLDONE | tee -a out/case_studies/timing_mac.txt
