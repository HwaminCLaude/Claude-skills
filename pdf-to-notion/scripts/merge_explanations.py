"""explanations_*.json 파일들을 explanations.json 으로 머지."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import EXPLANATIONS, OUT_DIR


def main():
    merged = {}
    files = sorted(OUT_DIR.glob("explanations_*.json"))
    print(f"[INFO] {len(files)}개 파일 발견")

    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  [ERR] {f.name}: {e}")
            continue
        for slug, body in data.items():
            if slug in merged:
                # 같은 deck을 페이지 범위로 나눠 쓴 부분 파일 → deep merge
                merged[slug].setdefault("page_explanations", {}).update(
                    body.get("page_explanations", {}))
                merged[slug].setdefault("section_titles", {}).update(
                    body.get("section_titles", {}))
                print(f"  ~ {slug}: 부분 병합 (+{len(body.get('page_explanations', {}))}페이지)")
                continue
            merged[slug] = body
            n_pages = len(body.get("page_explanations", {}))
            n_blocks = sum(len(v) for v in body.get("page_explanations", {}).values())
            n_titles = len(body.get("section_titles", {}))
            print(f"  + {slug}: {n_pages}페이지, 블록 {n_blocks}개, 섹션 제목 {n_titles}개")

    EXPLANATIONS.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[DONE] {EXPLANATIONS}")
    print(f"  강의자료 {len(merged)}개")
    total_pages = sum(len(v.get("page_explanations", {})) for v in merged.values())
    total_blocks = sum(
        sum(len(p) for p in v.get("page_explanations", {}).values())
        for v in merged.values()
    )
    print(f"  총 페이지 {total_pages}개, 총 블록 {total_blocks}개")


if __name__ == "__main__":
    main()
