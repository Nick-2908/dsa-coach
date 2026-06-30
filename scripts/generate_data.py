"""
Phase 1 data generator for the DSA Reasoning Coach.

Reads the curated problem list, uses the hand-written gold examples as few-shot style anchors,
and asks a FREE LLM to produce a (problem statement, derivation) pair for each problem.
Output is appended to data/raw/generated.jsonl, one JSON object per line. Resume-safe: re-running
skips problems already generated, so you can switch provider/model and just continue.

Supports three free providers -- set PROVIDER below:
    groq     : pip install groq               key https://console.groq.com/keys   -> groq_key.txt
    gemini   : pip install google-genai       key https://aistudio.google.com/apikey -> gemini_key.txt
    cerebras : pip install cerebras-cloud-sdk  key https://cloud.cerebras.ai        -> cerebras_key.txt
               (free tier, high limits; runs llama-3.3-70b at full quality)

Run:
    python scripts/generate_data.py
"""

import os
import re
import json
import time
import glob
import pathlib

# ----------------------------- Config -----------------------------
PROVIDER       = "cerebras"                   # "groq" | "gemini" | "cerebras"
GROQ_MODEL     = "llama-3.1-8b-instant"       # higher daily quota; alt (better quality): "llama-3.3-70b-versatile"
GEMINI_MODEL   = "gemini-2.5-flash"           # note: free tier here was only ~20 req/day
CEREBRAS_MODEL = "gpt-oss-120b"              # free tier; strong 120B reasoning. alt: "zai-glm-4.7"

GOLD_DIR      = "data/gold"
PROBLEM_FILE  = "data/problem_list.json"
OUT_FILE      = "data/raw/generated.jsonl"
MAX_FEWSHOT   = 5                            # gold examples per prompt (more = richer imitation)
SLEEP_SECONDS = 2.5                          # stay under the rate limit
MAX_RETRIES   = 4

SYSTEM_PROMPT = (
    "You are a DSA Reasoning Coach. Given a programming problem, you teach the learner HOW to "
    "derive the optimal solution -- the thought process, not just the answer. Always respond in "
    "the exact section format requested. Explain the approach as steps/pseudocode; do NOT write "
    "the full final code."
)


def load_key(env_name, file_name):
    key = os.environ.get(env_name)
    if not key and os.path.exists(file_name):
        key = pathlib.Path(file_name).read_text(encoding="utf-8").strip()
    return key


# ------------------------- Gold few-shot --------------------------
def parse_gold(text):
    """Split a gold .md file into (problem_statement, derivation)."""
    inp = text.index("## INPUT")
    out = text.index("## OUTPUT")
    problem    = text[inp:out].split("\n", 1)[1].strip()
    derivation = text[out:].split("\n", 1)[1].strip()
    return problem, derivation

def load_gold():
    pairs = []
    for path in sorted(glob.glob(os.path.join(GOLD_DIR, "*.md"))):
        pairs.append(parse_gold(pathlib.Path(path).read_text(encoding="utf-8")))
    if not pairs:
        raise SystemExit(f"No gold examples found in {GOLD_DIR}")
    return pairs[:MAX_FEWSHOT]

def build_prompt(gold, title, pattern):
    parts = ["Here are examples of the EXACT style and format to follow:\n"]
    for problem, derivation in gold:
        parts.append(f"### PROBLEM\n{problem}\n### DERIVATION\n{derivation}\n\n---\n")
    parts.append(
        f'Now do the same for this well-known problem: "{title}" (pattern: {pattern}).\n\n'
        "REQUIREMENTS for the derivation:\n"
        "- Write for a beginner who does NOT already know the solution; each step must feel motivated.\n"
        "- Every section must EXPLAIN THE REASONING in 2-4 full sentences -- never a bare label or "
        "a single terse line.\n"
        "- 'Bottleneck' must name the SPECIFIC wasted work in the brute force (not just 'it is slow').\n"
        "- 'Key insight' must clearly explain the leap from brute force to optimal AND why it works.\n"
        "- 'Pattern' must end with a recognition cue of the form 'when you see X, reach for Y'.\n"
        "- 'Optimized approach' = numbered steps / pseudocode only. Do NOT write full runnable code.\n"
        "- State BOTH time and space complexity with Big-O.\n\n"
        "First write the problem statement IN YOUR OWN WORDS (do not copy any source verbatim), "
        "then the full derivation. Output EXACTLY this structure and nothing else:\n\n"
        "### PROBLEM\n<your statement>\n### DERIVATION\n## Observations\n- ...\n"
        "(then Brute force, Bottleneck, Key insight, Pattern, Optimized approach, Complexity, "
        "Generalizable lesson -- all sections, in order)\n"
    )
    return "\n".join(parts)

