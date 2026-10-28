"""Task 5: 참고 자료와 예시 코퍼스 검사.

예시 코퍼스(references/example_corpus/)는 이 스킬에 들어 있지 않고 scripts/fetch_examples.py로 받는다.
받기 전에는 코퍼스를 여는 검사를 건너뛴다.
"""
import re
from pathlib import Path

import pytest

SK = Path(__file__).resolve().parents[1]
REF = SK / "references"
CORPUS = REF / "example_corpus"
needs_corpus = pytest.mark.skipif(not (CORPUS / "lora1.py").is_file(),
                                  reason="예시 코퍼스 없음 — python scripts/fetch_examples.py 로 받는다")

DOCS = [
    "flow-grammar.md",
    "design-system.md",
    "onscreen-text.md",
    "captions.md",
    "narration-voice.md",
    "raenimgl-api.md",
    "troubleshooting.md",
    "example-corpus.md",
]

RELS = ["detail", "next", "structure", "carry", "aside", "change",
        "build", "point", "new", "hook", "quote", "chapter"]

# 예: lora1.py:127, linearAttn.py:342, raenimgl/scene.py:10-20
REF_RE = re.compile(r"([A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*\.py):(\d+)(?:-(\d+))?")


def _read(name):
    return (REF / name).read_text(encoding="utf-8")


def test_docs_exist():
    missing = [d for d in DOCS if not (REF / d).is_file()]
    assert not missing, f"없는 문서: {missing}"
    for d in DOCS:
        assert len(_read(d).strip()) > 200, f"{d}가 비어 있음"


def test_example_corpus_doc_pins_sources():
    doc = _read("example-corpus.md")
    assert "4c5cf5cb96a1e8f0be66410f1e95bc4871fe9ea0" in doc
    assert "089d4ffec3cae45877cecd68ab143a5ab47190b3" in doc
    fetch = (SK / "scripts" / "fetch_examples.py").read_text(encoding="utf-8")
    assert "4c5cf5cb96a1e8f0be66410f1e95bc4871fe9ea0" in fetch
    assert "089d4ffec3cae45877cecd68ab143a5ab47190b3" in fetch


@needs_corpus
def test_corpus_has_33_scripts():
    top = list(CORPUS.glob("*.py"))
    assert len(top) >= 33, len(top)
    assert list((CORPUS / "raenimgl").glob("*.py")), "raenimgl 소스 없음"


@needs_corpus
def test_corpus_has_no_image_assets():
    exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp4", ".bmp"}
    bad = [p for p in CORPUS.rglob("*") if p.suffix.lower() in exts]
    assert not bad, bad


def test_flow_grammar_mentions_all_rels():
    text = _read("flow-grammar.md")
    missing = [r for r in RELS if f"`{r}`" not in text]
    assert not missing, missing


def _sections(text):
    """'## `rel`' 머리로 절을 나눈다."""
    out = {}
    parts = re.split(r"^## `([a-z]+)`", text, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        out[parts[i]] = parts[i + 1]
    return out


def test_flow_grammar_each_rel_has_examples():
    secs = _sections(_read("flow-grammar.md"))
    for r in RELS:
        assert r in secs, f"'## `{r}`' 절 없음"
        n = len(REF_RE.findall(secs[r]))
        assert n >= 2, f"{r}: 예시 {n}개"


@needs_corpus
def test_flow_grammar_refs_resolve():
    refs = REF_RE.findall(_read("flow-grammar.md"))
    assert len(refs) >= 24, len(refs)
    bad = []
    for path, a, b in refs:
        f = CORPUS / path
        if not f.is_file():
            bad.append(f"{path}: 파일 없음")
            continue
        n = len(f.read_text(encoding="utf-8").splitlines())
        lo = int(a)
        hi = int(b) if b else lo
        if not (1 <= lo <= hi <= n):
            bad.append(f"{path}:{a}{'-' + b if b else ''} (줄 수 {n})")
    assert not bad, bad
