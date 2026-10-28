"""Task 6: SKILL.md와 논문·코드 입력 도구 검사."""
import re
from pathlib import Path

SK = Path(__file__).resolve().parents[1]
SKILL_MD = SK / "SKILL.md"


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path}에 frontmatter가 없다"
    block = text.split("---", 2)[1]
    out = {}
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def _body() -> str:
    return SKILL_MD.read_text(encoding="utf-8").split("---", 2)[2]


def test_frontmatter_name():
    fm = _frontmatter(SKILL_MD)
    assert fm.get("name") == "ai-concept-visualization-video"
    assert fm.get("description"), "description이 비어 있다"


# 표의 `scripts/x.py`와 명령 줄의 "SK\scripts\x.py"를 모두 잡는다.
SCRIPT_REF = re.compile(r"scripts[/\\]+([A-Za-z0-9_]+\.py)")


def test_script_ref_regex_matches_both_separators():
    text = r'a `scripts/lint.py` b "SK\scripts\cues.py" c C:\\x\\scripts\\tts.py'
    assert set(SCRIPT_REF.findall(text)) == {"lint.py", "cues.py", "tts.py"}


def test_scripts_in_body_exist():
    names = set(SCRIPT_REF.findall(_body()))
    assert names, "본문에 scripts/*.py 참조가 없다"
    missing = sorted(n for n in names if not (SK / "scripts" / n).is_file())
    assert not missing, f"없는 스크립트: {missing}"
    # 명령 줄의 역슬래시 경로도 실제로 검사 대상에 들어간다
    backslash = set(re.findall(r"scripts\\([A-Za-z0-9_]+\.py)", _body()))
    assert backslash, "본문에 역슬래시 스크립트 경로가 없다"
    assert backslash <= names


def test_code_input_documented():
    body = _body()
    assert (SK / "scripts" / "parse_code.py").is_file()
    assert "scripts/parse_code.py" in body, "스크립트 표에 parse_code.py가 없다"
    assert r"scripts\parse_code.py" in body and "--input" in body, "1단계에 코드 입력 명령이 없다"


def test_references_in_body_exist():
    names = set(re.findall(r"references/([A-Za-z0-9_\-/]+\.md)", _body()))
    assert names, "본문에 references/*.md 참조가 없다"
    missing = sorted(n for n in names if not (SK / "references" / n).is_file())
    assert not missing, f"없는 참고 문서: {missing}"

