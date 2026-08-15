#!/usr/bin/env python
"""편성 템플릿 목록을 읽어 CP0 선택지로 만든다.

CP0의 선택지를 SKILL.md에 적어두면 템플릿을 추가할 때마다 문서를 고쳐야 한다.
그래서 **JSON에서 읽어 만든다** — 파일에 항목을 넣으면 그대로 선택지가 된다.

읽는 순서 (뒤쪽이 앞쪽을 덮어쓴다):
  1. assets/series_templates.json          기본 5종 (스킬과 함께 배포)
  2. assets/series_templates.local.json    사용자가 추가한 것 (있으면)

`.local.json`은 스킬을 업데이트해도 지워지지 않는다. 새 템플릿은 여기에 넣는다.

    python scripts/list_templates.py                # 사람이 읽는 표
    python scripts/list_templates.py --json         # AskUserQuestion용
    python scripts/list_templates.py --check        # 스키마 검사만
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ASSETS = Path(__file__).resolve().parent.parent / "assets"
BASE = ASSETS / "series_templates.json"
LOCAL = ASSETS / "series_templates.local.json"

REQUIRED = ("label", "episodes")
EPISODE_REQUIRED = ("slug", "role", "asks")


def load():
    """기본 + 사용자 추가분을 합친다. 같은 키면 사용자 것이 이긴다."""
    merged: dict = {}
    sources: dict[str, str] = {}
    for path, tag in ((BASE, "base"), (LOCAL, "local")):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for k, v in data.items():
            if k.startswith("_"):
                continue
            merged[k] = v
            sources[k] = tag
    return merged, sources


def validate(templates: dict) -> list[str]:
    problems = []
    for key, t in templates.items():
        if not isinstance(t, dict):
            problems.append(f"{key}: 객체가 아니다")
            continue
        for f in REQUIRED:
            if f not in t:
                problems.append(f"{key}: '{f}' 가 없다")
        eps = t.get("episodes")
        if not isinstance(eps, list) or not eps:
            problems.append(f"{key}: 'episodes' 가 비어 있다")
            continue
        for i, e in enumerate(eps):
            for f in EPISODE_REQUIRED:
                if f not in e:
                    problems.append(f"{key}.episodes[{i}]: '{f}' 가 없다")
    return problems


def as_options(templates: dict) -> list[dict]:
    """AskUserQuestion의 options 형태로. label은 40자를 넘기지 않는다."""
    out = []
    for key, t in templates.items():
        n = len(t["episodes"])
        mins = t.get("total_minutes", "")
        spine = " → ".join(e["role"] for e in t["episodes"])
        why = t.get("recommended_for", "")
        desc = f"{n}편"
        if mins:
            desc += f" · {mins}분"
        desc += f". {spine}."
        if why:
            desc += f" {why}."
        out.append({"key": key, "label": t["label"], "description": desc})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="AskUserQuestion용 options")
    ap.add_argument("--check", action="store_true", help="스키마 검사만")
    a = ap.parse_args()

    templates, sources = load()
    problems = validate(templates)

    if a.check:
        if problems:
            for p in problems:
                print(f"  FAIL  {p}")
            return 1
        print(f"[templates] {len(templates)}종 — 문제 없음"
              f" (기본 {sum(1 for v in sources.values() if v == 'base')},"
              f" 추가 {sum(1 for v in sources.values() if v == 'local')})")
        return 0

    if problems:
        for p in problems:
            print(f"  FAIL  {p}", file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps(as_options(templates), ensure_ascii=False, indent=2))
        return 0

    print(f"편성 템플릿 {len(templates)}종  (기본: {BASE.name}"
          + (f", 추가: {LOCAL.name}" if LOCAL.exists() else "") + ")\n")
    for o in as_options(templates):
        mark = "+" if sources[o["key"]] == "local" else " "
        print(f" {mark} {o['key']:<16} {o['label']}")
        print(f"   {' ' * 16} {o['description']}")
    if not LOCAL.exists():
        print(f"\n새 템플릿은 {LOCAL} 에 같은 형식으로 넣으면"
              "\n스킬을 업데이트해도 남고, 선택지에 자동으로 뜬다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
