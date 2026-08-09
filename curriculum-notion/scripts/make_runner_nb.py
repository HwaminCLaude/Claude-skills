# -*- coding: utf-8 -*-
"""make_runner_nb.py — Colab 안에서 91개 노트북을 전부 실행시키는 러너 노트북 생성.

왜 이렇게 하나
  UI 로 하나씩 열면 91개 × 3~5분이고 Colab DOM 이 가상화돼 오류 수집도 불안정하다.
  **Colab 런타임 안에서 직접 실행**하면 실제 Colab 환경(사전설치 버전·드라이브·GPU)을
  그대로 쓰면서 결과를 JSON 으로 받는다.

nbclient 대신 **인프로세스 exec** 를 쓴다
  nbclient 는 노트북마다 커널을 새로 띄우는데 Colab 에서 기동에만 ~100초가 걸려
  91개 × 2회 = 5시간이 나왔다. 셀을 같은 프로세스에서 실행하면 몇 분이면 끝난다.
  대신 노트북마다 **깨끗한 전역 네임스페이스**를 새로 만들어 상태가 안 섞이게 한다.

두 번 돌린다
  Pass A — 있는 그대로. 학습자가 '모두 실행' 했을 때 보는 것.
           기대: 오류 0 + `⏳`(빈칸 안내) 출력
  Pass B — 3장 TODO 를 7장 정답으로 바꿔서.
           기대: 오류 0 + `✅`(채점 통과) 출력

산출: `_코딩북_실습/_run_report.json`

    python make_runner_nb.py       →  notebooks/_RUNNER.ipynb
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).parent
OUT = HERE / "notebooks" / "_RUNNER.ipynb"

SETUP = r'''
from google.colab import drive
drive.mount('/content/drive')
'''

BODY = r'''
import json, re, sys, time, io, contextlib, types, traceback, copy
from pathlib import Path
import nbformat

ROOT = Path('/content/drive/MyDrive/메타코드 실습프로젝트/_코딩북_실습')
REPORT = ROOT / '_run_report.json'
assert ROOT.is_dir(), f'경로 없음: {ROOT}'

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.show = lambda *a, **k: plt.close('all')

# 드라이브는 이미 마운트돼 있다. 노트북 안의 drive.mount 가 다시 인증을 시도하지 않게 무력화.
_gc = sys.modules['google.colab']
_gc.drive.mount = lambda *a, **k: print('Mounted at /content/drive')

MAGIC = re.compile(r'^\s*[!%]')

def clean_src(src):
    """매직/셸 명령은 인프로세스에서 못 도니 걷어낸다(pip 은 Colab 에 이미 있는 것 위주)."""
    keep = []
    for ln in src.splitlines():
        if MAGIC.match(ln):
            keep.append('pass  # (magic 생략) ' + ln.strip()[:70])
        else:
            keep.append(ln)
    return '\n'.join(keep)

SOL_RE = re.compile(r'```python\s*(.*?)```', re.S)

def solution_of(nb):
    for c in reversed(nb.cells):
        if c.cell_type == 'markdown' and '정답 펼치기' in c.source:
            m = SOL_RE.search(c.source)
            if m:
                return m.group(1).strip()
    return None

def todo_index(nb):
    for i, c in enumerate(nb.cells):
        if c.cell_type == 'code' and 'TODO' in c.source and 'NotImplementedError' in c.source:
            return i
    return None

def run(nb, workdir):
    """셀을 순서대로 실행. 한 셀이 실패해도 계속 돌려 오류를 전부 모은다."""
    import os
    cwd = os.getcwd()
    os.chdir(workdir)
    G = {'__name__': '__main__'}
    bad, out_all = [], []
    t0 = time.time()
    try:
        for i, c in enumerate(nb.cells):
            if c.cell_type != 'code':
                continue
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    exec(compile(clean_src(c.source), f'<cell {i}>', 'exec'), G)
            except BaseException as e:
                bad.append({'cell': i, 'err': f'{type(e).__name__}: {e}'[:220],
                            'src': c.source[:160]})
            out_all.append(buf.getvalue())
    finally:
        os.chdir(cwd)
        plt.close('all')
    txt = '\n'.join(out_all)
    return {'fatal': None, 'cells': bad, 'sec': round(time.time() - t0, 1),
            'has_check_ok': '✅' in txt, 'has_todo_note': '⏳' in txt,
            'tail': txt[-500:]}

nbs = sorted(p for p in ROOT.rglob('*.ipynb') if not p.name.startswith('_'))
print(f'노트북 {len(nbs)}개\n')

report = []
for n, p in enumerate(nbs, 1):
    rel = str(p.relative_to(ROOT))
    entry = {'nb': rel}
    try:
        raw = nbformat.read(p, as_version=4)
    except Exception as e:
        entry['read_error'] = str(e)[:200]
        report.append(entry); continue

    entry['A'] = run(copy.deepcopy(raw), p.parent)

    sol, ti = solution_of(raw), todo_index(raw)
    if sol and ti is not None:
        nb2 = copy.deepcopy(raw)
        nb2.cells[ti].source = sol
        entry['B'] = run(nb2, p.parent)
    else:
        entry['B'] = {'fatal': '정답/TODO 셀 못 찾음', 'cells': [],
                      'has_check_ok': False, 'has_todo_note': False}

    report.append(entry)
    A, B = entry['A'], entry['B']
    flag = '' if (not A['cells'] and not B.get('cells')) else '  ← 확인필요'
    print(f"[{n}/{len(nbs)}] {rel:<42} A:{len(A['cells'])}오류 "
          f"{'⏳' if A['has_todo_note'] else '  '} | "
          f"B:{len(B.get('cells', []))}오류 {'✅' if B.get('has_check_ok') else '  '}{flag}",
          flush=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')

print('\n저장:', REPORT)
'''

SUMMARY = r'''
import json, collections
from pathlib import Path
rep = json.loads(Path('/content/drive/MyDrive/메타코드 실습프로젝트/_코딩북_실습/_run_report.json').read_text(encoding='utf-8'))
ca = collections.Counter(); cb = collections.Counter()
cleanA = cleanB = todo = okmark = 0
for e in rep:
    A, B = e.get('A', {}), e.get('B', {})
    if not A.get('cells'): cleanA += 1
    if not B.get('cells') and not B.get('fatal'): cleanB += 1
    if A.get('has_todo_note'): todo += 1
    if B.get('has_check_ok'): okmark += 1
    for c in A.get('cells', []): ca[c['err'].split(':')[0]] += 1
    for c in B.get('cells', []): cb[c['err'].split(':')[0]] += 1
print(f'노트북 {len(rep)}개')
print(f'  Pass A 오류없음 : {cleanA}/{len(rep)}   ⏳안내 출력 {todo}')
print(f'  Pass B 오류없음 : {cleanB}/{len(rep)}   ✅채점통과 {okmark}')
print('\nA 오류 유형:', dict(ca.most_common(12)))
print('B 오류 유형:', dict(cb.most_common(12)))
print('\n문제 있는 노트북:')
for e in rep:
    a = e.get('A', {}).get('cells', []); b = e.get('B', {}).get('cells', [])
    if a or b or not e.get('B', {}).get('has_check_ok'):
        print(' ', e['nb'], '| A:', [c['err'][:60] for c in a][:2],
              '| B:', [c['err'][:60] for c in b][:2],
              '| ✅' if e.get('B', {}).get('has_check_ok') else '| ✅없음')
'''


def md(t):
    return nbf.v4.new_markdown_cell(t.strip())


def code(t):
    return nbf.v4.new_code_cell(t.strip())


def main() -> int:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        md("# 코딩북 노트북 일괄 실행 · 오류 수집\n\n"
           "Colab 런타임 안에서 `_코딩북_실습/` 의 모든 노트북을 실제로 실행해 셀별 오류를 모읍니다.\n\n"
           "- **Pass A** — 있는 그대로. 기대: 오류 0 + `⏳` 안내\n"
           "- **Pass B** — 3장 TODO 를 정답으로. 기대: 오류 0 + `✅` 채점통과\n\n"
           "결과: `_코딩북_실습/_run_report.json`"),
        md("## 1. 드라이브 연결"),
        code(SETUP),
        md("## 2. 전체 실행\n\n인프로세스로 돌려서 몇 분이면 끝나요."),
        code(BODY),
        md("## 3. 요약"),
        code(SUMMARY),
    ]
    nb.metadata = {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                   "language_info": {"name": "python"}, "colab": {"provenance": []}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{OUT}  셀 {len(nb.cells)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
