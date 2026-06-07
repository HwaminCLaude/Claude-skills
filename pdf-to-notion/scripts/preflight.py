"""사전 점검(Stage 0) — pdf-to-notion / code-guidebook-notion 작업 전 환경·입력 자동 검증.

이 스크립트는 '로컬에서 확인 가능한 것'만 기계적으로 점검한다.
(Notion DB 실제 접근/통합 연결 여부는 MCP가 필요하므로 호출하는 Claude가 별도로 확인한다.)

사용법:
  PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python preflight.py <pdf|gb> "<작업폴더>" [--db "<DB URL 또는 ID>"]

출력:
  항목마다 [OK] / [WARN] / [MISSING] 한 줄.
  마지막에 사용자에게 받아내야 할 항목을 "ASK> ..." 로, 자동조치 가능한 항목을 "FIX> ..." 로 나열.
종료코드:
  0 = 진행 가능(MISSING 없음), 1 = MISSING 존재(사용자 조치 필요).
"""
from __future__ import annotations
import os, sys, shutil, subprocess, re
from pathlib import Path

RCLONE_BIN = os.environ.get("RCLONE_BIN", r"C:\Users\정화민\rclone\rclone.exe")
RCLONE_REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")
SOFFICE = r"C:/Users/정화민/LO_portable/program/soffice.exe"
SKIP = {"_split_images", "_output", "_scripts", "_guidebook", ".ipynb_checkpoints"}

asks: list[str] = []
fixes: list[str] = []
missing = 0

def ok(m):   print(f"[OK]   {m}")
def warn(m): print(f"[WARN] {m}")
def miss(m):
    global missing; missing += 1; print(f"[MISSING] {m}")

def under_skip(p: Path) -> bool:
    return any(part in SKIP for part in p.parts)

