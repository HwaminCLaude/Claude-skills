"""새 RunPod 실습 과정 저장소의 뼈대를 만들고, 기존 저장소의 tools/를 스킬 판과 맞춘다.

사용법:
    python init_course.py <과정 저장소 경로> [--title "과정 이름"] [--pod-root workspace/<폴더>]
                          [--venvs /root/venvs] [--kernel train] [--kernel-label "Python (train)"] [--force]
    python init_course.py <기존 과정 저장소> --check-tools     # tools/와 스킬 scripts/를 비교만 한다(쓰지 않음)
    python init_course.py <기존 과정 저장소> --update-tools    # tools/에서 다른 파일만 스킬 판으로 바꾼다(다른 파일은 손대지 않음)
    python init_course.py <기존 과정 저장소> --init-decisions [--title "과정 이름"]
                          # docs/DECISIONS.md(시작 인터뷰 기록 틀)가 없을 때 그 파일만 만든다(다른 파일은 손대지 않음)

    --pod-root 기본값은 /workspace/<저장소 폴더 이름(소문자·영숫자·하이픈)>. Git Bash에서는 앞의 /를 빼고 쓴다
      (붙이면 MSYS가 C:/Program Files/Git/workspace/…로 바꿔 넘겨서 이 스크립트가 멈춘다).
    --venvs·--kernel·--kernel-label: 같은 Pod를 다른 과정도 쓰면 과정별로 다르게 준다(예: /root/venvs/<과정>, <과정>-train).
      environment/setup.sh 기본값과 docs/LESSON_GUIDE.md에 함께 들어간다.

만드는 것(저장소 기준):
    README.md, curriculum.md          첫 화면·커리큘럼 초안
    docs/LESSON_GUIDE.md              레슨 제작 계약서(이 스킬의 assets/LESSON_GUIDE.template.md를 채워서)
    docs/DECISIONS.md                 시작 인터뷰 결정 기록 틀(assets/decisions.template.md — 인터뷰 답으로 채운다)
    tools/                            pod.sh pod_get.sh jlab.py webshot.py redact.py annotate.py check_lesson.py stackcheck.sh
    environment/setup.sh              Pod 파이썬 환경 만들기(LLM 과정 기본값, 버전 고정값의 단일 원본)
    environment/preflight-report.md   사전 점검 보고서 틀, environment/versions.md  실측 버전 기록 틀
    .gitignore                        .env.local, .ssh/, **/_raw/ 등 공개 금지 목록
    .env.local.example                Pod 접속값 자리(복사해서 .env.local로 채운다)
    chapters/ shared/diagrams/ verification/   빈 폴더(.gitkeep)

이미 있는 파일은 덮어쓰지 않는다: 하나라도 있으면 아무것도 쓰지 않고 목록을 보여 준 뒤 멈춘다.
--force는 README.md·curriculum.md·docs/LESSON_GUIDE.md·environment/*까지 템플릿으로 덮어쓰므로 작업 중인 저장소에는
쓰지 않는다(도구만 바꾸려면 --update-tools). docs/DECISIONS.md(인터뷰 기록)는 --force로도 덮어쓰지 않고 그대로 둔다
(없는 기존 저장소에 그 파일만 만들려면 --init-decisions). .env.local은 만들지도 덮어쓰지도 않는다.
tools/의 스크립트는 저장소 루트(= tools/의 부모)의 .env.local을 읽는다.
"""
import argparse
import datetime
import os
import re
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서도 한글·기호 출력

SK = Path(__file__).resolve().parents[1]       # 스킬 폴더
DECISIONS = "docs/DECISIONS.md"                # 시작 인터뷰 기록 — --force로도 덮어쓰지 않는다
TOOLS = ["pod.sh", "pod_get.sh", "jlab.py", "webshot.py", "redact.py", "annotate.py", "check_lesson.py",
         "stackcheck.sh"]
DIRS = ["chapters", "shared/diagrams", "verification"]
# environment/setup.sh에서 과정마다 바꾸는 줄(스킬 scripts/setup.sh의 줄과 글자까지 같아야 한다)
SETUP_LINES = {
    "COURSE_DIR": 'COURSE_DIR="${COURSE_DIR:-/workspace/llm-course}"',
    "VENVS": 'VENVS="${VENVS:-/root/venvs}"',
    "KERNEL": 'KERNEL="${KERNEL:-train}"',
    "KERNEL_LABEL": 'KERNEL_LABEL="${KERNEL_LABEL:-Python (train)}"',
}


