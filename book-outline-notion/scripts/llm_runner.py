"""
llm_runner.py — LLM 배치 실행기. Codex CLI 우선, 없으면 서브에이전트에 위임.

백엔드 (config.LLM_BACKEND)
  auto  : codex CLI 가 있으면 codex, 없으면 프롬프트 파일만 쓰고 종료(=agent 위임)
  codex : codex 강제 (없으면 실패)
  agent : 항상 프롬프트 파일만 쓴다

**agent 폴백 방식**
배치마다 `_output/prompts/<key>.md` 를 쓴다. Claude 가 그 프롬프트를 읽어
서브에이전트에 맡기고 결과 JSON 을 `_output/gen/<key>.json` 으로 저장하면,
스크립트를 다시 실행했을 때 그대로 이어진다(모든 단계가 산출 파일 존재로 멱등).

Codex CLI 실무 주의 — 전부 실측으로 확인한 것:
  1. **프롬프트는 stdin 으로** 넘긴다. `-i/--image` 가 가변 인자라 뒤에 붙인 위치
     인자(프롬프트)까지 이미지로 삼켜 "No prompt provided via stdin" 으로 실패한다.
  2. 결과는 **`-o/--output-last-message <FILE>`** 로 파일로 받는다. stdout 에는
     훅 로그(`hook: SessionStart` 등)가 섞여 파싱이 깨진다.
  3. Windows 의 codex 는 npm 배치파일(codex.CMD)이라 `shutil.which` 로 실경로를
     해석해야 subprocess 가 찾는다(config.resolve_codex).
  4. `--output-schema <JSON Schema 파일>` 로 응답 구조를 강제하면 파싱 실패가 없다.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as C

_print_lock = threading.Lock()


def log(msg: str):
    with _print_lock:
        print(msg, flush=True)


def backend() -> str:
    """실제로 쓸 백엔드를 정한다."""
    if C.LLM_BACKEND == "agent":
        return "agent"
    if C.LLM_BACKEND == "codex":
        if not C.CODEX_BIN:
            print("[ERROR] BOOK_LLM_BACKEND=codex 인데 codex CLI 를 못 찾았습니다.",
                  file=sys.stderr)
            sys.exit(1)
        return "codex"
    return "codex" if C.CODEX_BIN else "agent"


def write_schema(name: str, schema: dict) -> Path:
    p = C.SCHEMA_DIR / f"{name}.json"
    p.write_text(json.dumps(schema, ensure_ascii=False, indent=1), encoding="utf-8")
    return p


def _extract_json(raw: str) -> dict | None:
    """결과 텍스트에서 JSON 객체를 뽑는다(코드펜스가 붙는 경우 대비)."""
    raw = (raw or "").strip()
    if not raw:
        return None
    fence = re.search(r"```(?:json)?\s*(.+?)```", raw, re.S)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def run_batch(prompt: str, out_json: Path, schema_path: Path | None = None,
              images: list[Path] | None = None, timeout: int = 900,
              model: str | None = None) -> dict | None:
    """codex exec 한 번 실행 → 파싱된 dict. 산출 파일이 있으면 재사용(멱등)."""
    if out_json.exists():
        try:
            return json.loads(out_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            out_json.unlink()          # 깨진 산출물은 버리고 다시 만든다

    if not C.CODEX_BIN:
        return None

    last_msg = out_json.with_suffix(".raw.txt")
    cmd = [C.CODEX_BIN, "exec", "--skip-git-repo-check", "--ephemeral",
           "-s", "read-only", "-o", str(last_msg)]
    if schema_path:
        cmd += ["--output-schema", str(schema_path)]
    if model:
        cmd += ["-m", model]
    for img in (images or []):
        cmd += ["-i", str(img)]

    try:
        subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout,
                       cwd=str(C.ROOT))
    except subprocess.TimeoutExpired:
        log(f"   [TIMEOUT] {out_json.name}")
        return None
    except OSError as e:
        log(f"   [ERROR] codex 실행 실패: {e}")
        return None

    if not last_msg.exists():
        log(f"   [FAIL] 결과 파일 없음: {out_json.name}")
        return None
    data = _extract_json(last_msg.read_text(encoding="utf-8"))
    if data is None:
        log(f"   [FAIL] JSON 파싱 실패: {out_json.name}")
        return None
    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    last_msg.unlink(missing_ok=True)
    return data


def dump_prompts(jobs: list[dict], stage: str) -> list[Path]:
    """agent 폴백: 미완료 배치의 프롬프트를 파일로 떨군다."""
    written = []
    for j in jobs:
        if j["out_json"].exists():
            continue
        p = C.PROMPT_DIR / f"{j['key']}.md"
        head = [f"<!-- stage: {stage} -->",
                f"<!-- 결과를 이 경로에 JSON 으로 저장할 것: {j['out_json']} -->"]
        for i in (j.get("images") or []):
            head.append(f"<!-- 첨부 이미지(Read 도구로 직접 볼 것): {i} -->")
        p.write_text("\n".join(head) + "\n\n" + j["prompt"], encoding="utf-8")
        written.append(p)
    return written


def run_parallel(jobs: list[dict], workers: int = 4, stage: str = "llm") -> dict:
    """jobs: [{key, prompt, out_json, schema_path?, images?, timeout?}] 실행.

    codex 백엔드면 동시 실행하고, agent 백엔드면 프롬프트 파일만 쓰고 빈 결과를 준다.
    """
    if backend() == "agent":
        files = dump_prompts(jobs, stage)
        if files:
            log(f"\n[agent 위임] codex CLI 가 없어 프롬프트 {len(files)}개를 "
                f"{C.PROMPT_DIR} 에 저장했습니다.")
            log("  Claude 가 각 프롬프트를 서브에이전트(executor)에 맡기고, 결과 JSON 을")
            log(f"  {C.GEN_DIR}/<프롬프트와 같은 이름>.json 으로 저장한 뒤")
            log("  이 스크립트를 다시 실행하면 이어집니다.")
        return {}

    results: dict[str, dict | None] = {}
    done, total = 0, len(jobs)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(run_batch, j["prompt"], j["out_json"],
                            j.get("schema_path"), j.get("images"),
                            j.get("timeout", 900)): j for j in jobs}
        for fut in as_completed(futs):
            j = futs[fut]
            try:
                results[j["key"]] = fut.result()
            except Exception as e:                     # noqa: BLE001
                log(f"   [ERROR] {j['key']}: {e}")
                results[j["key"]] = None
            done += 1
            ok = sum(1 for v in results.values() if v)
            log(f"   [{done}/{total}] {j['key']} "
                f"{'OK' if results[j['key']] else 'FAIL'} (성공 {ok})")
    return results