def main():
    global missing
    if len(sys.argv) < 3 or sys.argv[1] not in ("pdf", "gb"):
        print("사용법: python preflight.py <pdf|gb> \"<작업폴더>\" [--db \"<DB URL/ID>\"]"); sys.exit(2)
    mode = sys.argv[1]
    root = Path(sys.argv[2])
    db = None
    if "--db" in sys.argv:
        i = sys.argv.index("--db")
        if i + 1 < len(sys.argv): db = sys.argv[i + 1]

    print(f"=== 사전 점검: mode={mode}, 폴더={root} ===")

    # 1) 작업 폴더 존재
    if not root.exists() or not root.is_dir():
        miss(f"작업 폴더가 없음: {root}")
        asks.append("정확한 작업 폴더 경로를 알려주세요(존재하는 폴더여야 함).")
        _summary(); sys.exit(1)
    ok(f"작업 폴더 존재: {root}")

    # 2) 변환 대상 파일 존재
    pdfs   = [p for p in root.rglob("*.pdf")   if not under_skip(p)]
    pptxs  = [p for p in root.rglob("*.pptx")  if not under_skip(p)]
    ipynbs = [p for p in root.rglob("*.ipynb") if not under_skip(p)]
    links  = [p for p in root.rglob("*.txt")   if not under_skip(p)]

    if mode == "pdf":
        if pdfs or pptxs:
            ok(f"PDF {len(pdfs)}개 + PPTX {len(pptxs)}개 발견")
        else:
            miss("폴더 안에 PDF/PPTX가 하나도 없음")
            asks.append("이 폴더에 변환할 PDF/PPTX가 맞는지, 자료가 다른 곳에 있는지 확인 필요.")
    else:  # gb
        if ipynbs:
            ok(f"노트북(.ipynb) {len(ipynbs)}개 발견")
        else:
            miss("폴더 안에 .ipynb 노트북이 하나도 없음")
            asks.append("이 폴더에 변환할 .ipynb가 맞는지 확인 필요.")

    # 3) PPTX가 있으면 LibreOffice 필요 (pdf 모드)
    if mode == "pdf" and pptxs:
        if Path(SOFFICE).exists():
            ok(f"LibreOffice 존재(PPTX→PDF 변환 가능): {SOFFICE}")
        else:
            warn("PPTX가 있는데 LibreOffice(soffice.exe)가 없음 → PDF 변환 필요")
            fixes.append("LibreOffice MSI를 관리자 권한 없이 추출: "
                         'msiexec /a "LO.msi" /qn TARGETDIR="C:\\Users\\정화민\\LO_portable" '
                         "→ program/soffice.exe 사용")

    # 4) 외부 링크 txt 감지 (구글드라이브 / 캐글)
    for lp in links:
        try: txt = lp.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception: continue
        if "drive.google.com" in txt:
            m = re.search(r"/folders/([A-Za-z0-9_-]+)", txt)
            fid = m.group(1) if m else "(폴더ID 추출 실패)"
            warn(f"외부 구글드라이브 링크 발견: {lp.name} → 폴더ID {fid}")
            fixes.append(f"rclone로 가져오기: rclone copy gdrive: <대상> "
                         f"--drive-root-folder-id={fid} --include *.ipynb --include *.pptx --include *.pdf")
        elif "kaggle.com" in txt:
            warn(f"캐글 링크 발견: {lp.name} → reCAPTCHA로 비로그인 다운로드 불가")
            asks.append(f"{lp.name}의 캐글 자료(.ipynb)를 직접 로그인해 받아 폴더에 넣어주세요.")
        elif txt.startswith("http"):
            warn(f"외부 링크 txt: {lp.name} → 내용 확인 필요: {txt[:80]}")
            asks.append(f"{lp.name}의 외부 링크 자료를 어떻게 가져올지 알려주세요.")

    # 5) rclone 바이너리 + remote
    if Path(RCLONE_BIN).exists():
        ok(f"rclone 존재: {RCLONE_BIN}")
        try:
            out = subprocess.run([RCLONE_BIN, "listremotes"], capture_output=True, text=True, timeout=20)
            remotes = out.stdout.replace("\r", "")
            if f"{RCLONE_REMOTE}:" in remotes:
                ok(f"rclone remote '{RCLONE_REMOTE}:' 설정됨")
            else:
                miss(f"rclone remote '{RCLONE_REMOTE}:' 미설정 (현재: {remotes.split() or '없음'})")
                asks.append(f"rclone에서 '{RCLONE_REMOTE}' remote를 직접 인증/설정해주세요 (rclone config).")
        except Exception as e:
            warn(f"rclone listremotes 실패: {e}")
    else:
        miss(f"rclone 바이너리 없음: {RCLONE_BIN}")
        asks.append("rclone 설치 경로를 알려주거나 설치해주세요(RCLONE_BIN).")

    # 6) Python 패키지 (pdf 모드)
    if mode == "pdf":
        for pkg, imp in (("PyMuPDF", "fitz"), ("pdfplumber", "pdfplumber")):
            try:
                __import__(imp); ok(f"python 패키지 {pkg} 사용 가능")
            except Exception:
                miss(f"python 패키지 {pkg} 없음")
                fixes.append(f"pip install {pkg}")

    # 7) Notion DB
    if db:
        ok(f"대상 Notion DB 입력됨: {db}")
        print("NOTE> Claude는 API-retrieve-a-database로 이 DB가 실제 열리는지, "
              "title property 이름이 '이름'인지 확인할 것.")
    else:
        miss("대상 Notion DB(URL 또는 ID) 미입력")
        asks.append("업로드할 Notion 데이터베이스 URL(또는 ID)을 알려주세요.")

    # 8) UTF-8 환경
    if os.environ.get("PYTHONUTF8") == "1":
        ok("PYTHONUTF8=1 (이모지/한글 출력 안전)")
    else:
        warn("PYTHONUTF8 미설정 → 파이썬 실행 시 PYTHONUTF8=1 PYTHONIOENCODING=utf-8 붙일 것")

    _summary()
    sys.exit(1 if missing else 0)

def _summary():
    print("\n=== 요약 ===")
    if asks:
        print("ASK> 사용자에게 받아내야 할 것 (AskUserQuestion 등으로 질의):")
        for a in asks: print("   -", a)
    if fixes:
        print("FIX> 자동/반자동 조치 가능:")
        for f in fixes: print("   -", f)
    if not asks and not fixes:
        print("추가 조치 없음.")
    print(f"\n판정: {'진행 불가(MISSING 있음)' if missing else '진행 가능 ✅'}")

if __name__ == "__main__":
    main()