def gitbash_path(p):
    """D:\\My Course\\x → /d/My Course/x (Git Bash에서 cd 할 경로)."""
    s = p.as_posix()
    if len(s) > 1 and s[1] == ":":
        s = "/" + s[0].lower() + s[2:]
    return s


def slug(name):
    """저장소 폴더 이름 → Pod 폴더 이름(소문자 영숫자·점·밑줄·하이픈). 남는 글자가 없으면 'course'."""
    s = re.sub(r"[^a-z0-9._-]+", "-", name.lower()).strip("-.")
    return re.sub(r"-{2,}", "-", s) or "course"


def fill(text, subst):
    for k, v in subst.items():
        text = text.replace(k, v)
    return text


def readme_stub(title, today):
    return f"""# {title} — RunPod에서 직접 따라 하는 실습

비개발자가 **실제 RunPod 화면**을 보면서 Terminal, Python 파일, Jupyter Notebook으로 따라 하는 실습 교재입니다.

- 모든 단계는 실제 GPU Pod에서 실행했고, 스크린샷과 로그를 증거로 남겼습니다.
- 각 레슨의 `README.md`는 영상 없이도 따라 할 수 있는 독립 교재입니다.

## 시작하기

| 순서 | 레슨 | 상태 |
|---|---|---|
| — | 전체 계획: [curriculum.md](curriculum.md) | 작성 중({today}) |

## 폴더 구조

```text
.
├── README.md                 ← 이 파일
├── curriculum.md             ← 전체 커리큘럼과 결정 사항
├── docs/LESSON_GUIDE.md      ← 레슨 제작 계약서(제작용)
├── environment/              ← setup.sh, 사전 점검 보고서, 실측 버전 기록
├── chapters/
│   └── chapter-NN/lesson-MM-slug/
│       ├── README.md         ← 독립형 실습 교재
│       ├── playbook.yaml     ← 단계별 원본 절차서(README의 기준)
│       ├── code/ notebooks/ scripts/
│       ├── screenshots/      ← 공개용(민감정보 가림) 스크린샷
│       ├── logs/ expected-output/
│       ├── troubleshooting.md
│       └── evidence-manifest.json
├── shared/diagrams/          ← 개념 그림
├── tools/                    ← Pod 접속·캡처·마스킹·검사 도구(제작용)
└── verification/             ← 재현성 검증 기록
```

## 제작용 도구 (`tools/`)

| 도구 | 용도 |
|---|---|
| `pod.sh A\\|B '명령'` | `.env.local`의 접속값으로 Pod에 SSH 명령 실행(호스트 키는 저장소 `.ssh/`에 보관) |
| `pod_get.sh A 원격경로 로컬폴더` | Pod 파일 가져오기 |
| `jlab.py` | SSH 터널 + 헤드리스 Chromium으로 JupyterLab 실화면 조작·캡처(1600×900) |
| `webshot.py <URL> <저장 경로>` | 로그인 없는 공개 웹 페이지 캡처(1600×900) |
| `redact.py <레슨폴더>` | `_raw/redact-spec.json`에 적힌 원본만 모자이크 처리해 `screenshots/`로 내보냄 |
| `annotate.py <레슨폴더>` | 마스킹본 위에 '클릭 위치' 번호 표시 |
| `check_lesson.py <레슨폴더>` | 품질 게이트(이미지 배치, 해설 대본, 참조 파일, 노트북, 기대 출력, 비밀값 스캔) + `evidence-manifest.json` 생성. `--repo`는 저장소 전체 비밀값 스캔 |
| `stackcheck.sh` | 본 제작 전 패키지 스택 설치·동작 실측(컨테이너 디스크에서) |

`.env.local`, `.ssh/`, `**/_raw/`(마스킹 전 원본)는 공개하지 않습니다(`.gitignore`).
"""


