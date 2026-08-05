"""
00_preflight.py — 환경 점검 + **PDF 구조 자동 탐지**.

새 PDF에 이 스킬을 적용할 때 가장 먼저 실행한다. 목차가 몇 쪽부터 몇 쪽인지,
본문이 어디서 시작하는지, 인쇄 쪽번호와 PDF 쪽번호가 어긋나는지를 스스로 찾아
**그대로 복사해 쓸 환경변수**를 출력한다.

점검: PDF · PyMuPDF/pdfplumber · Notion 토큰/DB 접근 · rclone · LLM 백엔드
종료코드 0 = 진행 가능 / 1 = 조치 필요
"""
from __future__ import annotations

import collections
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as C

OK, MISSING, INFO = [], [], {}
PAGE_ONLY = re.compile(r"^\d{1,4}$")


def ok(msg: str):
    OK.append(msg)
    print(f"  [OK]   {msg}")


def bad(msg: str, fix: str):
    MISSING.append((msg, fix))
    print(f"  [MISS] {msg}\n         > {fix}")


# ── 1. 입력 ────────────────────────────────────────────────
def check_files():
    print("\n== 1. 입력 파일 ==")
    if not C.ROOT.exists():
        bad(f"작업 폴더 없음: {C.ROOT}", "ASK> BOOK_ROOT 를 올바른 폴더로 지정")
        return
    if not C.PDF_PATH.exists():
        bad(f"PDF 없음: {C.PDF_PATH}", "ASK> BOOK_PDF 로 대상 PDF 지정")
        return
    ok(f"PDF: {C.PDF_PATH.name} ({C.PDF_PATH.stat().st_size / 1024 / 1024:.1f}MB)")


def check_pkgs():
    print("\n== 2. Python 패키지 ==")
    try:
        import fitz
        ver = getattr(fitz, "__version__", None) or getattr(fitz, "VersionBind", "?")
        ok(f"PyMuPDF {ver}")
    except Exception as e:
        bad(f"PyMuPDF 없음 ({e})", "FIX> pip install PyMuPDF")
    try:
        import pdfplumber
        ok(f"pdfplumber {pdfplumber.__version__}")
    except Exception as e:
        bad(f"pdfplumber 없음 ({e})", "FIX> pip install pdfplumber")


