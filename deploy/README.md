---
title: DSA Reasoning Coach
emoji: "."
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: apache-2.0
suggested_hardware: zero-a10g
---

# DSA Reasoning Coach

A small, self-hosted LLM that teaches you how to **derive** a Data Structures & Algorithms
solution — observations, brute force, the bottleneck, the key insight, the pattern — instead of
handing you the answer. Distilled from a frontier model into a **Qwen2.5-7B** model with a LoRA
adapter you can run yourself.

## What makes it different

It's fine-tuned to do two things a base model won't reliably do **without being told**:
1. Answer in a fixed **8-section teaching format** (Observations → Brute force → Bottleneck →
   Key insight → Pattern → Optimized approach → Complexity → Generalizable lesson).
2. **Refuse to dump runnable code** — it teaches the thinking, not the solution.

Crucially, the demo uses only a *minimal* system prompt (`"You are a helpful DSA tutor."`). The
format and the no-code-leak behavior are **internalized by the fine-tune**, not injected via the
prompt. That's the headline result below.

## Evaluation (held-out 16 problems, no schema in the prompt)

LLM-as-judge (Cerebras `gpt-oss-120b`), greedy decoding. Base = stock Qwen2.5-7B-Instruct with the
same minimal prompt.

| Criterion | Base | Fine-tuned 7B | Δ |
|---|---|---|---|
| Format adherence (/2) | 0.00 | 1.94 | **+1.94** |
| Insight correctness (/2) | 1.56 | 1.56 | +0.00 |
| Complexity correct (/2) | 0.44 | 1.50 | **+1.06** |
| Answer not leaked (/1) | 0.00 | 1.00 | **+1.00** |
| **TOTAL (/7)** | **2.00** | **6.00** | **+4.00** |

With no schema in the prompt, the base model free-forms and dumps full code on every problem;
the fine-tune emits the teaching format and refuses code — a **3× total-score win**, while holding
**insight parity** (the 7B teacher explains the idea in words as correctly as the base does by
pasting code).

## How it was built

Distillation pipeline → QLoRA fine-tune (Unsloth, free Colab T4) → custom LLM-as-judge eval.
Key training trick: **prompt augmentation** (rotating full-schema / minimal / no system prompt
per example) so the behavior binds to the *task*, not the instruction text.

- Base model: `Qwen/Qwen2.5-7B-Instruct`
- Adapter: LoRA (r=16), 73 distilled training examples, 3 epochs
