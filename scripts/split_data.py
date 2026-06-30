"""
Split data/processed/clean.jsonl into train / val / held-out test.

Stratified by `pattern` so every pattern appears in train, and the test set is a
representative cross-section of patterns. Deterministic (fixed seed) so the split
is reproducible and the held-out test set never silently changes between runs.

Allocation priority per pattern: train first, then test, then val. This guarantees
thin patterns (e.g. tries=2) still land at least one example in train.

Usage:
    python scripts/split_data.py            # write splits
    python scripts/split_data.py --dry-run  # just print the planned counts
"""
import json
import random
import argparse
import collections
from pathlib import Path

SEED = 42
VAL_FRAC = 0.10
TEST_FRAC = 0.15

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "processed" / "clean.jsonl"
OUT_DIR = ROOT / "data" / "processed"


def load(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def stratified_split(rows):
    by_pattern = collections.defaultdict(list)
    for r in rows:
        by_pattern[r["pattern"]].append(r)

    rng = random.Random(SEED)
    train, val, test = [], [], []

    for pattern in sorted(by_pattern):
        items = by_pattern[pattern][:]
        rng.shuffle(items)
        n = len(items)

        # round, but never let val/test starve train of its only example
        n_test = round(n * TEST_FRAC)
        n_val = round(n * VAL_FRAC)
        n_test = min(n_test, max(0, n - 1))          # keep >=1 for train
        n_val = min(n_val, max(0, n - 1 - n_test))   # keep >=1 for train

        test.extend(items[:n_test])
        val.extend(items[n_test:n_test + n_val])
        train.extend(items[n_test + n_val:])

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def write(rows, path):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def summarize(name, rows):
    c = collections.Counter(r["pattern"] for r in rows)
    print(f"{name:6s} n={len(rows):3d}  " + " ".join(f"{p}:{n}" for p, n in c.most_common()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = load(SRC)
    train, val, test = stratified_split(rows)

    assert len(train) + len(val) + len(test) == len(rows)
    titles = [r["title"] for r in train + val + test]
    assert len(titles) == len(set(titles)), "title leaked across splits / duplicate"

    print(f"total {len(rows)}")
    summarize("train", train)
    summarize("val", val)
    summarize("test", test)

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return

    write(train, OUT_DIR / "train.jsonl")
    write(val, OUT_DIR / "val.jsonl")
    write(test, OUT_DIR / "test.jsonl")
    print(f"\nwrote -> {OUT_DIR/'train.jsonl'}, val.jsonl, test.jsonl")


if __name__ == "__main__":
    main()
