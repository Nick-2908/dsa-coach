"""
DSA Reasoning Coach — Modal deployment (free always-on, scales to zero).

Serves Qwen2.5-7B-Instruct (bf16) + the distilled LoRA adapter behind a custom, hand-built
chat UI (no Gradio — a single-page FastAPI app that streams tokens over SSE-style chunks and
renders the 8-section markdown client-side). Modal scales the GPU container to zero when idle,
so an idle demo costs $0. The first request after idle pays a cold start (container spins up +
model loads, ~15-60s); subsequent requests stream fast.

Like the HF Space version, this uses a MINIMAL system prompt — the 8-section teaching format and
the no-code-leak behavior come from the fine-tune, not the prompt. That internalized behavior is
the whole point of the project (see the eval table in README.md).

Deploy:   modal deploy deploy/modal_app.py
Dev/test: modal serve  deploy/modal_app.py     (temporary URL, live while the command runs)
"""

import modal

# --- config -------------------------------------------------------------------
APP_NAME       = "dsa-reasoning-coach"
BASE_MODEL     = "Qwen/Qwen2.5-7B-Instruct"
ADAPTER_REPO   = "MoistPotato/dsa-reasoning-coach-7b-lora"
MINIMAL_PROMPT = "You are a helpful DSA tutor."
MAX_NEW_TOKENS = 1024

EXAMPLES = [
    "You are given an array of integers and a target. Return the indices of the two numbers "
    "that add up to the target.",
    "Given a string, find the length of the longest substring without repeating characters.",
    "Houses are arranged in a circle; you cannot rob two adjacent houses. Return the maximum "
    "amount of money you can rob.",
    "Given the heights of bars in a histogram, find the area of the largest rectangle.",
]


# --- image: bake the weights in at build time so cold starts load from local disk ---
def _download_weights():
    from huggingface_hub import snapshot_download

    snapshot_download(BASE_MODEL)
    snapshot_download(ADAPTER_REPO)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch",
        "transformers>=4.45.0",
        "peft>=0.13.0",
        "accelerate>=0.34.0",
        "sentencepiece",
        "huggingface_hub==0.25.2",
        "fastapi[standard]==0.115.0",
        "starlette==0.38.6",
    )
    # download base model + adapter into the image layer (Modal caches it)
    .run_function(_download_weights)
)

app = modal.App(APP_NAME, image=image)


# --- the single-page chat UI (inlined: HTML + CSS + JS, no static hosting needed) ---
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>DSA Reasoning Coach</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.0/marked.min.js"></script>
<style>
  :root{
    --bg:#ffffff; --text:#1c1c1e; --muted:#8a8a8f; --border:#ececec;
    --accent:#1c1c1e; --user:#f4f4f5; --code:#f6f6f7;
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    margin:0; background:var(--bg); color:var(--text);
    font-family:'Inter',system-ui,sans-serif; -webkit-font-smoothing:antialiased;
    display:flex; flex-direction:column; height:100vh;
  }
  header{text-align:center; padding:28px 16px 18px}
  header h1{margin:0; font-size:18px; font-weight:600; letter-spacing:-.2px}
  header p{margin:5px 0 0; color:var(--muted); font-size:13px}

  #chat{flex:1; overflow-y:auto; width:100%; max-width:680px; margin:0 auto; padding:8px 20px 24px}
  .msg{margin:0 0 26px}
  .user{display:flex; justify-content:flex-end}
  .user .bubble{
    background:var(--user); border-radius:16px; padding:11px 15px; max-width:82%;
    font-size:14.5px; line-height:1.55;
  }
  .bot .bubble{font-size:14.5px; line-height:1.72}
  .bot .bubble h2{font-size:14.5px; font-weight:600; margin:22px 0 7px}
  .bot .bubble h2:first-child{margin-top:0}
  .bot .bubble ul{margin:7px 0; padding-left:20px}
  .bot .bubble li{margin:4px 0}
  .bot .bubble p{margin:8px 0}
  .bot .bubble code{background:var(--code); padding:2px 6px; border-radius:5px; font-family:'JetBrains Mono',monospace; font-size:12.5px}
  .bot .bubble pre{background:var(--code); padding:12px 14px; border-radius:10px; overflow-x:auto}
  .bot .bubble pre code{background:none; padding:0}
  .cursor{display:inline-block; width:7px; height:15px; background:var(--muted); animation:blink 1.1s steps(2) infinite; vertical-align:text-bottom; margin-left:1px; border-radius:1px}
  @keyframes blink{50%{opacity:0}}

  .empty{margin-top:6vh; text-align:center}
  .empty p{color:var(--muted); font-size:14px; line-height:1.6; margin:0 0 22px}
  .suggest{display:flex; flex-direction:column; gap:9px; max-width:520px; margin:0 auto; text-align:left}
  .sug{
    border:1px solid var(--border); border-radius:12px; padding:12px 15px; font-size:13.5px;
    color:var(--text); cursor:pointer; transition:.15s; background:var(--bg);
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
  }
  .sug:hover{background:var(--user); border-color:#dcdcdc}

  footer{padding:10px 20px 22px}
  .inputrow{
    max-width:680px; margin:0 auto; display:flex; gap:8px; align-items:flex-end;
    border:1px solid var(--border); border-radius:18px; padding:7px 7px 7px 16px;
    transition:.15s; box-shadow:0 1px 2px rgba(0,0,0,.03);
  }
  .inputrow:focus-within{border-color:#cfcfcf; box-shadow:0 2px 10px rgba(0,0,0,.05)}
  textarea{
    flex:1; resize:none; background:transparent; color:var(--text); border:none;
    padding:8px 0; font-family:inherit; font-size:14.5px; line-height:1.5; max-height:170px; outline:none;
  }
  textarea::placeholder{color:var(--muted)}
  button#ask{
    background:var(--accent); color:#fff; border:none; border-radius:12px;
    width:36px; height:36px; flex:0 0 36px; cursor:pointer; transition:.15s;
    display:flex; align-items:center; justify-content:center; font-size:17px;
  }
  button#ask:hover{opacity:.85}
  button#ask:disabled{opacity:.35; cursor:not-allowed}
  .hint{color:var(--muted); font-size:11.5px; text-align:center; margin:9px 0 0}
</style>
</head>
<body>
  <header>
    <h1>DSA Reasoning Coach</h1>
    <p>Learn to <b>derive</b> the solution — not memorize the code.</p>
  </header>

  <div id="chat">
    <div class="empty" id="empty">
      <p>Paste a problem. It walks you from observations to the key insight and the pattern —<br/>
         without dumping the full solution.</p>
      <div class="suggest" id="suggest"></div>
    </div>
  </div>

  <footer>
    <div class="inputrow">
      <textarea id="box" rows="1" placeholder="Paste a problem statement…"></textarea>
      <button id="ask" title="Send">↑</button>
    </div>
    <div class="hint">First answer after idle can take ~30–60s (GPU cold start), then it streams.</div>
  </footer>

<script>
const EXAMPLES = __EXAMPLES__;
const chat = document.getElementById('chat');
const box  = document.getElementById('box');
const ask  = document.getElementById('ask');
const empty= document.getElementById('empty');
const suggest = document.getElementById('suggest');

EXAMPLES.forEach(ex => {
  const c = document.createElement('div');
  c.className = 'sug';
  c.textContent = ex.length > 64 ? ex.slice(0,61)+'…' : ex;
  c.title = ex;
  c.onclick = () => { box.value = ex; box.focus(); autoGrow(); };
  suggest.appendChild(c);
});

function autoGrow(){ box.style.height='auto'; box.style.height=Math.min(box.scrollHeight,170)+'px'; }
box.addEventListener('input', autoGrow);
box.addEventListener('keydown', e => {
  if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); }
});
ask.onclick = send;

