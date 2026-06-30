"""
Phase 1 quality filter for the DSA Reasoning Coach.

Reads the raw generated examples, rejects bad ones, and writes a clean dataset. An example is
KEPT only if it: has all required schema sections, is long enough, states a complexity, and does
NOT leak full code (our model must teach the approach, never hand over the solution).

    python scripts/filter_data.py

Outputs:
    data/processed/clean.jsonl      -- the good examples
    data/processed/rejected.jsonl   -- rejects, each tagged with the reasons it failed
"""

import os
import re
import json
import pathlib
from collections import Counter

IN_FILE     = "data/raw/generated.jsonl"
CLEAN_FILE  = "data/processed/clean.jsonl"
REJECT_FILE = "data/processed/rejected.jsonl"

REQUIRED_SECTIONS = [
    "Observations", "Brute force", "Bottleneck", "Key insight",
    "Pattern", "Optimized approach", "Complexity", "Generalizable lesson",
]

# Signs that the model wrote real, runnable code instead of pseudocode steps.
LEAK_PATTERNS = [
    r"```",                              # a code fence
    r"\bdef\s+\w+\s*\(",                 # python function def
    r"\bclass\s+\w+\s*[:\(]",            # class definition
    r"\bpublic\s+(static\s+)?\w+\s+\w+\s*\(",   # java-style method
    r"\bfunction\s+\w+\s*\(",            # js function
    r"#include",                         # c/c++
    r"System\.out|console\.log|printf\s*\(",    # print statements
]

MIN_PROBLEM_LEN    = 30
MIN_DERIVATION_LEN = 300


def find_issues(rec):
    issues = []
    problem = (rec.get("problem") or "").strip()
    deriv   = (rec.get("derivation") or "").strip()
    low     = deriv.lower()

    if len(problem) < MIN_PROBLEM_LEN:
        issues.append("problem_too_short")
    if len(deriv) < MIN_DERIVATION_LEN:
        issues.append("derivation_too_short")

    for sec in REQUIRED_SECTIONS:
        if ("## " + sec.lower()) not in low:
            issues.append(f"missing_section:{sec}")

    for pat in LEAK_PATTERNS:
        if re.search(pat, deriv, flags=re.I):
            issues.append("code_leak")
            break

    if "o(" not in re.sub(r"[*_`]", "", low):   # strip markdown emphasis (e.g. *O*(n)) first
        issues.append("no_complexity")

    return issues


def main():
    if not os.path.exists(IN_FILE):
        raise SystemExit(f"No input at {IN_FILE} -- run generate_data.py first.")
    os.makedirs(os.path.dirname(CLEAN_FILE), exist_ok=True)

    records = [json.loads(l) for l in pathlib.Path(IN_FILE).read_text(encoding="utf-8").splitlines() if l.strip()]

    kept, rejected = [], []
    seen_titles = set()
    reason_counts = Counter()

    for rec in records:
        title = rec.get("title", "")
        if title in seen_titles:                 # duplicate title -> drop
            rec["_reasons"] = ["duplicate_title"]
            rejected.append(rec)
            reason_counts["duplicate_title"] += 1
            continue
        seen_titles.add(title)

        issues = find_issues(rec)
        if issues:
            rec["_reasons"] = issues
            rejected.append(rec)
            for i in issues:
                reason_counts[i.split(":")[0]] += 1
        else:
            kept.append(rec)

    with open(CLEAN_FILE, "w", encoding="utf-8") as f:
        for rec in kept:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with open(REJECT_FILE, "w", encoding="utf-8") as f:
        for rec in rejected:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---- report ----
    print(f"\nRead:     {len(records)}")
    print(f"Kept:     {len(kept)}  -> {CLEAN_FILE}")
    print(f"Rejected: {len(rejected)}  -> {REJECT_FILE}")
    if reason_counts:
        print("\nRejection reasons:")
        for reason, count in reason_counts.most_common():
            print(f"  {count:3d}  {reason}")
    print("\nPattern coverage (clean set):")
    for pat, count in Counter(r["pattern"] for r in kept).most_common():
        print(f"  {count:3d}  {pat}")


if __name__ == "__main__":
    main()
