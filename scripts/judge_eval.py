"""
Phase 3 evaluation for the DSA Reasoning Coach: LLM-as-judge.

Scores the BASE model vs the FINE-TUNED model on the 16 held-out test problems, using a strong
frontier model (Cerebras gpt-oss-120b) as the judge. Each candidate derivation is graded AGAINST
the gold reference derivation in test.jsonl, on a small rubric:

    format_adherence    0-2  all 8 sections present, correct order, "thinking not code" style
    insight_correctness 0-2  is the key insight / algorithm actually correct?
    complexity_correct  0-2  are BOTH time and space Big-O correct?
    answer_not_leaked   0-1  did it avoid dumping full runnable code? (1 = good, 0 = leaked)
                        ----
    total (max 7)

Inputs (download these from Google Drive first):
    data/eval/eval_base.json        [{title, problem, base_output}, ...]
    data/eval/eval_finetuned.json   [{title, problem, finetuned_output}, ...]
    data/processed/test.jsonl       gold reference derivations (matched by title)

Outputs:
    data/eval/scores.json           per-problem scores for both models
    prints a base-vs-finetune comparison table to the console

Run:
    python scripts/judge_eval.py
"""

import os
import re
import json
import time
import pathlib
import argparse

# ----------------------------- Config -----------------------------
JUDGE_MODEL   = "gpt-oss-120b"      # Cerebras free tier, strong reasoning (same model used for data gen)
TEST_FILE     = "data/processed/test.jsonl"
# Defaults match the original schema-prompt eval; override with --base/--finetuned/--out
# to judge the no-schema files (e.g. eval_*_noschema_v2.json).
BASE_FILE     = "data/eval/eval_base.json"
FINETUNE_FILE = "data/eval/eval_finetuned.json"
OUT_FILE      = "data/eval/scores.json"
SLEEP_SECONDS = 2.0
MAX_RETRIES   = 4

JUDGE_SYSTEM = (
    "You are a strict, fair grader of DSA teaching answers. You compare a candidate derivation "
    "against a known-correct reference and score it on a rubric. You only output JSON."
)

RUBRIC = (
    "Score the CANDIDATE on this rubric (integers only):\n"
    "- format_adherence (0-2): 2 = all 8 sections present in this exact order (Observations, "
    "Brute force, Bottleneck, Key insight, Pattern, Optimized approach, Complexity, Generalizable "
    "lesson); 1 = most present but some missing/out of order; 0 = format largely ignored.\n"
    "- insight_correctness (0-2): 2 = the key insight AND optimized approach are algorithmically "
    "correct and match the reference's idea; 1 = right general direction but flawed/muddled "
    "details; 0 = wrong algorithm.\n"
    "- complexity_correct (0-2): 2 = BOTH time and space Big-O are correct; 1 = one correct or "
    "slightly off; 0 = wrong or missing.\n"
    "- answer_not_leaked (0-1): 1 = explains with steps/pseudocode and does NOT dump full runnable "
    "code; 0 = leaks a full code solution.\n"
)


def load_key(env_name, file_name):
    key = os.environ.get(env_name)
    if not key and os.path.exists(file_name):
        key = pathlib.Path(file_name).read_text(encoding="utf-8").strip()
    return key


def make_judge():
    """Return a function call(system, user)->str backed by Cerebras."""
    from cerebras.cloud.sdk import Cerebras
    key = load_key("CEREBRAS_API_KEY", "cerebras_key.txt")
    if not key:
        raise SystemExit("No Cerebras key. Put it in cerebras_key.txt or set CEREBRAS_API_KEY.")
    client = Cerebras(api_key=key)

    def call(system, user):
        r = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0,          # deterministic grading
        )
        return r.choices[0].message.content

    return call


def build_judge_prompt(problem, reference, candidate):
    return (
        f"{RUBRIC}\n"
        "PROBLEM:\n" + problem.strip() + "\n\n"
        "REFERENCE (known-correct) DERIVATION:\n" + reference.strip() + "\n\n"
        "CANDIDATE DERIVATION (the one you must grade):\n" + candidate.strip() + "\n\n"
        "Respond with ONLY this JSON object and nothing else:\n"
        '{"format_adherence": <int>, "insight_correctness": <int>, '
        '"complexity_correct": <int>, "answer_not_leaked": <int>, '
        '"justification": "<one sentence>"}'
    )


