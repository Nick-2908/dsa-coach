"""
Quick human-review viewer for the generated dataset.

    python scripts/inspect_data.py                 # 6 random examples
    python scripts/inspect_data.py 1 62 101        # specific line numbers (1-based)
    python scripts/inspect_data.py --file data/processed/clean.jsonl

Use this to judge whether the REASONING is actually correct -- the filter can't do that for you.
"""

import sys
import json
import random
import pathlib

DEFAULT_FILE = "data/processed/clean.jsonl"
SAMPLE_N = 6


def main():
    args = sys.argv[1:]
    path = DEFAULT_FILE
    if "--file" in args:
        i = args.index("--file")
        path = args[i + 1]
        del args[i:i + 2]

    lines = [l for l in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    records = [json.loads(l) for l in lines]

    if args:                                   # specific 1-based line numbers
        idxs = [int(a) - 1 for a in args]
    else:
        idxs = sorted(random.sample(range(len(records)), min(SAMPLE_N, len(records))))

    for i in idxs:
        if i < 0 or i >= len(records):
            print(f"\n(skipping out-of-range line {i + 1})")
            continue
        r = records[i]
        print("\n" + "=" * 78)
        print(f"# LINE {i + 1}/{len(records)}  |  pattern: {r.get('pattern')}  |  title: {r.get('title')}")
        print("=" * 78)
        print("\n--- PROBLEM ---\n" + (r.get("problem") or "").strip())
        print("\n--- DERIVATION ---\n" + (r.get("derivation") or "").strip())
    print()


if __name__ == "__main__":
    main()