function addMsg(role, html){
  const m = document.createElement('div');
  m.className = 'msg ' + role;
  m.innerHTML = '<div class="bubble"></div>';
  m.querySelector('.bubble').innerHTML = html;
  chat.appendChild(m);
  chat.scrollTop = chat.scrollHeight;
  return m.querySelector('.bubble');
}

async function send(){
  const problem = box.value.trim();
  if(!problem) return;
  if(empty) empty.style.display='none';
  ask.disabled = true; box.disabled = true;

  addMsg('user', escapeHtml(problem));
  box.value=''; autoGrow();
  const bubble = addMsg('bot', '<span class="cursor"></span>');

  let full = '';
  try{
    const resp = await fetch('/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({problem})
    });
    if(!resp.ok || !resp.body) throw new Error('HTTP '+resp.status);
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    while(true){
      const {done, value} = await reader.read();
      if(done) break;
      full += dec.decode(value, {stream:true});
      bubble.innerHTML = marked.parse(full) + '<span class="cursor"></span>';
      chat.scrollTop = chat.scrollHeight;
    }
    bubble.innerHTML = marked.parse(full);
  }catch(err){
    bubble.innerHTML = full ? marked.parse(full) : 'Something went wrong: '+escapeHtml(err.message);
  }finally{
    ask.disabled = false; box.disabled = false; box.focus();
  }
}

function escapeHtml(s){
  return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
</script>
</body>
</html>"""


@app.function(
    gpu="A10G",            # 24GB holds 7B bf16 easily; cheaper than A100. (L4 also works.)
    scaledown_window=120,  # stay warm 2 min after the last request, then spin down -> idle is free
    timeout=600,
)
@modal.concurrent(max_inputs=10)  # stream multiple users on one warm container
@modal.asgi_app()
def ui():
    """Built once per container start; the loaded model is reused for that container's life."""
    import json
    from threading import Thread

    import torch
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, StreamingResponse
    from pydantic import BaseModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

    from peft import PeftModel

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, torch_dtype=torch.bfloat16).to("cuda")
    model = PeftModel.from_pretrained(model, ADAPTER_REPO)
    model = model.merge_and_unload()  # fold LoRA into base weights -> faster per-token decode
    model.eval()

    page = INDEX_HTML.replace("__EXAMPLES__", json.dumps(EXAMPLES))

    web = FastAPI()

    class ChatReq(BaseModel):
        problem: str

    @web.get("/")
    def index():
        return HTMLResponse(page)

    @web.post("/chat")
    def chat(req: ChatReq):
        def generate():
            messages = [
                {"role": "system", "content": MINIMAL_PROMPT},
                {"role": "user",   "content": req.problem},
            ]
            inputs = tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                return_tensors="pt", return_dict=True,
            ).to("cuda")

            streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
            gen_kwargs = dict(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,        # greedy = deterministic, matches the eval
                temperature=None, top_p=None, top_k=None,  # unset sampling params (silences warnings)
                use_cache=True,
                streamer=streamer,
            )
            thread = Thread(target=model.generate, kwargs=gen_kwargs)
            thread.start()
            for token in streamer:
                yield token

        return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")

    return web
