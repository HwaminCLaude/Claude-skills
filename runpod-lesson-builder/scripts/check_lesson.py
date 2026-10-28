"""레슨 품질 게이트 검사 + evidence-manifest.json 생성, 그리고 저장소 전체 비밀값 스캔.

사용법:
  python tools/check_lesson.py chapters/chapter-02/lesson-02-first-gpu-check   # 레슨 하나(게이트)
  python tools/check_lesson.py --repo [저장소 경로]                             # 저장소 전체 비밀값 스캔(기본: tools/의 부모)

레슨 검사 항목 (하나라도 FAIL이면 종료 코드 1):
  1. playbook.yaml 필수 필드(그림을 찍지 못한 STEP은 screenshots 대신 not_captured: "<이유>")
  2. playbook이 가리키는 스크린샷이 screenshots/에 있고, 마스킹 산출물(_masking.json) 또는
     마스킹본 위에 그린 주석 이미지(annotate-spec.json)인지
  3. README에 모든 단계 앵커가 있고, 각 단계의 스크린샷이 그 단계 구역 안(또는 앞 단계 구역 안)에 들어 있는지
     (단계 구역 = 그 앵커부터 다음 단계 앵커 또는 코드 블록 밖의 다음 '## ' 절 제목 앞까지).
     not_captured가 있는 단계는 그 이유 문구가 README의 그 단계 구역에 그대로 있어야 한다.
  3-1. 해설 대본: 시작·마무리 블록 + 모든 단계 구역 안의 '🎙️ 해설 대본' 블록(docs/DECISIONS.md 앞머리 narration: false면 건너뜀)
  4. README가 참조하는 이미지·파일이 모두 존재하는지(문서 안 앵커 링크 '#...'는 제외)
  5. 노트북: 코드 셀 출력 존재(출력이 없어야 하는 셀은 셀 태그 no-output 또는 첫 줄 '# no-output'), 실행 번호 1..n
  6. 기대 출력(expected-output)과 로그 일치
  7. 비밀값 스캔(토큰, API 키, IP, SSH 지문, Pod ID·접속 주소·SSH 포트 등) — 공개 대상 파일 전부
     (하위 폴더 포함. _raw/, 점(.)으로 시작하는 폴더, __pycache__, 이미지·영상·모델 같은 바이너리는 제외)
  8. storyboard.md가 있으면 모든 scene_id 포함

--repo 모드: 저장소의 공개 파일 전부(environment/, verification/, docs/, REPORT.md, README.md, curriculum.md,
  chapters/ …)를 같은 패턴으로 스캔한다. .git/·_raw/·점 폴더(.ssh/ 등)·__pycache__·tools/(스킬과 같은 도구 사본)·
  .env.local·바이너리는 건너뛰고, 루프백(127.x.x.x)과 0.0.0.0은 주소 비밀값으로 보지 않는다.

.env.local(Pod별 HOST·ID 값과 4자리 이상 숫자 PORT 값을 스캔 패턴에 더한다)은 이 파일이 든 tools/의 부모 폴더에서
먼저 찾고, 없으면 레슨 기준 저장소 루트(chapters/chapter-NN/lesson-MM 의 세 단계 위)에서 찾는다.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import yaml

REQUIRED = ["id", "part", "screen", "env", "result", "screenshots", "readme_anchor", "scene_id"]
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".mp4", ".mov", ".webm", ".mp3", ".wav",
              ".m4a", ".pdf", ".zip", ".gz", ".tar", ".7z", ".safetensors", ".bin", ".pt", ".pth", ".ckpt",
              ".onnx", ".pyc", ".npy", ".npz", ".parquet", ".arrow", ".whl", ".ttf", ".otf", ".woff", ".woff2"}
NARRATION = "🎙️ 해설 대본"     # README 접는 블록 제목(🎙️ = U+1F399 U+FE0F)

results = []
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서도 한글·기호 출력


def check(ok, name, detail=""):
    results.append((ok, name, detail))
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail else ""))


def find_root(lesson):
    cands = [Path(__file__).resolve().parents[1]]
    if len(lesson.parents) > 2:
        cands.append(lesson.parents[2])
    for c in cands:
        if (c / ".env.local").exists():
            return c
    return None


def load_decisions(lesson, root):
    """시작 인터뷰 기록 docs/DECISIONS.md의 앞머리(YAML)를 읽는다. 없거나 못 읽으면 빈 dict(= 기본값으로 검사)."""
    cands = [c for c in (root, lesson.parents[2] if len(lesson.parents) > 2 else None,
                         Path(__file__).resolve().parents[1]) if c]
    for c in cands:
        p = c / "docs" / "DECISIONS.md"
        if not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            print("NOTE docs/DECISIONS.md를 UTF-8로 읽지 못함 — 기본값으로 검사한다")
            return {}
        end = text.find("\n---", 3)
        if not text.startswith("---") or end == -1:
            print("NOTE docs/DECISIONS.md에 앞머리(---)가 없음 — 기본값으로 검사한다")
            return {}
        try:
            d = yaml.safe_load(text[3:end]) or {}
        except yaml.YAMLError:
            print("NOTE docs/DECISIONS.md 앞머리를 읽지 못함 — 기본값으로 검사한다")
            return {}
        return d if isinstance(d, dict) else {}
    return {}


def load_env(root):
    """.env.local 읽기. bash의 source와 같게 값 바깥 따옴표와 줄 앞 'export '는 무시한다."""
    env = {}
    p = root / ".env.local" if root else None
    if p and p.exists():
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k.startswith("export "):
                    k = k[len("export "):].strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                env[k] = v
    return env


def secret_patterns(env, repo_mode=False):
    ipv4 = (r"\b(?!127\.|0\.0\.0\.0\b)(?:\d{1,3}\.){3}\d{1,3}\b" if repo_mode
            else r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    pats = [
        (r"token=[A-Za-z0-9]{8,}", "token= 값"),
        (r"RUNPOD_API_KEY\s*=\s*\S+", "RUNPOD_API_KEY 값"),
        (r"JUPYTER_PASSWORD\s*=\s*\S+", "JUPYTER_PASSWORD 값"),
        (r"\bhf_[A-Za-z0-9]{20,}", "Hugging Face 토큰"),
        (r"\brpa_[A-Za-z0-9]{10,}", "RunPod API 키"),
        (ipv4, "IPv4 주소"),
        (r"-[0-9a-f]{8}@ssh\.runpod\.io", "프록시 SSH 사용자"),
        (r"SHA256:[A-Za-z0-9+/]{43}", "SSH 키 지문"),
    ]
    for k, v in env.items():
        if re.fullmatch(r"POD_[A-Z]_(ID|HOST)", k) and v:
            pats.append((re.escape(v), f"{k} 값"))
        elif re.fullmatch(r"POD_[A-Z]_PORT", k) and re.fullmatch(r"\d{4,5}", v or ""):
            # SSH 포트는 맥락이 있을 때만 잡는다(-p 12345, -P 12345, port=12345, 포트 12345) — 숫자만으로는 오탐이 많다
            pats.append((rf"(?:-[pP]\s*|(?i:port)\s*[=:]?\s*|포트\s*:?\s*){v}\b", f"{k} 값"))
    return pats


def public_files(lesson):
    """공개 대상 파일: 레슨 폴더 전체(하위 폴더 포함)에서 _raw/, 점 폴더, __pycache__, 바이너리를 뺀 것."""
    for f in sorted(lesson.rglob("*")):
        if not f.is_file():
            continue
        dirs = f.relative_to(lesson).parts[:-1]
        if any(d == "_raw" or d == "__pycache__" or d.startswith(".") for d in dirs):
            continue
        if f.suffix.lower() in BINARY_EXT:
            continue
        yield f


def repo_files(root):
    """--repo 모드의 공개 대상: 저장소 전체에서 .git/·_raw/·점 폴더·__pycache__·tools/·.env.local·바이너리를 뺀 것."""
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(root).parts
        dirs = rel[:-1]
        if any(d == "_raw" or d == "__pycache__" or d.startswith(".") for d in dirs):
            continue
        if dirs and dirs[0] == "tools":
            continue
        if rel == (".env.local",) or f.suffix.lower() in BINARY_EXT:
            continue
        yield f


def scan(files, base, pats):
    hits = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        for pat, label in pats:
            if re.search(pat, text):
                hits.append(f"{f.relative_to(base).as_posix()}: {label}")
    return sorted(set(hits))


def _heading_cut(text):
    """text 안에서 코드 블록(```) 밖에 있는 첫 '## ' 절 제목의 위치(없으면 None)."""
    fence, pos = False, 0
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            fence = not fence
        elif not fence and line.startswith("## "):
            return pos
        pos += len(line)
    return None


def section_spans(readme, anchors):
    """앵커 id -> (시작, 끝) 문자 위치. 끝 = 다음 단계 앵커와 다음 '## ' 절 제목 중 앞선 것."""
    pos = {}
    for a in anchors:
        m = re.search(rf'<a id="{re.escape(a)}"></a>', readme)
        pos[a] = m.start() if m else None
    found = sorted((p, a) for a, p in pos.items() if p is not None)
    spans = {}
    for i, (p, a) in enumerate(found):
        end = found[i + 1][0] if i + 1 < len(found) else len(readme)
        cut = _heading_cut(readme[p:end])
        spans[a] = (p, p + cut if cut is not None else end)
    return spans


def shots_of(step):
    return step.get("screenshots") or []


def main(lesson_dir):
    lesson = Path(lesson_dir).resolve()
    root = find_root(lesson)
    env = load_env(root)
    if root is None:
        print("NOTE .env.local을 찾지 못함 — Pod별 HOST·ID·PORT 값 없이 기본 패턴으로만 비밀값을 스캔한다")
    decisions = load_decisions(lesson, root)
    pb = yaml.safe_load((lesson / "playbook.yaml").read_text(encoding="utf-8"))
    steps = pb["steps"]

    # 1. 필수 필드 (not_captured가 있는 단계는 screenshots가 비어도 된다)
    missing = [f"{s.get('id')}:{f}" for s in steps for f in REQUIRED
               if not s.get(f) and not (f == "screenshots" and s.get("not_captured"))]
    check(not missing, "playbook 필수 필드", ", ".join(missing))

    # 2. 스크린샷 존재 + 마스킹 경로
    shots = lesson / "screenshots"
    mask_p = shots / "_masking.json"
    if mask_p.exists():
        masked = json.loads(mask_p.read_text(encoding="utf-8-sig"))
    else:
        masked = {}
        check(False, "screenshots/_masking.json", "없음 — 먼저 python tools/redact.py <레슨폴더>")
    raw_dir = lesson / "_raw"
    ann_spec_p = raw_dir / "annotate-spec.json"
    man_p = lesson / "evidence-manifest.json"
    if ann_spec_p.exists():
        annotated = json.loads(ann_spec_p.read_text(encoding="utf-8-sig"))
    elif not raw_dir.exists() and man_p.exists():
        # 새 clone: _raw/는 .gitignore로 빠지므로 클릭 표시 그림 정보는 커밋된 manifest에서 읽는다
        man = json.loads(man_p.read_text(encoding="utf-8"))
        annotated = {Path(i["file"]).name: {"src": Path(i["base"]).name, "marks": [None] * int(i.get("marks") or 0)}
                     for i in man.get("images", []) if i.get("source") == "annotated" and i.get("base")}
        print("NOTE: _raw/ 없음(새 clone) — 클릭 표시 그림은 evidence-manifest.json 기준, manifest는 다시 쓰지 않음")
    else:
        annotated = {}
    bad = []
    for s in steps:
        for img in shots_of(s):
            if not (shots / img).exists():
                bad.append(f"{s['id']}:{img} 없음")
            elif img not in masked and not (img in annotated and annotated[img]["src"] in masked):
                bad.append(f"{s['id']}:{img} 마스킹 경로 아님")
    published = {p.name for p in shots.glob("*.png")}
    stray = sorted(published - set(masked) - set(annotated))
    check(not bad, "스크린샷 존재·마스킹", "; ".join(bad))
    check(not stray, "공개 폴더에 마스킹 경로 밖 이미지 없음", ", ".join(stray))

    # 3. README 앵커와 단계별 이미지 배치
    readme = (lesson / "README.md").read_text(encoding="utf-8")
    anchors = [s["readme_anchor"] for s in steps]
    spans = section_spans(readme, anchors)
    no_anchor = [a for a in anchors if a not in spans]
    check(not no_anchor, "README 단계 앵커", ", ".join(no_anchor))
    misplaced = []
    for s in steps:
        span = spans.get(s["readme_anchor"])
        if not span:
            continue
        body = readme[span[0]:span[1]]
        # 앞 단계 구역에서 이미 보여 준 공용 이미지는 이 단계 안에 없어도 된다(02 미리 보기 같은 단계 밖 절은 인정하지 않음)
        earlier = [readme[a0:a1] for a0, a1 in spans.values() if a0 < span[0]]
        for img in shots_of(s):
            ref = f"screenshots/{img}"
            if ref not in body and not any(ref in e for e in earlier):
                misplaced.append(f"{s['id']}:{img}")
        reason = (s.get("not_captured") or "").strip()
        if reason and reason not in body:
            misplaced.append(f"{s['id']}: not_captured 이유 문구가 README 구역에 없음")
    check(not misplaced, "단계 이미지가 해당 단계 구역 안(또는 앞 단계 구역 안)에 배치", ", ".join(misplaced))

    # 3-1. 해설 대본: 시작·마무리 블록 + 모든 STEP 구역 끝의 해설 블록
    #      (시작 인터뷰에서 '해설 대본 없음'으로 정했으면 docs/DECISIONS.md의 narration: false — 이 항목만 건너뛴다)
    nar = decisions.get("narration")
    if isinstance(nar, str):            # narration: "false"처럼 따옴표로 쓴 값도 받아 준다
        nar = {"false": False, "no": False, "off": False, "true": True, "yes": True, "on": True}.get(nar.strip().lower(), nar)
    if nar is False:
        print("NOTE docs/DECISIONS.md narration: false — 해설 대본 항목은 검사하지 않는다")
    else:
        nar_missing = [s["id"] for s in steps
                       if s["readme_anchor"] in spans
                       and NARRATION not in readme[spans[s["readme_anchor"]][0]:spans[s["readme_anchor"]][1]]]
        has_intro = f"{NARRATION} — 시작" in readme
        has_outro = f"{NARRATION} — 마무리" in readme
        check(not nar_missing and has_intro and has_outro, "해설 대본(시작·STEP별·마무리)",
              ("STEP 없음: " + ", ".join(nar_missing) if nar_missing else "")
              + ("" if has_intro else " 시작 블록 없음") + ("" if has_outro else " 마무리 블록 없음"))

    # 4. README 참조 파일 존재 (http 링크·문서 안 앵커 '#...'는 건너뛰고, 'file.md#절'은 파일만 확인)
    refs = re.findall(r"\]\(([^)\s]+)\)", readme)
    dead = [r for r in refs if not r.startswith(("http", "#", "mailto:"))
            and not (lesson / unquote(r.split("#", 1)[0])).exists()]
    check(not dead, "README 참조 파일 존재", ", ".join(dead))

    # 5. 노트북 (notebooks/*.ipynb 전부: 실행 번호 1..n, 코드 셀마다 출력. 출력이 없어야 하는 셀은
    #    셀 메타데이터 태그 "no-output"(학습자 코드에 주석이 남지 않음) 또는 소스 첫 줄 '# no-output')
    for nb_path in sorted((lesson / "notebooks").glob("*.ipynb")):
        nb = json.loads(nb_path.read_text(encoding="utf-8"))
        code = [c for c in nb["cells"] if c["cell_type"] == "code" and "".join(c["source"]).strip()]
        counts = [c.get("execution_count") for c in code]
        no_out = [i + 1 for i, c in enumerate(code)
                  if not c.get("outputs")
                  and "no-output" not in ((c.get("metadata") or {}).get("tags") or [])
                  and not "".join(c["source"]).lstrip().startswith("# no-output")]
        check(counts == list(range(1, len(code) + 1)), f"{nb_path.name} 실행 번호 1..n", str(counts))
        check(not no_out, f"{nb_path.name} 코드 셀 출력", str(no_out))

    # 6. 기대 출력 vs 로그: expected-output/*.txt 머리에 '# log: <레슨 기준 경로>' 와
    #    선택 '# after: <이 글자 뒤부터 검사>' 를 적는다. 나머지 줄은 정규식(줄 단위).
    for exp_p in sorted((lesson / "expected-output").glob("*.txt")):
        lines = exp_p.read_text(encoding="utf-8").splitlines()
        meta = {m.group(1): m.group(2).strip() for l in lines if (m := re.match(r"#\s*(log|after):\s*(.+)", l))}
        pats = [l for l in lines if l and not l.startswith("#")]
        if "log" not in meta:
            check(False, f"{exp_p.name} 기대 출력", "'# log:' 줄이 없음")
            continue
        log_p = lesson / meta["log"]
        if not log_p.exists():
            check(False, f"{exp_p.name} 기대 출력", f"로그 없음: {meta['log']}")
            continue
        block = log_p.read_text(encoding="utf-8", errors="ignore")
        if meta.get("after"):
            block = block.split(meta["after"], 1)[-1]
        miss = [p for p in pats if not re.search(p, block, re.M)]
        check(not miss, f"{exp_p.name} 기대 출력이 로그와 일치", ", ".join(miss))

    # 7. 비밀값 스캔
    hits = scan(public_files(lesson), lesson, secret_patterns(env))
    check(not hits, "비밀값 스캔", "; ".join(hits))

    # 8. storyboard
    sb = lesson / "storyboard.md"
    if sb.exists():
        text = sb.read_text(encoding="utf-8")
        scenes = sorted({s["scene_id"] for s in steps})
        miss = [x for x in scenes if x not in text]
        check(not miss, "storyboard에 모든 scene_id", ", ".join(miss))

    if raw_dir.exists():
        write_manifest(lesson, pb, masked, annotated)
    fails = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(fails)} PASS / {len(fails)} FAIL")
    return 1 if fails else 0


def write_manifest(lesson, pb, masked, annotated):
    raw_log = {}
    lp = lesson / "_raw" / "capture-log.jsonl"
    if lp.exists():
        for line in lp.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                e = json.loads(line)
                raw_log[e["file"]] = e          # file = _raw 안의 원본 파일 이름(redact-spec의 키와 같아야 한다)
    step_of = {}
    for s in pb["steps"]:
        for img in shots_of(s):
            step_of.setdefault(img, []).append(s["id"])
    items = []
    for out, info in sorted(masked.items()):
        e = raw_log.get(info["source"], {})
        items.append({"file": f"screenshots/{out}", "steps": step_of.get(out, []), "kind": e.get("kind"),
                      "source": "real-capture", "masked_boxes": info["masked_boxes"],
                      "captured_note": e.get("note"), "pod": e.get("pod"), "tool": e.get("tool")})
    for out, spec in sorted(annotated.items()):
        items.append({"file": f"screenshots/{out}", "steps": step_of.get(out, []), "kind": "click",
                      "source": "annotated", "base": f"screenshots/{spec['src']}",
                      "marks": len(spec["marks"])})
    manifest = {"lesson": pb["lesson"]["id"], "captured_at": pb["lesson"]["captured_at"],
                "environment": pb["lesson"]["environment"], "images": items}
    not_captured = {s["id"]: s["not_captured"] for s in pb["steps"] if s.get("not_captured")}
    if not_captured:                    # 그림 없이 '촬영하지 않음(이유)'로 쓴 단계
        manifest["not_captured"] = not_captured
    (lesson / "evidence-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
    print(f"evidence-manifest.json: {len(items)} images")


def main_repo(repo_dir=None):
    root = Path(repo_dir).resolve() if repo_dir else Path(__file__).resolve().parents[1]
    if not root.is_dir():
        print(f"저장소 폴더가 없다: {root}")
        return 2
    env = load_env(root)
    if not (root / ".env.local").exists():
        print("NOTE .env.local을 찾지 못함 — Pod별 HOST·ID·PORT 값 없이 기본 패턴으로만 비밀값을 스캔한다")
    files = list(repo_files(root))
    hits = scan(files, root, secret_patterns(env, repo_mode=True))
    check(not hits, f"저장소 비밀값 스캔({len(files)}개 파일)", "; ".join(hits))
    fails = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(fails)} PASS / {len(fails)} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--repo":
        sys.exit(main_repo(sys.argv[2] if len(sys.argv) > 2 else None))
    if len(sys.argv) != 2:
        print("사용법: python tools/check_lesson.py <레슨폴더>  |  python tools/check_lesson.py --repo [저장소]")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