# --------------------------- Generation ---------------------------
def make_caller():
    """Return a function call(prompt)->str for the selected provider."""
    if PROVIDER == "groq":
        from groq import Groq
        key = load_key("GROQ_API_KEY", "groq_key.txt")
        if not key:
            raise SystemExit("No Groq key. Put it in groq_key.txt or set GROQ_API_KEY.")
        client = Groq(api_key=key)
        def call(prompt):
            r = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": prompt}],
                temperature=0.6,
            )
            return r.choices[0].message.content
        return call

    elif PROVIDER == "cerebras":
        from cerebras.cloud.sdk import Cerebras
        key = load_key("CEREBRAS_API_KEY", "cerebras_key.txt")
        if not key:
            raise SystemExit("No Cerebras key. Put it in cerebras_key.txt or set CEREBRAS_API_KEY.")
        client = Cerebras(api_key=key)
        def call(prompt):
            r = client.chat.completions.create(
                model=CEREBRAS_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": prompt}],
                temperature=0.6,
            )
            return r.choices[0].message.content
        return call

    elif PROVIDER == "gemini":
        from google import genai
        from google.genai import types
        key = load_key("GEMINI_API_KEY", "gemini_key.txt")
        if not key:
            raise SystemExit("No Gemini key. Put it in gemini_key.txt or set GEMINI_API_KEY.")
        client = genai.Client(api_key=key)
        cfg = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
        def call(prompt):
            return client.models.generate_content(
                model=GEMINI_MODEL, contents=prompt, config=cfg).text
        return call

    raise SystemExit(f"Unknown PROVIDER: {PROVIDER}")

def split_output(text):
    text = (text or "").strip()
    m = re.search(r"###\s*DERIVATION", text)
    if not m:
        return None, None
    problem = re.sub(r"^###\s*PROBLEM\s*", "", text[:m.start()].strip(), flags=re.I).strip()
    derivation = text[m.end():].strip()
    return problem, derivation

def already_done():
    done = set()
    if os.path.exists(OUT_FILE):
        for line in pathlib.Path(OUT_FILE).read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["title"])
    return done

def main():
    call = make_caller()
    gold = load_gold()
    problems = json.loads(pathlib.Path(PROBLEM_FILE).read_text(encoding="utf-8"))
    done = already_done()
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    print(f"Provider: {PROVIDER} | already have {len(done)} examples\n")
    total = sum(len(v) for v in problems.values())
    n = 0
    with open(OUT_FILE, "a", encoding="utf-8") as f:
        for pattern, titles in problems.items():
            for title in titles:
                n += 1
                if title in done:
                    print(f"[{n}/{total}] skip (done): {title}")
                    continue

                prompt = build_prompt(gold, title, pattern)
                text = None
                for attempt in range(MAX_RETRIES):
                    try:
                        text = call(prompt)
                        break
                    except Exception as e:
                        wait = SLEEP_SECONDS * (attempt + 2)
                        print(f"    error ({str(e)[:120]}); retry in {wait:.0f}s")
                        time.sleep(wait)

                if not text:
                    print(f"[{n}/{total}] FAILED: {title}")
                    continue

                problem, derivation = split_output(text)
                if not problem or not derivation:
                    print(f"[{n}/{total}] malformed, skipping: {title}")
                    continue

                f.write(json.dumps({
                    "pattern": pattern, "title": title,
                    "problem": problem, "derivation": derivation,
                }, ensure_ascii=False) + "\n")
                f.flush()
                print(f"[{n}/{total}] ok: {title}")
                time.sleep(SLEEP_SECONDS)

    print(f"\nDone. Output -> {OUT_FILE}")

if __name__ == "__main__":
    main()
