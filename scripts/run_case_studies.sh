#!/bin/sh
# Real known-bad case studies, quick mode, one at a time. Inputs come from scripts/build_case_studies.py.
#   CASE_INPUTS=/path/to/inputs sh scripts/run_case_studies.sh
cd "$(dirname "$0")/.."
I=${CASE_INPUTS:-$HOME/.cache/touchstone/case_studies/inputs}
PY=${PY:-.venv/bin/python}
export PYTHONPATH=$PWD CASE_INPUTS=$I
mkdir -p out/case_studies
git rev-parse HEAD > out/case_studies/ENGINE_COMMIT
run() { n=$1; shift; s=$(date +%s); $PY -m touchstone.cli appraise "$@" --quick --out out/case_studies/$n > out/case_studies/$n.stdout 2>&1; echo "$n exit=$? $(($(date +%s)-s))s" | tee -a out/case_studies/timing.txt; }
run math_train_quick $I/math_train.jsonl --kind dataset --suite $I/math_test_suite.jsonl
run code_alpaca_quick $I/code_alpaca_20k.json --kind dataset --suite $I/humaneval_suite.jsonl
run mathinstruct_quick $I/mathinstruct.jsonl --kind dataset --suite $I/math_test_suite.jsonl
run demo_good_quick examples/demo/good_word_problems.jsonl --kind dataset
run demo_env_quick examples/demo/gameable_env --kind env
run h5_orca_quick examples/h5/gsm/orca_math.jsonl --kind dataset --suite examples/h5/gsm/suite.jsonl
$PY scripts/case_full_suite_overlap.py > out/case_studies/math_full_suite_overlap.stdout 2>&1; echo "full_suite_overlap exit=$?" | tee -a out/case_studies/timing.txt
