#!/usr/bin/env bash
# 과정 공통 파이썬 환경 만들기 — Pod를 켤 때마다 한 번 실행한다(LLM 기본값 실측 약 1.5~2분).
# 학습자 위치: $COURSE_DIR/scripts/setup.sh  (환경 만들기 레슨에서 학습자가 직접 만든다. LLM 과정은 C02-L04)
# 제작용: tools/pod.sh A 'cat > /root/setup.sh' < environment/setup.sh && tools/pod.sh A 'bash /root/setup.sh'
#
# 버전 고정값의 단일 원본은 이 파일이다(아래 TRAIN_PKGS·SERVE_PKGS, LLM 과정 기본값: Qwen3 + vLLM 0.32.0).
#   다른 과정이면 패키지 목록과 VENV_SET만 바꾼다. 버전을 바꾸면 tools/stackcheck.sh의 같은 고정값도 함께 고친다.
#   docs/LESSON_GUIDE.md·README에는 Pod에서 확인한 값(lock 파일, 아래 마지막 출력)을 적는다.
#
# 바꿀 수 있는 값(실행할 때 환경변수로 넘기거나 아래 줄을 고친다 — init_course.py가 과정에 맞게 채운다):
#   VENVS                venv를 둘 곳(컨테이너 디스크). 다른 과정이 같은 Pod를 쓰면 /root/venvs/<과정>처럼 따로 둔다
#   KERNEL, KERNEL_LABEL train venv를 등록할 커널 이름 / Launcher에 보이는 이름
#   VENV_SET             만들 venv(쉼표로): train,serve(기본) / train(서빙 없는 과정) / serve
#   COURSE_DIR           학습자 작업 폴더(Network Volume 위)
#   LOCKDIR              설치된 버전 기록(lock)을 둘 곳 — 학습자 폴더 밖 숨김 폴더(File Browser에 안 보임)
# 이미 있는 venv가 아래 고정 목록과 다르면(다른 과정의 venv, 설치가 중간에 끊긴 venv) 아무것도 바꾸지 않고 멈춘다(exit 3).
#   남의 venv면 지우지 말고 VENVS를 바꿔 다시 실행하고, 혼자 쓰는 Pod의 반쯤 깔린 venv면 rm -rf <venv> 뒤 다시 실행한다.
#   FORCE_VENV=1 이면 다른 점을 알리기만 하고 그대로 쓴다.
#
# 왜 이렇게 나누나?
#  - venv(파이썬 패키지 묶음)는 수십 GB라서 컨테이너 디스크(/root)에 둔다. Stop하면 지워지므로 다시 만든다.
#  - 모델 파일은 /workspace/.cache/huggingface(HF_HOME)에 둔다. Stop해도 남아서 다시 받지 않는다.
#  - venv 두 개: train(학습·노트북·FastAPI) / serve(vLLM). vLLM이 torch·transformers 버전을 고정하기 때문.
set -euo pipefail

export UV_CACHE_DIR=/root/.cache/uv          # uv 캐시를 공유 볼륨이 아니라 컨테이너 디스크에
VENVS="${VENVS:-/root/venvs}"
KERNEL="${KERNEL:-train}"
KERNEL_LABEL="${KERNEL_LABEL:-Python (train)}"
VENV_SET="${VENV_SET:-train,serve}"
COURSE_DIR="${COURSE_DIR:-/workspace/llm-course}"
LOCKDIR="${LOCKDIR:-/workspace/.course-env/$(basename "$COURSE_DIR")}"
FORCE_VENV="${FORCE_VENV:-0}"

TRAIN_PKGS=(torch==2.14.1 transformers==5.21.0 peft==0.21.2 trl==1.16.0 accelerate==1.15.0
  datasets==5.1.0 bitsandbytes==0.50.2 "fastapi[standard]==0.162.0" uvicorn==0.54.0
  openai==3.40.0 ipykernel==7.4.0 matplotlib==3.10.7 pandas==2.3.3 jsonschema==4.25.1 pytest==8.4.2)
