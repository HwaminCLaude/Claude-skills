"""로그인 없이 열리는 공개 웹 페이지를 헤드리스 Chromium으로 찍는다(1600x900, 주소창 없음).

사용법(이 PC의 python, playwright + chromium 필요):
  python tools/webshot.py <URL> <레슨폴더>/_raw/sNN-<무엇>.png --step S03 [--note "무엇이 보이는지"]
         [--wait-text "Model card"] [--click "Reject all"] [--hide "#cookie-banner"] [--scroll-to "Files and versions"]
         [--full-page] [--kind current] [--no-log]

- 저장 경로가 레슨의 _raw/ 안이면 _raw/capture-log.jsonl 에 한 줄을 더한다(--no-log로 끔). file 값은 _raw 안의
  파일 이름이라 redact-spec.json의 키와 같다(check_lesson.py가 evidence-manifest를 만들 때 이 값으로 찾는다).
- 쿠키·동의 배너는 개인정보를 덜 주는 쪽 버튼(예: "Reject all", "Necessary only")의 글자를 --click으로 누르거나
  --hide(CSS 선택자)로 가린다. 로그인·결제·토큰이 필요한 페이지는 찍지 않는다 — 주소에 token=·key=·password=·
  secret= 이 있으면 멈춘다. 찍은 그림도 redact-spec.json에 넣어 redact.py를 거쳐야 공개된다.
- README 14절에 링크할 공식 문서도 이 도구로 한 번 열어(제목이 맞는지) 확인할 수 있다.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서도 한글·기호 출력

VIEWPORT = {"width": 1600, "height": 900}


def main(argv=None):
    ap = argparse.ArgumentParser(description="공개 웹 페이지 캡처(1600x900) + capture-log 한 줄")
    ap.add_argument("url")
    ap.add_argument("out", help="저장할 PNG 경로(레슨의 _raw/sNN-<무엇>.png)")
    ap.add_argument("--step", default="", help="playbook 단계 ID(예: S03)")
    ap.add_argument("--kind", default="current", help="current/click/result/execution/verification")
    ap.add_argument("--note", default="", help="그림에 무엇이 보이는지(capture-log의 note)")
    ap.add_argument("--wait-text", action="append", default=[], help="이 글자가 보일 때까지 기다린다(여러 번 가능)")
    ap.add_argument("--click", action="append", default=[], help="찍기 전에 이 글자의 버튼을 누른다(배너 닫기, 여러 번 가능)")
    ap.add_argument("--hide", action="append", default=[], help="찍기 전에 이 CSS 선택자 요소를 숨긴다(여러 번 가능)")
    ap.add_argument("--scroll-to", default=None, help="이 글자가 있는 곳까지 스크롤")
    ap.add_argument("--full-page", action="store_true", help="페이지 전체(세로로 긴 그림)")
    ap.add_argument("--timeout", type=int, default=30000, help="ms")
    ap.add_argument("--no-log", action="store_true", help="capture-log.jsonl에 쓰지 않는다")
    a = ap.parse_args(argv)

    if not re.match(r"^https?://", a.url):
        print("http(s) 주소만 찍는다:", a.url)
        return 2
    if re.search(r"[?&#](token|key|api_key|password|secret)=", a.url, re.I):
        print("주소에 비밀값으로 보이는 쿼리가 있어 멈춘다(로그인·토큰이 필요한 페이지는 찍지 않는다)")
        return 2

    from playwright.sync_api import sync_playwright

    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1, locale="en-US")
            page = ctx.new_page()
            page.goto(a.url, wait_until="domcontentloaded", timeout=a.timeout)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass                                       # 계속 통신하는 페이지도 있다
            for t in a.wait_text:
                page.get_by_text(t).first.wait_for(timeout=a.timeout)
            for t in a.click:
                btn = page.get_by_role("button", name=t)
                if btn.count():
                    btn.first.click(timeout=5000)
                    page.wait_for_timeout(800)
                else:
                    print(f"note: '{t}' 버튼이 없어 누르지 않았다")
            for sel in a.hide:
                page.add_style_tag(content=f"{sel} {{ display: none !important; }}")
            if a.scroll_to:
                page.get_by_text(a.scroll_to).first.scroll_into_view_if_needed(timeout=a.timeout)
            page.wait_for_timeout(800)
            page.screenshot(path=str(out), full_page=a.full_page)
            title = page.title()
        finally:
            browser.close()
    print(f"saved {out} (title: {title})")

    if not a.no_log and out.parent.name == "_raw":
        entry = {"file": out.name, "step": a.step, "kind": a.kind, "note": a.note or title, "source": "real-capture",
                 "tool": "tools/webshot.py (headless Chromium 1600x900" + (", full page" if a.full_page else "") + ")",
                 "pod": None, "url": a.url,
                 "copied_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
        with (out.parent / "capture-log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print("capture-log.jsonl += " + out.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