# ── 3. PDF 구조 자동 탐지 ──────────────────────────────────
def detect_structure():
    """목차 쪽 범위 · 본문 범위 · 쪽번호 오프셋 · 머리말 위치를 찾는다."""
    print("\n== 3. PDF 구조 탐지 ==")
    try:
        import fitz
    except Exception as e:
        bad(f"PyMuPDF 로드 실패 ({e})", "FIX> pip install PyMuPDF")
        return
    doc = fitz.open(C.PDF_PATH)
    n = doc.page_count
    ok(f"총 {n}쪽")

    # (a) 목차 페이지 = '번호 있는 제목' + '쪽번호' 쌍이 3개 이상인 쪽
    toc_score = {}
    for i in range(min(n, 80)):
        lines = [l.strip() for l in doc[i].get_text("text").splitlines() if l.strip()]
        pairs = sum(1 for a, b in zip(lines, lines[1:])
                    if C.match_level(a) and PAGE_ONLY.fullmatch(b))
        if pairs >= 3:
            toc_score[i + 1] = pairs

    if not toc_score:
        bad("목차 페이지를 찾지 못했습니다",
            "ASK> 목차 쪽 범위를 BOOK_TOC_FIRST/BOOK_TOC_LAST 로 직접 지정")
        doc.close()
        return

    # 가장 긴 연속 구간이 본목차. 뒤따르는 표목차·그림목차는 끊긴 구간으로 분리된다.
    pages = sorted(toc_score)
    runs, cur = [], [pages[0]]
    for p in pages[1:]:
        if p == cur[-1] + 1:
            cur.append(p)
        else:
            runs.append(cur)
            cur = [p]
    runs.append(cur)
    runs.sort(key=len, reverse=True)
    toc_first, toc_last = runs[0][0], runs[0][-1]
    ok(f"목차 {toc_first}~{toc_last}쪽 "
       f"(항목쌍 {sum(toc_score[p] for p in runs[0])}개)")
    if len(runs) > 1:
        others = ", ".join(f"{r[0]}~{r[-1]}" for r in runs[1:4])
        print(f"         (표·그림 목차로 보이는 구간: {others} — 본목차에서 제외됨)")
    INFO["BOOK_TOC_FIRST"], INFO["BOOK_TOC_LAST"] = toc_first, toc_last

    # (b) 인쇄 쪽번호 오프셋 — 여러 항목의 **최빈값**으로 정한다.
    #     첫 항목 하나만 보면 표목차·그림목차 페이지에 같은 제목이 있어 오판한다
    #     (실측: 본문 43쪽인데 표목차 24쪽으로 잡혀 오프셋 -19 가 나왔다).
    lines = []
    for p in range(toc_first, toc_last + 1):
        lines += [l.strip() for l in doc[p - 1].get_text("text").splitlines() if l.strip()]
    entries = []
    for a, b in zip(lines, lines[1:]):
        hit = C.match_level(a)
        if hit and PAGE_ONLY.fullmatch(b):
            entries.append((hit, int(b)))
    # 목차·표목차·그림목차 구간을 모두 지난 뒤부터 찾는다
    search_from = max(r[-1] for r in runs)
    votes = collections.Counter()
    for (lv, num, title), printed in entries[:40]:
        want = C.norm(C.prefix_for(lv, num) + title)
        if len(want) < 6:
            continue
        for i in range(search_from, n):
            if want in C.norm(doc[i].get_text("text")):
                votes[(i + 1) - printed] += 1
                break
    body_first = None
    if votes:
        offset, agree = votes.most_common(1)[0]
        body_first = entries[0][1] + offset
        ok(f"본문 시작 {body_first}쪽 (인쇄 쪽번호 오프셋 {offset}, "
           f"표본 {sum(votes.values())}개 중 {agree}개 일치)")
        if offset != 0:
            print(f"         ⚠ 오프셋이 0이 아닙니다 → BOOK_PAGE_OFFSET={offset}")
            INFO["BOOK_PAGE_OFFSET"] = offset
        if agree < sum(votes.values()) * 0.6:
            print(f"         ⚠ 일치율이 낮습니다({dict(votes)}). "
                  f"BOOK_BODY_FIRST 를 직접 확인하세요.")
    if body_first is None:
        bad("본문 시작 쪽을 찾지 못했습니다", "ASK> BOOK_BODY_FIRST 를 직접 지정")
    else:
        INFO["BOOK_BODY_FIRST"] = body_first

    # (c) 본문 끝 = 뒤에서부터 본문 분량(200자+)이 있는 마지막 쪽
    body_last = n
    for i in range(n - 1, -1, -1):
        if len(doc[i].get_text("text").strip()) > 200:
            body_last = i + 1
            break
    ok(f"본문 끝 {body_last}쪽")
    INFO["BOOK_BODY_LAST"] = body_last

    # (d) 머리말/쪽번호 y 위치 실측 → 필터 경계가 맞는지 확인
    ys = collections.Counter()
    for i in range((body_first or 1) - 1, min(body_last, n), 17):
        for b in doc[i].get_text("blocks"):
            if b[6] == 0:
                ys[round(b[1])] += 1
    tops = [y for y, c in ys.items() if y < 120 and c > 3]
    bots = [y for y, c in ys.items() if y > 700 and c > 3]
    if tops and bots:
        ok(f"머리말 y≈{min(tops)} / 쪽번호 y≈{max(bots)} "
           f"(현재 필터 {C.HEADER_Y:.0f}~{C.FOOTER_Y:.0f})")
        if min(tops) >= C.HEADER_Y or max(bots) <= C.FOOTER_Y:
            print(f"         ⚠ 필터가 머리말/쪽번호를 못 걸러낼 수 있습니다 → "
                  f"BOOK_HEADER_Y={min(tops) + 8:.0f} "
                  f"BOOK_FOOTER_Y={max(bots) - 8:.0f} 권장")

    # (e) 목차 노드 수 미리 세기 → 01단계 게이트 값
    cnt, i = 0, 0
    while i < len(lines):
        if PAGE_ONLY.fullmatch(lines[i]):
            i += 1
            continue
        if C.match_level(lines[i]) and i + 1 < len(lines) \
                and PAGE_ONLY.fullmatch(lines[i + 1]):
            cnt += 1
            i += 2
        else:
            i += 1
    ok(f"목차 항목 {cnt}개 예상")
    INFO["BOOK_EXPECTED_NODES"] = cnt

    lv = collections.Counter()
    i = 0
    while i < len(lines):
        hit = C.match_level(lines[i])
        if hit and i + 1 < len(lines) and PAGE_ONLY.fullmatch(lines[i + 1]):
            lv[hit[0]] += 1
            i += 2
        else:
            i += 1
    print(f"         레벨별: {dict(sorted(lv.items()))}")
    upto = sum(v for k, v in lv.items() if k <= C.MAX_DB_LEVEL)
    print(f"         → DB 행 {upto}개 (레벨 {C.MAX_DB_LEVEL}까지), "
          f"본문 흡수 {cnt - upto}개")
    doc.close()