def curriculum_stub(title, today):
    return f"""# 전체 커리큘럼 — {title}

- 기준일: {today}. 레슨마다 '마지막 검증일'을 README 머리말에 적는다.
- 제작 원칙: 실제 Pod에서 실행 → 증거(스크린샷·로그) → 독립형 README(+ 🎙️ 해설 대본) → README만 보고 재현 검증. 영상은 요청한 레슨만.
- 레슨 상태: ✅ 완료 · 🟡 진행 중 · ⬜ 예정

## 공통 환경 결정
| 항목 | 결정 | 근거 |
|---|---|---|
| Pod | <템플릿, GPU 종류·개수, Cloud> | <실측 / 공식 문서> |
| 저장 | 실습 파일·모델 캐시는 `/workspace`(Volume) | 컨테이너 디스크는 Stop 때 지워짐 |
| 파이썬 환경 | <venv 구성 — 학습자는 어느 레슨에서 만드는지> | <버전 충돌 근거> |
| 모델·데이터 | <ID, 라이선스, gated 여부> | <근거> |
| 고정값 카드 | <과정 전체 고정값> | <실측 레슨> |

## 결정이 필요한 것 (본 제작 전)
1. <저장 용량, 비용, 라이선스처럼 사용자가 정할 것>

## 챕터별 레슨
| Ch | 레슨 | 주 환경 | GPU | 상태 |
|---|---|---|---|---|
| 01 | L01 <목표 하나> · L02 <목표 하나> | <브라우저 / Terminal / ipynb / .py> | <불필요 / 24GB+ / 48GB> | ⬜ |

## Pod에서 아직 실측하지 않은 것
- <공식 문서끼리 어긋나거나 확인되지 않은 항목과 확인 명령>

## 이미 실측으로 확인한 것
- <environment/versions.md 참고>
"""


def compare_tools(root):
    """tools/의 각 파일을 스킬 scripts/와 바이트 단위로 비교 → [(이름, '같음'|'다름'|'없음')]."""
    out = []
    for t in TOOLS:
        dst, src = root / "tools" / t, SK / "scripts" / t
        if not dst.exists():
            out.append((t, "없음"))
        else:
            out.append((t, "같음" if dst.read_bytes() == src.read_bytes() else "다름"))
    return out


def tools_mode(root, update):
    if not (root / "tools").is_dir():
        print(f"tools/ 폴더가 없다({root}). 새 과정이면 --check-tools/--update-tools 없이 실행한다.")
        return 2
    rows = compare_tools(root)
    for t, st in rows:
        print(f"  {st}  tools/{t}")
    todo = [t for t, st in rows if st != "같음"]
    if not todo:
        print("tools/가 스킬 판과 같다.")
        return 0
    if not update:
        print(f"\n{len(todo)}개가 스킬 판과 다르다. 사용자에게 알리고, 이 tools/를 쓰는 워크플로가 돌고 있지 않을 때\n"
              f"  python \"{Path(__file__).resolve().as_posix()}\" \"{root.as_posix()}\" --update-tools\n"
              "로 tools/만 바꾼다(README·curriculum·LESSON_GUIDE·environment/는 그대로).")
        return 1
    for t in todo:
        dest = root / "tools" / t
        shutil.copy2(SK / "scripts" / t, dest)                           # 바이트 그대로(줄바꿈 LF 유지)
        if dest.suffix == ".sh":
            os.chmod(dest, 0o755)
        print(f"바꿈   tools/{t}")
    print("tools/만 바꿨다. 다른 파일은 손대지 않았다.")
    return 0


