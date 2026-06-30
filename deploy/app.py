"""
DSA Reasoning Coach — Gradio demo (Hugging Face ZeroGPU Space).

Loads Qwen2.5-7B-Instruct (bf16) + the distilled LoRA adapter and teaches the user how to
DERIVE a DSA solution using an 8-section format, WITHOUT dumping runnable code.

The demo deliberately uses a MINIMAL system prompt ("You are a helpful DSA tutor.") — the
8-section teaching format and the no-code-leak behavior come from the fine-tune, not the prompt.
That internalized behavior is the whole point of the project (see the eval table in the README).
"""

import os
from threading import Thread

import torch
import gradio as gr
import spaces
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from peft import PeftModel

# --- config -------------------------------------------------------------------
BASE_MODEL   = "Qwen/Qwen2.5-7B-Instruct"
# Override via a Space Variable named ADAPTER_REPO if you ever rename the repo (see DEPLOY.md).
ADAPTER_REPO = os.environ.get("ADAPTER_REPO", "MoistPotato/dsa-reasoning-coach-7b-lora")

MINIMAL_PROMPT = "You are a helpful DSA tutor."
MAX_NEW_TOKENS = 1024

# --- load once at startup (CPU; ZeroGPU grants the GPU inside @spaces.GPU) -----
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
)
model = PeftModel.from_pretrained(model, ADAPTER_REPO)
model.eval()


@spaces.GPU(duration=120)
def respond(problem, history):
    model.to("cuda")
    messages = [
        {"role": "system", "content": MINIMAL_PROMPT},
        {"role": "user",   "content": problem},
    ]
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    ).to("cuda")

    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    gen_kwargs = dict(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=False,        # greedy = deterministic, matches the eval
        use_cache=True,
        streamer=streamer,
    )
    thread = Thread(target=model.generate, kwargs=gen_kwargs)
    thread.start()

    partial = ""
    for token in streamer:
        partial += token
        yield partial


EXAMPLES = [
    "You are given an array of integers and a target. Return the indices of the two numbers "
    "that add up to the target.",
    "Given a string, find the length of the longest substring without repeating characters.",
    "Houses are arranged in a circle; you cannot rob two adjacent houses. Return the maximum "
    "amount of money you can rob.",
    "Given the heights of bars in a histogram, find the area of the largest rectangle.",
]

demo = gr.ChatInterface(
    fn=respond,
    type="messages",
    title="DSA Reasoning Coach",
    description=(
        "A 7B model distilled to **teach you how to derive** a DSA solution — observations, "
        "bottleneck, the key insight, the pattern — instead of handing you the code. "
        "Paste a problem statement. (It won't dump a full solution; that's by design.)"
    ),
    examples=EXAMPLES,
)

if __name__ == "__main__":
    demo.launch()
