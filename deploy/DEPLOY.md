# Deploying the DSA Reasoning Coach (HF Gradio Space, ZeroGPU)

Two repos on Hugging Face:
1. a **model repo** holding the LoRA adapter (`lora_7b_v2`), and
2. a **Space** running `app.py` that loads base Qwen2.5-7B + the adapter.

Repo ids are pre-filled for HF user **MoistPotato**.

---

## Step 1 — Push the adapter to the Hub (run in Colab)

The adapter is on Drive at `/content/drive/MyDrive/dsa-coach/lora_7b_v2`. In a Colab cell:

```python
from huggingface_hub import login, HfApi, create_repo
login()  # paste a HF token with WRITE access (hf.co/settings/tokens)

REPO = "MoistPotato/dsa-reasoning-coach-7b-lora"
create_repo(REPO, repo_type="model", exist_ok=True)

HfApi().upload_folder(
    folder_path="/content/drive/MyDrive/dsa-coach/lora_7b_v2",
    repo_id=REPO,
    repo_type="model",
)
print("pushed adapter ->", REPO)
```

The adapter is small (tens of MB), so this is quick. Confirm at
`https://huggingface.co/MoistPotato/dsa-reasoning-coach-7b-lora` that
`adapter_model.safetensors` + `adapter_config.json` are there.

> Optional: paste the `## Evaluation` table from `README.md` into the model repo's README so the
> model card has the results (Phase 6 polish).

---

## Step 2 — Create the Space

1. Go to https://huggingface.co/new-space
2. Owner = you, name = `dsa-reasoning-coach`, SDK = **Gradio**, License = Apache-2.0.
3. Hardware = **ZeroGPU** (free; gives an on-demand A100). Create.

## Step 3 — (already done) adapter repo id

`app.py` already points at `MoistPotato/dsa-reasoning-coach-7b-lora`. Nothing to edit. If you ever
rename the adapter repo, override it without touching code via a Space **Variable**
`ADAPTER_REPO = <new repo id>` (Space → Settings → Variables and secrets).

## Step 4 — Upload the Space files

Upload these three files from `deploy/` to the root of the Space repo:
- `app.py`
- `requirements.txt`
- `README.md`  (its YAML frontmatter configures the Space — keep it at the top)

Easiest path (web): Space → **Files** → Add file → Upload files. Or via git:

```bash
git clone https://huggingface.co/spaces/MoistPotato/dsa-reasoning-coach
cp deploy/app.py deploy/requirements.txt deploy/README.md dsa-reasoning-coach/
cd dsa-reasoning-coach && git add . && git commit -m "DSA Reasoning Coach demo" && git push
```

## Step 5 — Watch it build

The Space builds (installs requirements, downloads base Qwen2.5-7B on first run — a few minutes),
then shows the chat UI. Test with an example problem; confirm it returns the 8-section format and
does **not** dump full code.

---

## Notes / gotchas

- **Qwen2.5-7B is a gated-free model** but downloads fine on Spaces. If you ever hit an auth error,
  add an `HF_TOKEN` secret to the Space.
- **ZeroGPU**: the GPU only exists inside the `@spaces.GPU`-decorated `respond()` function — that's
  why the model loads on CPU at startup and `.to("cuda")` happens per call. Don't move GPU calls to
  module scope.
- **bf16, not 4-bit**: ZeroGPU's A100 holds 7B in bf16 easily, which avoids bitsandbytes-on-ZeroGPU
  friction. If you ever target a smaller GPU, switch back to 4-bit load.
- First request after idle is slow (cold GPU allocation); subsequent ones are fast.