# ── 4. Notion ──────────────────────────────────────────────
def check_notion():
    print("\n== 4. Notion ==")
    if not C.NOTION_DB_ID:
        bad("BOOK_DB_ID 가 비어 있습니다",
            "ASK> 대상 DB URL 을 BOOK_DB_ID 로 지정 (URL 그대로 넣어도 됨)")
        return
    try:
        import notion_api as N
    except Exception as e:
        bad(f"notion_api 로드 실패: {e}", "FIX> scripts/notion_api.py 확인")
        return
    try:
        u = N.me()
        ws = (u.get("bot") or {}).get("workspace_name") or u.get("name")
        ok(f"토큰 유효 — 워크스페이스: {ws}")
    except Exception as e:
        bad(f"토큰 인증 실패: {e}", "ASK> .env 의 Notion 통합 토큰 확인")
        return
    src = C.NOTION_DS_ID
    try:
        db = N.get_database(C.NOTION_DB_ID)
        title = "".join(t.get("plain_text", "") for t in db.get("title", []))
        ok(f"DB 접근 가능: '{title or '(제목 없음)'}'")
        got = (db.get("data_sources") or [{}])[0].get("id")
        if got:
            src = got
            INFO["BOOK_DS_ID"] = got
            ok(f"data_source_id: {got}")
    except Exception as e:
        bad(f"DB 접근 실패: {e}",
            "ASK> Notion 페이지 ⋯ → 연결(Connections) 에 통합앱을 추가했는지 확인")
        return
    try:
        d = N.get_data_source(src)
        props = d.get("properties") or {}
        titles = [k for k, v in props.items() if v.get("type") == "title"]
        if C.TITLE_PROP in props:
            ok(f"title 속성: '{C.TITLE_PROP}'")
        elif titles:
            bad(f"title 속성 이름이 '{titles[0]}' (설정값 '{C.TITLE_PROP}')",
                f"FIX> BOOK_TITLE_PROP={titles[0]}")
        rows = N.query_all(src)
        if rows:
            bad(f"DB에 기존 행이 {len(rows)}개 있습니다",
                "ASK> 덮어쓸지 사용자에게 확인 (빈 DB를 전제로 만든다)")
        else:
            ok("DB가 비어 있음")
    except Exception as e:
        bad(f"데이터소스 조회 실패: {e}", "FIX> BOOK_DS_ID 확인")


# ── 5·6. rclone / LLM ──────────────────────────────────────
def check_rclone():
    print("\n== 5. rclone (그림 호스팅) ==")
    try:
        out = subprocess.run([C.RCLONE_BIN, "listremotes"], capture_output=True,
                             text=True, encoding="utf-8", timeout=60)
        remotes = [r.strip() for r in out.stdout.splitlines() if r.strip()]
        if f"{C.RCLONE_REMOTE}:" in remotes:
            ok(f"remote '{C.RCLONE_REMOTE}:' 인증됨")
        else:
            bad(f"remote '{C.RCLONE_REMOTE}:' 없음 (있는 것: {remotes})",
                "ASK> rclone config 로 Google Drive remote 인증 요청")
    except FileNotFoundError:
        bad("rclone 실행파일 없음", "ASK> rclone 설치 후 RCLONE_BIN 지정")
    except Exception as e:
        bad(f"rclone 확인 실패: {e}", "FIX> rclone 설치/경로 확인")


def check_llm():
    print("\n== 6. LLM 백엔드 ==")
    import llm_runner as R
    if R.backend() == "agent":
        ok("codex CLI 없음 → Claude 서브에이전트 위임 모드")
        print("         (04·06·08 단계가 _output/prompts/ 에 프롬프트를 남깁니다)")
        return
    ok(f"codex CLI: {C.CODEX_BIN}")
    outfile = C.OUT_DIR / "_preflight_codex.txt"
    try:
        r = subprocess.run(
            [C.CODEX_BIN, "exec", "--skip-git-repo-check", "--ephemeral",
             "-s", "read-only", "-o", str(outfile)],
            input="Reply with exactly: CODEX_OK", capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180, cwd=str(C.ROOT))
        got = outfile.read_text(encoding="utf-8").strip() if outfile.exists() else ""
        if "CODEX_OK" in got:
            ok("codex 인증·비대화 실행 정상")
        else:
            bad(f"codex 응답 이상 (rc={r.returncode}, got={got[:100]!r})",
                "ASK> `codex login` 인증 요청 (또는 BOOK_LLM_BACKEND=agent)")
    except subprocess.TimeoutExpired:
        bad("codex 응답 시간 초과(180s)", "ASK> 네트워크/인증 확인")
    except Exception as e:
        bad(f"codex 스모크 테스트 실패: {e}", "ASK> `codex login` 확인")
    finally:
        outfile.unlink(missing_ok=True)


def main():
    print("=" * 64)
    print(" book-outline-notion : 사전 점검 + 구조 탐지")
    print("=" * 64)
    check_files()
    check_pkgs()
    detect_structure()
    check_notion()
    check_rclone()
    check_llm()

    if INFO:
        print("\n" + "=" * 64)
        print(" 아래 값을 고정하고 01단계로 진행하세요")
        print("=" * 64)
        print(" PowerShell:")
        for k, v in INFO.items():
            print(f'   $env:{k} = "{v}"')
        print(" bash:")
        print("   export " + " ".join(f'{k}="{v}"' for k, v in INFO.items()))

    print("\n" + "=" * 64)
    if MISSING:
        print(f"조치 필요 {len(MISSING)}건 ❌")
        for msg, fix in MISSING:
            print(f"  - {msg}\n    > {fix}")
        sys.exit(1)
    print(f"진행 가능 ✅ ({len(OK)}개 항목 통과)")
    sys.exit(0)


if __name__ == "__main__":
    main()