def parse_scores(text):
    """Pull the JSON object out of the judge's reply."""
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def load_references():
    refs = {}
    for line in pathlib.Path(TEST_FILE).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            refs[row["title"]] = row["derivation"]
    return refs


def judge_file(call, refs, results, output_key, label):
    """Score every candidate in one eval file. Returns list of per-problem score dicts."""
    scored = []
    for i, row in enumerate(results):
        title = row["title"]
        candidate = row.get(output_key, "")
        reference = refs.get(title)
        if reference is None:
            print(f"  [{label}] {i} {title}: no reference found, skipping")
            continue

        prompt = build_judge_prompt(row["problem"], reference, candidate)
        scores = None
        for attempt in range(MAX_RETRIES):
            try:
                scores = parse_scores(call(JUDGE_SYSTEM, prompt))
                if scores:
                    break
            except Exception as e:
                wait = SLEEP_SECONDS * (attempt + 2)
                print(f"    error ({str(e)[:100]}); retry in {wait:.0f}s")
                time.sleep(wait)

        if not scores:
            print(f"  [{label}] {i} {title}: FAILED to score")
            continue

        scores["total"] = (scores.get("format_adherence", 0)
                           + scores.get("insight_correctness", 0)
                           + scores.get("complexity_correct", 0)
                           + scores.get("answer_not_leaked", 0))
        scored.append({"title": title, **scores})
        print(f"  [{label}] {i} {title}: total {scores['total']}/7")
        time.sleep(SLEEP_SECONDS)
    return scored


def averages(scored):
    keys = ["format_adherence", "insight_correctness", "complexity_correct",
            "answer_not_leaked", "total"]
    n = len(scored) or 1
    return {k: sum(s.get(k, 0) for s in scored) / n for k in keys}


def print_table(base_avg, ft_avg):
    rows = [
        ("Format adherence (/2)",    "format_adherence"),
        ("Insight correctness (/2)", "insight_correctness"),
        ("Complexity correct (/2)",  "complexity_correct"),
        ("Answer not leaked (/1)",   "answer_not_leaked"),
        ("TOTAL (/7)",               "total"),
    ]
    print("\n" + "=" * 64)
    print(f"{'Criterion':<28}{'Base':>10}{'Fine-tuned':>14}{'Δ':>10}")
    print("-" * 64)
    for label, key in rows:
        b, f = base_avg[key], ft_avg[key]
        print(f"{label:<28}{b:>10.2f}{f:>14.2f}{f - b:>+10.2f}")
    print("=" * 64)


def main():
    ap = argparse.ArgumentParser(description="LLM-as-judge: base vs fine-tuned on the 16 test problems.")
    ap.add_argument("--base",      default=BASE_FILE,     help="base-model eval json")
    ap.add_argument("--finetuned", default=FINETUNE_FILE, help="fine-tuned eval json")
    ap.add_argument("--out",       default=OUT_FILE,      help="output scores json")
    args = ap.parse_args()

    call = make_judge()
    refs = load_references()
    base = json.loads(pathlib.Path(args.base).read_text(encoding="utf-8"))
    finetuned = json.loads(pathlib.Path(args.finetuned).read_text(encoding="utf-8"))

    print(f"Judging {len(base)} base + {len(finetuned)} fine-tuned outputs with {JUDGE_MODEL}\n")
    print("BASE model:")
    base_scored = judge_file(call, refs, base, "base_output", "base")
    print("\nFINE-TUNED model:")
    ft_scored = judge_file(call, refs, finetuned, "finetuned_output", "ft")

    base_avg = averages(base_scored)
    ft_avg = averages(ft_scored)

    pathlib.Path(args.out).write_text(json.dumps({
        "base_scored": base_scored, "base_avg": base_avg,
        "finetuned_scored": ft_scored, "finetuned_avg": ft_avg,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print_table(base_avg, ft_avg)
    print(f"\nPer-problem scores saved -> {args.out}")


if __name__ == "__main__":
    main()
