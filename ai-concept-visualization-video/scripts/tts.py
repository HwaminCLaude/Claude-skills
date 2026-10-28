"""큐마다 edge-tts 로 음성을 합성하고 실측 길이를 적는다(TTS 모드, 3.6단계).

    python tts.py --episode <dir> [--voice ko-KR-HyunsuMultilingualNeural] [--force]

- shots.json 큐마다 `say`(없으면 `t`)를 합성해 <dir>/tts/<id>.mp3 를 만든다.
- 길이(ffprobe)를 <dir>/tts/durs.json ({id: 초}) 에 shots.json 큐 순서로 쓴다.
  다음 단계 `cues.py --episode <dir>` 가 이 값을 큐 길이로 쓴다.
- 이미 있는 mp3 는 건너뛴다. 단 tts/.cache.json 에 적힌 합성 입력(문장, 목소리)이
  지금 대본과 다르거나 기록이 없으면 다시 만든다. 대본을 고친 큐만 다시 합성된다.
  (mp3 존재만 보고 건너뛰면, 문장을 고쳐도 옛 음성이 남고 자막만 새 문장이 된다.)
  --force 면 전부 다시 만든다.
- 이 파이썬에 edge_tts 가 없으면 uv 임시 환경(`uv run --no-project --with edge-tts`)으로
  자기 자신을 다시 실행한다. 프로젝트 venv 를 바꾸지 않는다.
- 합성은 순서대로 한다(병렬로 보내면 서비스가 막는다). 실패하면 3번까지 다시 시도한다.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cues as _cues  # noqa: E402

DEFAULT_VOICE = "ko-KR-HyunsuMultilingualNeural"
CACHE_NAME = ".cache.json"
DURS_NAME = "durs.json"
REEXEC_ENV = "VIZ_TTS_REEXEC"
RETRIES = 3


def _utf8_stdout() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _reexec_with_uv(argv: list[str]) -> int:
    """edge_tts 가 없을 때 uv 임시 환경에서 이 스크립트를 다시 돌린다."""
    uv = shutil.which("uv")
    if uv is None or os.environ.get(REEXEC_ENV):
        print("FAIL edge-tts not available. Install it into the project venv "
              "(`uv pip install --python <PY> edge-tts`) or put uv on PATH.")
        return 1
    env = dict(os.environ)
    env[REEXEC_ENV] = "1"
    env["PYTHONUTF8"] = "1"  # 한글 사용자 경로의 uv 캐시 .pth 를 cp949 로 읽다 죽는 것을 막는다
    cmd = [uv, "run", "--no-project", "--python", "3.10", "--with", "edge-tts",
           "python", str(Path(__file__).resolve()), *argv]
    print("edge_tts not in this python; running in a uv temp env", flush=True)
    return subprocess.run(cmd, env=env).returncode


def probe_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True, check=True)
    return round(float(out.stdout.strip()), 3)


def text_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def cue_texts(shots: dict) -> list[tuple[str, str]]:
    """[(id, 합성할 문장)] — say 가 비어 있으면 t."""
    out = []
    for _, cue in _cues.iter_cues(shots):
        text = (cue.get("say") or cue.get("t") or "").strip()
        out.append((cue["id"], text))
    return out


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def stale_reason(clip: Path, record: dict | None, text: str, voice: str, force: bool) -> str | None:
    if not clip.is_file() or clip.stat().st_size == 0:
        return "new"
    if force:
        return "--force"
    if not record:
        return "no cache record"
    if record.get("text") != text_key(text):
        return "text changed"
    if record.get("voice") != voice:
        return "voice changed"
    return None


def synth(edge_tts, text: str, voice: str, out: Path) -> None:
    tmp = out.with_suffix(".part.mp3")
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            asyncio.run(edge_tts.Communicate(text, voice).save(str(tmp)))
            if tmp.is_file() and tmp.stat().st_size > 0:
                tmp.replace(out)
                return
            last = RuntimeError("empty audio")
        except Exception as e:  # 네트워크·서비스 오류
            last = e
        time.sleep(1.5 * attempt)
    tmp.unlink(missing_ok=True)
    raise RuntimeError(f"edge-tts failed after {RETRIES} tries: {last}")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _utf8_stdout()
    ap = argparse.ArgumentParser(description="큐마다 edge-tts 합성 → tts/<id>.mp3, tts/durs.json")
    ap.add_argument("--episode", required=True, help="에피소드 폴더(shots.json 이 있는 곳)")
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--force", action="store_true", help="있는 mp3 도 전부 다시 합성")
    args = ap.parse_args(argv)

    ep = Path(args.episode).resolve()
    shots_path = ep / "shots.json"
    if not shots_path.is_file():
        print(f"FAIL {shots_path} not found")
        return 1
    shots = json.loads(shots_path.read_text(encoding="utf-8"))
    items = cue_texts(shots)
    if not items:
        print("FAIL shots.json has no cues")
        return 1
    empty = [cid for cid, text in items if not text]
    if empty:
        print(f"FAIL cues with no text: {', '.join(empty)}")
        return 1
    if shots.get("mode", "silent") != "tts":
        print(f"WARN shots.json mode is {shots.get('mode', 'silent')!r}; "
              "cues.py uses durs.json only in mode \"tts\"")

    tts_dir = ep / "tts"
    tts_dir.mkdir(exist_ok=True)
    cache_path = tts_dir / CACHE_NAME
    cache = _load_json(cache_path)

    todo = [(cid, text, reason) for cid, text in items
            if (reason := stale_reason(tts_dir / f"{cid}.mp3", cache.get(cid), text,
                                       args.voice, args.force))]
    if todo:
        try:
            import edge_tts  # noqa: PLC0415
        except ImportError:
            return _reexec_with_uv(argv)
        for i, (cid, text, reason) in enumerate(todo, 1):
            try:
                synth(edge_tts, text, args.voice, tts_dir / f"{cid}.mp3")
            except RuntimeError as e:
                cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"FAIL {cid} {e}")
                return 1
            cache[cid] = {"text": text_key(text), "voice": args.voice}
            print(f"synth {i}/{len(todo)} {cid} ({reason})", flush=True)
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    durs = {cid: probe_duration(tts_dir / f"{cid}.mp3") for cid, _ in items}
    (tts_dir / DURS_NAME).write_text(json.dumps(durs, ensure_ascii=False, indent=1), encoding="utf-8")

    total = sum(durs.values())
    print(f"synthesized {len(todo)}, kept {len(items) - len(todo)}, voice {args.voice}")
    print(f"TOTAL\t{len(durs)} cues\t{total:.2f}s")
    print(f"wrote {tts_dir / DURS_NAME}")
    print(f"next: cues.py --episode \"{ep}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