def init_decisions(root, title):
    """기존 과정 저장소에 docs/DECISIONS.md(시작 인터뷰 기록 틀)만 만든다. 이미 있으면 아무것도 쓰지 않는다."""
    if not root.is_dir():
        print(f"저장소 폴더가 없다({root}). 새 과정이면 --init-decisions 없이 실행한다(DECISIONS.md도 함께 만든다).")
        return 2
    dest = root / DECISIONS
    if dest.exists():
        print(f"이미 있어 쓰지 않았다: {DECISIONS} — 바뀐 결정은 그 파일의 값과 '바뀐 기록'을 고친다.")
        return 1
    text = fill((SK / "assets" / "decisions.template.md").read_text(encoding="utf-8"),
                {"{{COURSE_TITLE}}": title or root.name})
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8", newline="\n")
    print(f"만듦   {DECISIONS}\n다른 파일은 손대지 않았다. 시작 인터뷰(스킬 references/intake-interview.md)의 답으로 채운다"
          "(앞머리 키 이름은 그대로).")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="RunPod 실습 과정 저장소 뼈대 만들기 / tools/ 맞추기")
    ap.add_argument("path", help="과정 저장소 폴더(없으면 만든다)")
    ap.add_argument("--title", default=None, help="과정 이름(기본: 폴더 이름 — 사용자에게 먼저 묻는다)")
    ap.add_argument("--pod-root", default=None,
                    help="Pod 안 학습자 작업 폴더(기본: /workspace/<저장소 폴더 이름>. Git Bash에서는 앞의 /를 빼고 workspace/<폴더>)")
    ap.add_argument("--venvs", default="/root/venvs", help="Pod의 venv 상위 폴더(기본 /root/venvs)")
    ap.add_argument("--kernel", default="train", help="train venv의 커널(kernelspec) 이름(기본 train)")
    ap.add_argument("--kernel-label", default="Python (train)", help='Launcher에 보이는 커널 이름(기본 "Python (train)")')
    ap.add_argument("--force", action="store_true",
                    help="이미 있는 파일도 덮어쓴다 — README·curriculum·LESSON_GUIDE·environment/까지 템플릿으로 바뀌므로 "
                         "작업 중인 저장소에는 쓰지 않는다(도구만 바꾸려면 --update-tools). docs/DECISIONS.md(인터뷰 기록)는 보존한다")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check-tools", action="store_true", help="기존 저장소의 tools/를 스킬 scripts/와 비교만 한다")
    g.add_argument("--update-tools", action="store_true", help="기존 저장소의 tools/에서 다른 파일만 스킬 판으로 바꾼다")
    g.add_argument("--init-decisions", action="store_true",
                   help="기존 저장소에 docs/DECISIONS.md가 없을 때 그 틀만 만든다(과정 이름은 --title, 없으면 폴더 이름). "
                        "다른 파일은 손대지 않는다")
    a = ap.parse_args(argv)

    root = Path(a.path).resolve()
    if a.check_tools or a.update_tools:
        return tools_mode(root, a.update_tools)
    if a.init_decisions:
        return init_decisions(root, a.title)

    for name, val in (("--pod-root", a.pod_root or ""), ("--venvs", a.venvs)):
        if re.match(r"^[A-Za-z]:[\\/]", val):
            # Git Bash(MSYS)는 python.exe 같은 Windows 프로그램에 넘기는 /workspace/… 인자를 C:/Program Files/Git/workspace/…로 바꾼다
            print(f"{name}가 Windows 경로로 바뀌어 들어왔다({val}). Git Bash의 경로 변환 때문이다.\n"
                  f"앞의 /를 빼고 쓰거나({name} workspace/<폴더>) 명령 앞에 MSYS_NO_PATHCONV=1 을 붙여 다시 실행한다.")
            return 2
    if not re.fullmatch(r"[A-Za-z0-9._-]+", a.kernel):
        print(f"--kernel은 영숫자·점·밑줄·하이픈만 쓴다: {a.kernel}")
        return 2
    if re.search(r'["$`\\]', a.kernel_label):
        print(f"--kernel-label에는 따옴표·$·백틱·역슬래시를 쓰지 않는다: {a.kernel_label}")
        return 2
    title = a.title or root.name
    today = datetime.date.today().isoformat()
    pod_root = "/" + (a.pod_root.strip("/") if a.pod_root else "workspace/" + slug(root.name))
    venvs = "/" + a.venvs.strip("/")
    lockdir = "/workspace/.course-env/" + pod_root.rstrip("/").rsplit("/", 1)[-1]
    subst = {"{{COURSE_TITLE}}": title, "{{DATE}}": today, "{{REPO_PATH}}": str(root),
             "{{REPO_GITBASH}}": gitbash_path(root), "{{POD_ROOT}}": pod_root, "{{POD_ROOT_REL}}": pod_root.lstrip("/"),
             "{{VENVS}}": venvs, "{{KERNEL}}": a.kernel, "{{KERNEL_LABEL}}": a.kernel_label, "{{LOCKDIR}}": lockdir,
             "{{EXAMPLE_LESSON}}": (SK / "assets" / "example-lesson").as_posix()}

    setup = (SK / "scripts" / "setup.sh").read_text(encoding="utf-8")
    new_vals = {"COURSE_DIR": pod_root, "VENVS": venvs, "KERNEL": a.kernel, "KERNEL_LABEL": a.kernel_label}
    for key, line in SETUP_LINES.items():
        if line not in setup:
            print(f"스킬 scripts/setup.sh에서 바꿀 줄을 찾지 못해 멈춘다({key}): {line}")
            return 2
        setup = setup.replace(line, f'{key}="${{{key}:-{new_vals[key]}}}"')

    plan = [("README.md", "text", readme_stub(title, today)),
            ("curriculum.md", "text", curriculum_stub(title, today)),
            ("docs/LESSON_GUIDE.md", "text",
             fill((SK / "assets" / "LESSON_GUIDE.template.md").read_text(encoding="utf-8"), subst)),
            (DECISIONS, "text",                     # 시작 인터뷰 기록(references/intake-interview.md 4절)
             fill((SK / "assets" / "decisions.template.md").read_text(encoding="utf-8"), subst))]
    plan += [(f"tools/{t}", "copy", SK / "scripts" / t) for t in TOOLS]
    plan += [("environment/setup.sh", "text", setup),
             ("environment/preflight-report.md", "text",
              fill((SK / "assets" / "preflight-report.template.md").read_text(encoding="utf-8"), subst)),
             ("environment/versions.md", "text",
              fill((SK / "assets" / "versions.template.md").read_text(encoding="utf-8"), subst)),
             (".gitignore", "copy", SK / "assets" / "gitignore.txt"),
             (".env.local.example", "copy", SK / "assets" / "env.local.example")]

    missing = [str(src) for _, kind, src in plan if kind == "copy" and not Path(src).exists()]
    if missing:
        print("스킬 파일이 없어 멈춘다:", ", ".join(missing))
        return 2
    existing = [d for d, _, _ in plan if (root / d).exists()]
    if existing and not a.force:
        print(f"이미 있는 파일이 있어 아무것도 쓰지 않았다({root}).\n"
              "기존 과정이면 도구만 맞춘다(--check-tools → --update-tools). 인터뷰 기록이 없으면 --init-decisions.\n"
              f"--force는 아래 파일을 모두 템플릿으로 덮어쓴다({DECISIONS}는 보존):")
        for d in existing:
            print("  -", d + ("  (보존)" if d == DECISIONS else ""))
        return 1

    for d, kind, payload in plan:
        if a.force and d == DECISIONS and d in existing:
            print("보존   " + d)                                         # 인터뷰 기록은 --force로도 덮어쓰지 않는다
            continue
        dest = root / d
        dest.parent.mkdir(parents=True, exist_ok=True)
        if kind == "copy":
            shutil.copy2(payload, dest)                                  # 바이트 그대로(줄바꿈 LF 유지)
        else:
            dest.write_text(payload, encoding="utf-8", newline="\n")
        if dest.suffix == ".sh":
            os.chmod(dest, 0o755)
        print(("덮어씀 " if d in existing else "만듦   ") + d)
    for d in DIRS:
        p = root / d
        p.mkdir(parents=True, exist_ok=True)
        if not any(p.iterdir()):
            (p / ".gitkeep").touch()
            print("만듦   " + d + "/")

    gb = gitbash_path(root)
    print(f"""
Pod 안 학습자 작업 폴더: {pod_root}   venv: {venvs}/train·serve   커널: {a.kernel} ("{a.kernel_label}")   lock: {lockdir}

다음 단계(이 스크립트는 로컬 파일만 만들었다 — Pod·계정에는 아무것도 하지 않았다):
 0. 시작 인터뷰(스킬 references/intake-interview.md)에서 정한 값을 docs/DECISIONS.md에 채운다(앞머리 키 이름은 그대로).
 1. .env.local.example 을 .env.local 로 복사하고 Pod 접속값을 채운다
    (RunPod 콘솔 → Pods → Pod 이름 → Connect → SSH over exposed TCP 의 IP·포트, Pod 이름·ID).
    .env.local 과 .ssh/ 는 .gitignore에 이미 들어 있다. 값은 따옴표 없이 쓰고, 대화에 다시 출력하지 않는다.
 2. 접속 확인(Git Bash):  cd "{gb}" && tools/pod.sh A 'nvidia-smi -L'
 3. 사전 점검(읽기 전용, 스킬 references/workflow.md Phase 0) → environment/preflight-report.md → 사용자 보고·승인.
    Pod를 다른 과정·세션도 쓰는지 본다:  tools/pod.sh A 'ls -A {pod_root} 2>/dev/null | head -5; ls /root/venvs 2>/dev/null; tmux ls 2>&1 | head -5'
    {pod_root} 가 비어 있지 않거나 남의 venv·tmux가 있으면 멈추고 사용자에게 묻는다.
 4. 승인 뒤 Pod 환경(LLM 과정 기본값 약 2분):
      tools/pod.sh A 'cat > /root/setup.sh' < environment/setup.sh && tools/pod.sh A 'bash /root/setup.sh'
 5. docs/LESSON_GUIDE.md 의 <…> 자리(환경 표·레인 표)를 실측값으로 채운다.
 6. (선택) git init — 로컬만. 첫 레슨은 파일럿으로 하나만 만들고
      python tools/check_lesson.py chapters/chapter-NN/lesson-MM-slug  가 모두 PASS인지 본 뒤 병렬 제작으로 간다.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
