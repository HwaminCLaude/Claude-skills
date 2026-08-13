"""Generate a supporting still via the Codex CLI's native image generation.

This is an *optional* node. The backbone of every episode is Manim drawing;
generated art fills only the cuts that shapes and equations cannot carry —
metaphor, atmosphere, real-world analogy. Roughly 1-3 cuts per episode. If
you find yourself reaching for more, the storyboard is the thing that's wrong.

Accuracy guardrail
------------------
These videos present the user's own research. A generated picture that looks
like data, results, or the actual architecture would be fabrication. Prompts
that ask for those are refused; use `crop_figure.py` on the paper PDF or draw
it in Manim instead.

No text inside images
---------------------
Generated lettering is unreliable and Korean especially so. Images are always
prompted text-free; labels go on top as Manim `Text`/`MathTex`, which also
keeps typography consistent with the rest of the video.

    python gen_image.py --check
    python gen_image.py --prompt "고차원 공간에서 가까운 이웃을 찾는 장면의 은유" \\
                        --out C:\\manimwork\\my-paper\\ep01\\assets\\generated\\s04_neighbors.png
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


# Windows consoles default to cp949 here, and every one of these scripts prints
# Korean. Without this, a run dies with UnicodeEncodeError *after* it has already
# written its output files — the confusing failure mode of looking broken while
# actually having succeeded.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

GENERATED_ROOT = Path.home() / ".codex" / "generated_images"
TIMEOUT_SEC = 420

# Prepended to every prompt so a series looks like one series and the stills sit
# on Manim's black stage without a visible seam.
STYLE_PREFIX = (
    "Flat vector illustration, minimal, on a pure black (#000000) background. "
    "Restrained palette: white, soft blue, muted teal, one warm accent. "
    "Clean geometric shapes, generous negative space, subtle depth, no gradients "
    "heavier than a soft glow. Editorial diagram aesthetic, not photorealistic. "
    "ABSOLUTELY NO TEXT, no letters, no numbers, no labels, no captions, no watermark "
    "anywhere in the image. Composition centered with room at the top for a caption "
    "to be added later. Subject: "
)

# Anything that would read as a research artifact.
FORBIDDEN = [
    (r"그래프|차트|plot|chart|graph\b", "성능·데이터 그래프"),
    (r"성능|정확도|accuracy|benchmark|결과\s*표|result table|confusion matrix", "실험 결과"),
    (r"아키텍처\s*다이어그램|architecture diagram|network diagram|model diagram", "아키텍처 다이어그램"),
    (r"figure\s*\d|fig\.?\s*\d|논문\s*그림", "논문 figure 재현"),
    (r"scatter\s*plot|산점도|히스토그램|histogram|heatmap|히트맵", "데이터 시각화"),
]


def resolve(exe: str) -> str | None:
    """Windows npm shims are .cmd files; hand subprocess a real path."""
    return shutil.which(exe)


def run_codex(argv: list[str], timeout: int, stdin_text: str | None = None) -> tuple[int, str]:
    """Invoke the codex CLI.

    The prompt goes in over stdin, never as a positional argument. On Windows
    `codex` is an npm `.cmd` shim, so the call has to route through cmd.exe —
    and cmd.exe re-parses the command line, mangling parentheses and other
    metacharacters that occur naturally in an image prompt (`(#000000)`).
    `codex exec -` reads instructions from stdin and sidesteps that entirely.
    """
    exe = resolve("codex")
    if exe is None:
        return 127, "codex not on PATH"
    cmd = [exe, *argv]
    if os.name == "nt" and Path(exe).suffix.lower() in (".cmd", ".bat"):
        cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c", *cmd]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace", input=stdin_text)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"codex timed out after {timeout}s"


def capability() -> tuple[bool, str]:
    """True when the generated-imagery node can run at all."""
    if resolve("codex") is None:
        return False, "codex CLI가 PATH에 없습니다"
    rc, out = run_codex(["features", "list"], 90)
    if rc != 0:
        return False, "`codex features list` 실패"
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] == "image_generation":
            if parts[-1].lower() == "true":
                return True, "image_generation = true"
            return False, "image_generation 플래그가 꺼져 있음 (codex features enable image_generation)"
    return False, "image_generation 플래그를 찾지 못했습니다"


def screen_prompt(prompt: str) -> str | None:
    for pattern, label in FORBIDDEN:
        if re.search(pattern, prompt, re.IGNORECASE):
            return label
    return None


def snapshot() -> set[Path]:
    if not GENERATED_ROOT.is_dir():
        return set()
    return set(GENERATED_ROOT.rglob("ig_*.png"))


def newest(paths: set[Path]) -> Path | None:
    return max(paths, key=lambda p: p.stat().st_mtime) if paths else None


def record(out: Path, prompt: str, full_prompt: str, source: Path) -> None:
    ledger = out.parent / "prompts.json"
    entries = []
    if ledger.is_file():
        try:
            entries = json.loads(ledger.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            entries = []
    entries = [e for e in entries if e.get("file") != out.name]
    entries.append({
        "file": out.name,
        "prompt": prompt,
        "full_prompt": full_prompt,
        "codex_source": str(source),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    ledger.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Codex 이미지 생성 노드")
    ap.add_argument("--check", action="store_true", help="능력 게이트만 확인하고 종료")
    ap.add_argument("--prompt", help="장면 묘사 (한국어/영어 모두 가능)")
    ap.add_argument("--out", help="저장 경로 (.png)")
    ap.add_argument("--override-guardrail", action="store_true",
                    help="금지 패턴 검사를 무시 (연구 산출물처럼 보이는 이미지를 만들 위험)")
    ap.add_argument("--timeout", type=int, default=TIMEOUT_SEC)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ok, reason = capability()
    if args.check:
        print(f"{'OK' if ok else 'DISABLED'}  {reason}")
        if args.json:
            print(json.dumps({"enabled": ok, "reason": reason}, ensure_ascii=False))
        return 0 if ok else 1
    if not ok:
        print(f"[gen_image] 비활성: {reason}")
        print("[gen_image] 이 컷은 Manim 작도로 폴백해야 합니다.")
        if args.json:
            print(json.dumps({"enabled": False, "reason": reason}, ensure_ascii=False))
        return 1

    if not args.prompt or not args.out:
        ap.error("--prompt 와 --out 이 필요합니다 (또는 --check)")

    violation = screen_prompt(args.prompt)
    if violation and not args.override_guardrail:
        print(f"[gen_image] 거부: 요청이 '{violation}'에 해당합니다.")
        print("[gen_image] 연구 산출물처럼 보이는 이미지는 생성하지 않습니다. "
              "논문 figure는 crop_figure.py로 잘라 쓰고, 도식은 Manim으로 작도하세요.")
        return 2

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    full_prompt = STYLE_PREFIX + args.prompt.strip()

    instruction = (
        "Use your image generation tool to create exactly one image from the "
        "description below. Do not write files, do not run shell commands, do not "
        "produce code — only generate the image.\n\n" + full_prompt
    )

    before = snapshot()
    print(f"[gen_image] generating (timeout {args.timeout}s)...", flush=True)
    started = time.time()
    rc, output = run_codex(
        ["exec", "--skip-git-repo-check", "--color", "never", "-s", "read-only",
         "-C", str(out.parent), "-"],
        args.timeout,
        stdin_text=instruction,
    )
    elapsed = round(time.time() - started, 1)

    created = snapshot() - before
    picked = newest(created)
    if picked is None:
        print(f"[gen_image] 실패 ({elapsed}s, rc={rc}) — 새 이미지가 생성되지 않았습니다.")
        for line in output.strip().splitlines()[-12:]:
            print(f"  | {line}")
        print("[gen_image] 프롬프트를 다듬어 재시도하거나(최대 3회) Manim 작도로 폴백하세요.")
        return 1

    shutil.copyfile(picked, out)
    record(out, args.prompt, full_prompt, picked)
    print(f"[gen_image] OK ({elapsed}s) {picked.name} -> {out}")
    print(f"[gen_image] 라벨·수식은 이미지에 넣지 말고 Manim Text/MathTex로 얹으세요.")

    if args.json:
        print(json.dumps({"enabled": True, "out": str(out), "source": str(picked),
                          "elapsed_sec": elapsed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
