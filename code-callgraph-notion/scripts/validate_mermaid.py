#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_mermaid.py — _diagrams.md 안의 모든 ```mermaid 블록을 mermaid-cli(mmdc)로 렌더해 문법 검증.

- Notion에 올리기 전에 반드시 실행해 렌더 실패(0에러)를 확인한다.
- mmdc 필요: `npm i -g @mermaid-js/mermaid-cli` (설치 후 `mmdc` 명령).
- puppeteer 샌드박스 회피 설정을 자동 생성해 사용.

사용: python validate_mermaid.py <diagrams_md> [<diagrams_md> ...]
반환코드: 실패 블록이 있으면 1.
"""
import re, os, sys, json, subprocess, tempfile, shutil

def run_mmdc(exe, mm, svg, pptr):
    # Windows에서 mmdc는 .cmd 셋이라 셸 경유가 필요.
    if os.name=="nt":
        return subprocess.run(f'"{exe}" -i "{mm}" -o "{svg}" -p "{pptr}"',
                              capture_output=True, text=True, shell=True)
    return subprocess.run([exe,"-i",mm,"-o",svg,"-p",pptr], capture_output=True, text=True)

def main():
    exe=shutil.which("mmdc")
    if not exe:
        print("!! mmdc(mermaid-cli) 미설치: npm i -g @mermaid-js/mermaid-cli"); sys.exit(2)
    tmp=tempfile.mkdtemp(prefix="mmv_")
    pptr=os.path.join(tmp,"pptr.json")
    open(pptr,"w").write(json.dumps({"args":["--no-sandbox","--disable-setuid-sandbox"]}))
    total=fail=0
    for md in sys.argv[1:]:
        txt=open(md,encoding="utf-8").read()
        for i,b in enumerate(re.findall(r"```mermaid\n(.*?)```", txt, re.S), 1):
            total+=1
            mm=os.path.join(tmp,f"b{total:03d}.mmd"); svg=mm[:-4]+".svg"
            open(mm,"w",encoding="utf-8").write(b)
            r=run_mmdc(exe, mm, svg, pptr)
            if not (os.path.exists(svg) and os.path.getsize(svg)>0):
                fail+=1; print(f"  ✗ {os.path.basename(md)} 블록{i} FAIL")
                print("   ", (r.stderr or r.stdout).strip().splitlines()[-1:] )
    print(f"검증: 총 {total} 블록 · 실패 {fail}")
    shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(1 if fail else 0)

if __name__=="__main__":
    main()
