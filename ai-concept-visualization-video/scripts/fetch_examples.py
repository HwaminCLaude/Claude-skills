"""예시 코퍼스를 받는다(선택, 참고 전용).

원본 공개 저장소 두 곳의 고정 커밋에서 장면 코드와 raenimgl 소스를 받아 `references/example_corpus/`에 둔다.
씬을 짤 때 `references/flow-grammar.md`의 `파일:줄` 예시를 열어 보는 자료다. 실행하지 않고, 에피소드 폴더에
복사하지 않는다. 원본 저장소에 라이선스 파일이 없어 이 스킬에는 넣지 않았다(`references/example-corpus.md`).

    python fetch_examples.py            # 이미 있으면 건너뜀
    python fetch_examples.py --force    # 다시 받아 바꿔 끼움(받기에 실패하면 있던 코퍼스는 그대로)

받는 구조:
- `<topic>.py`     원본 `src/<topic>/main.py` 그대로(줄 번호 같음)
- `raenimgl/*.py`  raenimgl 패키지 소스(이미지 같은 에셋은 받지 않음)
git 이 PATH 에 있어야 한다. 끝 줄은 PASS/SKIP/FAIL.
"""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCENES = ("https://github.com/CodingVillainKor/manimgl-imcommit",
          "4c5cf5cb96a1e8f0be66410f1e95bc4871fe9ea0")
RAENIMGL = ("https://github.com/CodingVillainKor/raenimgl.git",
            "089d4ffec3cae45877cecd68ab143a5ab47190b3")
DEST = Path(__file__).resolve().parents[1] / "references" / "example_corpus"
PARTIAL = DEST.with_name("example_corpus.partial")


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _checkout(url: str, commit: str, into: Path) -> None:
    """그 커밋 하나만 얕게 받는다."""
    into.mkdir(parents=True)
    _git(into, "init", "-q")
    _git(into, "remote", "add", "origin", url)
    _git(into, "fetch", "-q", "--depth", "1", "origin", commit)
    _git(into, "checkout", "-q", "FETCH_HEAD")


def _rmtree(path: Path) -> None:
    def onerror(func, p, _exc):  # Windows: git 객체 파일은 읽기 전용이라 지우기 전에 쓰기 권한을 준다
        os.chmod(p, stat.S_IWRITE)
        func(p)
    if path.exists():
        shutil.rmtree(path, onerror=onerror)


def main() -> int:
    ap = argparse.ArgumentParser(description="예시 코퍼스 받기(git 필요)")
    ap.add_argument("--force", action="store_true", help="이미 있어도 다시 받아 바꿔 끼운다")
    a = ap.parse_args()
    if shutil.which("git") is None:
        print("FAIL git not found on PATH")
        return 2
    if DEST.exists() and not a.force:
        print(f"SKIP 이미 있음: {DEST} (다시 받으려면 --force)")
        return 0

    tmp = Path(tempfile.mkdtemp(prefix="example_corpus_"))
    try:
        _checkout(*SCENES, tmp / "scenes")
        _checkout(*RAENIMGL, tmp / "raenimgl")
        scenes = sorted((tmp / "scenes" / "src").glob("*/main.py"))
        libs = sorted((tmp / "raenimgl" / "raenimgl").glob("*.py"))
        if not scenes or not libs:
            print(f"FAIL 예상한 구조가 아님: 장면 {len(scenes)}개, raenimgl {len(libs)}개")
            return 1
        _rmtree(PARTIAL)                      # 지난번에 끊긴 사본이 있으면 버린다
        (PARTIAL / "raenimgl").mkdir(parents=True)
        for p in scenes:
            shutil.copyfile(p, PARTIAL / f"{p.parent.name}.py")
        for p in libs:
            shutil.copyfile(p, PARTIAL / "raenimgl" / p.name)
        _rmtree(DEST)                         # 다 받은 뒤에만 바꿔 끼운다
        PARTIAL.replace(DEST)
    except subprocess.CalledProcessError as e:
        print(f"FAIL git {' '.join(e.cmd[1:3])}: {(e.stderr or '').strip()[:200]}")
        return 1
    finally:
        _rmtree(tmp)
        _rmtree(PARTIAL)
    print(f"PASS 장면 {len(scenes)}편 + raenimgl {len(libs)}개 → {DEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