SERVE_PKGS=("vllm[bench]==0.32.0")

want() { case ",$VENV_SET," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }

# 이미 있는 venv에 고정 목록(이름==버전)이 모두 깔려 있는지 본다. 다르면 그 항목을 찍고 1을 돌려준다.
same_pins() {
  local py=$1 frz p name ver ver_re bad=0
  shift
  frz=$(uv pip freeze --python "$py" 2>/dev/null | tr '[:upper:]' '[:lower:]' | tr '_' '-') || frz=""
  for p in "$@"; do
    name=${p%%==*}; name=${name%%\[*}; ver=${p#*==}
    name=$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
    ver_re=$(printf '%s' "$ver" | sed 's/[.+]/\\&/g')
    if ! grep -Eq "^${name}==${ver_re}([+].*)?$" <<<"$frz"; then
      echo "  - $p (지금: $(grep -E "^${name}==" <<<"$frz" | head -1 || true))" >&2
      bad=1
    fi
  done
  return "$bad"
}

CREATED=""
make_venv() {   # $1 = venv 이름, 나머지 = 고정 목록
  local v=$1
  shift
  local py="$VENVS/$v/bin/python"
  if [ -x "$py" ]; then
    if same_pins "$py" "$@"; then
      echo "[setup] $v venv 있음(고정 목록과 같음) — 건너뜀"
    elif [ "$FORCE_VENV" = 1 ]; then
      echo "[setup] 경고: $VENVS/$v 가 고정 목록과 다르지만 FORCE_VENV=1 이라 그대로 쓴다" >&2
    else
      echo "[setup] 멈춤: $VENVS/$v 가 이 과정의 고정 목록과 다르다(위 목록). 다른 과정의 venv면 지우지 말고" \
           "VENVS=/root/venvs/<과정> 으로, 혼자 쓰는 Pod의 반쯤 깔린 venv면 rm -rf $VENVS/$v 뒤 다시 실행한다." >&2
      exit 3
    fi
  else
    echo "[setup] $v venv 만드는 중..."
    uv venv "$VENVS/$v" --python /usr/bin/python3.12 --seed
    uv pip install --python "$py" --torch-backend=auto "$@"
    CREATED="$CREATED $v"
  fi
}

mkdir -p "$VENVS" "$LOCKDIR"
if want train; then make_venv train "${TRAIN_PKGS[@]}"; fi
if want serve; then
  make_venv serve "${SERVE_PKGS[@]}"
  case " $CREATED " in *" serve "*) "$VENVS/serve/bin/vllm" download-kernels ;; esac
fi

if want train; then
  # JupyterLab에서 고를 수 있게 train venv를 커널로 등록 (Launcher에 "$KERNEL_LABEL" 이 생긴다)
  "$VENVS/train/bin/python" -m ipykernel install --user --name "$KERNEL" --display-name "$KERNEL_LABEL" >/dev/null
  uv pip freeze --python "$VENVS/train/bin/python" > "$LOCKDIR/train.lock"
fi
if want serve; then uv pip freeze --python "$VENVS/serve/bin/python" > "$LOCKDIR/serve.lock"; fi
rm -rf "$UV_CACHE_DIR"    # 설치가 끝난 uv 캐시(실측 약 22GB)를 지워 컨테이너 디스크를 확보

echo "[setup] 완료 (venv: $VENVS, lock: $LOCKDIR)"
if want train; then
  "$VENVS/train/bin/python" -c "import torch, transformers; print('train:', torch.__version__, 'transformers', transformers.__version__, 'cuda', torch.cuda.is_available())"
fi
if want serve; then
  "$VENVS/serve/bin/python" -c "import vllm, torch; print('serve: vllm', vllm.__version__, 'torch', torch.__version__)"
fi
df -h / | tail -1
