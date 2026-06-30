# Deploying the DSA Reasoning Coach on Modal (free always-on, scales to zero)

This is the **free always-on** path: Modal gives a real GPU container that scales to **zero**
when idle, so an idle demo costs $0 (fits the Starter plan's monthly free credits). You only burn
credits during the seconds someone is actually generating.

The adapter is already public at `MoistPotato/dsa-reasoning-coach-7b-lora`, so there's nothing to
push first — the image downloads the base model + adapter at build time.

> Alternative path: `DEPLOY.md` (HF ZeroGPU Space, $9/mo Pro). Pick one. These files (`app.py`) are
> for that path; `modal_app.py` is for this one.

---

## Step 1 — Install + authenticate Modal (local, one time)

```bash
pip install modal
modal setup      # opens a browser to link/create your Modal account (free Starter plan)
```

Modal's free Starter plan includes monthly compute credits — enough for a low-traffic portfolio
demo that's idle most of the time.

## Step 2 — (optional) Test it live before deploying

```bash
modal serve deploy/modal_app.py
```

This builds the image (first time: installs deps + downloads Qwen2.5-7B, several minutes), then
prints a temporary public URL. The URL is live **only while this command runs** — good for a quick
check. Open it, paste an example, confirm you get the 8-section format and **no** full code dump.
Ctrl-C to stop.

## Step 3 — Deploy (permanent URL)

```bash
modal deploy deploy/modal_app.py
```

Prints a permanent public URL like `https://<you>--dsa-reasoning-coach-ui.modal.run`. That's your
live website. It stays deployed; the container spins up on the first request and spins down
~2 min after the last (the `scaledown_window` in `modal_app.py`), so **idle = free**.

## Step 4 — Record the demo

Open the URL, run **2–3 examples** (e.g. Two Sum, Longest Substring, House Robber II), and screen-
record it for the README / portfolio GIF. After that you can just leave it deployed and idle — it
won't cost anything until someone hits it again.

---

## Notes / gotchas

- **Cold start:** first request after idle spins up a container and loads the 7B (~30–60s), then
  it's fast. Add a "first response takes ~30s to warm up" note in the UI if you like.
- **GPU choice:** `gpu="A10G"` (24GB) holds 7B in bf16 with room to spare and is cheaper than A100.
  `gpu="L4"` is even cheaper and also fits — swap it in `modal_app.py` if you want to stretch credits.
- **Weights baked into the image:** `_download_weights()` runs at build time so cold starts load
  from local disk instead of re-downloading 15GB each time. Rebuild happens automatically if you
  change the image definition.
- **No HF token needed:** Qwen2.5-7B-Instruct is open (not gated) and the adapter repo is public.
  If you ever make the adapter private, add a Modal secret and pass `token=` to the loaders.
- **Keeping it warm (optional, costs credits):** to avoid cold starts during active demoing, add
  `min_containers=1` to the `@app.function(...)` decorator. Remove it again to return to free idle.
- **Stop paying entirely:** `modal app stop dsa-reasoning-coach` tears the deployment down.
