#!/usr/bin/env bash
# 본 제작 전 스택 실측(LLM 과정 기본값: vLLM 0.32.0 serve venv + HF 학습 스택 train venv, Qwen/Qwen3-0.6B)
# — Pod의 컨테이너 디스크(/root/stackcheck)에서만 수행한다.
# 공유 Network Volume(/workspace)은 촬영 화면을 깨끗하게 두기 위해 건드리지 않는다.
# 실행: tools/pod.sh B 'mkdir -p /root/stackcheck && cat > /root/stackcheck/run.sh' < tools/stackcheck.sh
#       tools/pod.sh B 'nohup bash /root/stackcheck/run.sh > /root/stackcheck/run.log 2>&1 &'
# 회수: tools/pod_get.sh B /root/stackcheck/run.log verification/stackcheck-<날짜>/  (logs/ 폴더도 같은 방법)
# Pod B는 .env.local의 POD_B_* 줄 주석을 풀어야 쓸 수 있다(Pod가 하나면 B 대신 A — 제작에 쓰지 않는 시간에).
# 버전 고정값은 environment/setup.sh(단일 원본)와 같게 둔다. 다른 과정이면 그 고정값과 STEP 3의 동작 확인 코드만 바꾼다.
# 끝나면 /root/stackcheck 를 지워 디스크를 돌려준다(약 46GB).
set -u
BASE=/root/stackcheck
export UV_CACHE_DIR=$BASE/uv-cache HF_HOME=$BASE/hf-cache
# JupyterLab 터미널과 같은 조건을 재현(이미지가 이 값을 켜 둔다)
export HF_HUB_ENABLE_HF_TRANSFER=1 HF_XET_HIGH_PERFORMANCE=1
mkdir -p "$BASE/logs"
log(){ echo "[$(date -u +%H:%M:%S)] $*"; }
T0=$(date +%s)
log "uv $(uv --version 2>&1) | driver $(nvidia-smi --query-gpu=driver_version --format=csv,noheader)"

log "STEP 1 serve venv (vllm[bench]==0.32.0)"
uv venv "$BASE/venvs/serve" --python 3.12 --seed 2>&1 | tail -1
echo "serve python -> $(readlink -f "$BASE/venvs/serve/bin/python")"
s=$(date +%s)
uv pip install --python "$BASE/venvs/serve/bin/python" "vllm[bench]==0.32.0" --torch-backend=auto \
  > "$BASE/logs/serve_install.log" 2>&1
log "serve install rc=$? in $(( $(date +%s)-s ))s"; tail -3 "$BASE/logs/serve_install.log"
"$BASE/venvs/serve/bin/python" - <<'EOF' 2>&1 | grep -v -i warn
import importlib
for m in ["vllm","torch","transformers","fastapi","openai","huggingface_hub","tokenizers","flashinfer"]:
    try:
        mod = importlib.import_module(m); print(" ", m, getattr(mod, "__version__", "?"))
    except Exception as e:
        print(" ", m, "IMPORT-FAIL", type(e).__name__, str(e)[:120])
import torch
print("  torch.cuda", torch.version.cuda, "available", torch.cuda.is_available())
EOF
s=$(date +%s)
"$BASE/venvs/serve/bin/vllm" download-kernels > "$BASE/logs/serve_kernels.log" 2>&1
log "download-kernels rc=$? in $(( $(date +%s)-s ))s"; tail -2 "$BASE/logs/serve_kernels.log"
for f in gpu-memory-utilization tool-call-parser reasoning-parser max-lora-rank host max-model-len generation-config; do
  echo "----- --help=$f"; "$BASE/venvs/serve/bin/vllm" serve --help="$f" 2>&1 | head -30
done > "$BASE/logs/vllm_flags.txt" 2>&1
log "vllm flag help captured ($(wc -l < "$BASE/logs/vllm_flags.txt") lines)"

log "STEP 2 train venv (HF stack)"
uv venv "$BASE/venvs/train" --python 3.12 --seed 2>&1 | tail -1
s=$(date +%s)
uv pip install --python "$BASE/venvs/train/bin/python" torch==2.14.1 transformers==5.21.0 peft==0.21.2 trl==1.16.0 \
  accelerate==1.15.0 datasets==5.1.0 bitsandbytes==0.50.2 "fastapi[standard]==0.162.0" uvicorn==0.54.0 \
  openai==3.40.0 ipykernel==7.4.0 --torch-backend=auto > "$BASE/logs/train_install.log" 2>&1
log "train install rc=$? in $(( $(date +%s)-s ))s"; tail -3 "$BASE/logs/train_install.log"

log "STEP 3 transformers v5 / TRL / bnb behavior (Qwen/Qwen3-0.6B)"
"$BASE/venvs/train/bin/python" - <<'EOF' 2>&1 | grep -v -i "warn"
import inspect, torch, transformers, trl, peft, bitsandbytes as bnb, huggingface_hub as hh
from transformers import AutoTokenizer, AutoModelForCausalLM
from trl import SFTConfig, SFTTrainer
print("  versions transformers", transformers.__version__, "trl", trl.__version__, "peft", peft.__version__,
      "bnb", bnb.__version__, "torch", torch.__version__, "cuda", torch.version.cuda, torch.cuda.is_available(), "hub", hh.__version__)
t = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B")
x = t.apply_chat_template([{"role": "user", "content": "안녕"}], add_generation_prompt=True, return_tensors="pt")
print("  apply_chat_template ->", type(x).__name__, list(x.keys()) if hasattr(x, "keys") else None)
m = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-0.6B", dtype=torch.bfloat16, device_map="cuda")
seen = {}
def keep(mod, a, o):   # 관찰용 hook은 None을 반환해야 한다(값을 반환하면 그 값이 레이어 출력을 대체한다)
    seen.setdefault("o", (type(o).__name__, tuple(getattr(o, "shape", ()))))
h = m.model.layers[0].register_forward_hook(keep)
out = m(**x.to(m.device), output_attentions=True); h.remove()
print("  layer hook output ->", seen.get("o"))
att = out.attentions
print("  attn_impl", getattr(m.config, "_attn_implementation", "?"), "| attentions ->",
      None if att is None else [None if a is None else tuple(a.shape) for a in att[:2]])
p = inspect.signature(SFTConfig).parameters
print("  SFTConfig max_length", "max_length" in p, "| max_seq_length", "max_seq_length" in p,
      "| SFTTrainer(quantization_config)", "quantization_config" in inspect.signature(SFTTrainer.__init__).parameters)
from bitsandbytes.functional import quantize_4bit
q, s = quantize_4bit(torch.randn(256, 256, device="cuda", dtype=torch.bfloat16), quant_type="nf4")
print("  nf4 quantize ok", tuple(q.shape), q.dtype)
g = m.generate(**x.to(m.device), max_new_tokens=16)
print("  generate ok, new tokens", g.shape[-1] - x["input_ids"].shape[-1])
print("  peak VRAM GiB", round(torch.cuda.max_memory_allocated() / 2**30, 2))
EOF

log "STEP 4 sizes / misc"
du -sh "$BASE"/venvs/* "$BASE/uv-cache" "$BASE/hf-cache" 2>/dev/null
echo "runpodctl: $(runpodctl version 2>&1 | tail -1)"; runpodctl --help 2>&1 | sed -n '1,25p'
log "DONE total $(( $(date +%s)-T0 ))s"
