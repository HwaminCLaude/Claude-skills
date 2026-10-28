"""민감정보를 모자이크로 가린 공개용 스크린샷을 만든다.

사용법: python tools/redact.py <레슨 폴더>

<레슨 폴더>/_raw/redact-spec.json 에 적힌 이미지만 <레슨 폴더>/screenshots/ 로 내보낸다.
명세에 없는 원본은 공개 폴더로 나가지 않는다(실수로 원본이 공개되는 것을 막는 기본값).

redact-spec.json 형식:
{
  "s01-runpod-pods-list.jpg": {"out": "s01-runpod-pods-list.png", "boxes": [[x0, y0, x1, y1], ...]},
  "s03-jupyterlab-first-screen.jpg": {"out": "s03-jupyterlab-first-screen.png", "boxes": []}
}
좌표는 원본 이미지 픽셀 기준이다. 가린 영역에는 빨간 테두리를 그려 '가렸다'는 사실이 보이게 한다.
결과 목록은 screenshots/_masking.json 에 남는다(check_lesson.py가 '마스킹을 거친 이미지'인지 이 파일로 확인).
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서도 한글·기호 출력

BLOCK = 9                      # 모자이크 한 칸 크기(px)
OUTLINE = (220, 60, 60)        # 가린 영역 테두리 색


def pixelate(im, box):
    x0, y0, x1, y1 = box
    region = im.crop(box)
    w, h = region.size
    small = region.resize((max(1, w // BLOCK), max(1, h // BLOCK)), Image.BILINEAR)
    im.paste(small.resize((w, h), Image.NEAREST), (x0, y0))
    ImageDraw.Draw(im).rectangle(box, outline=OUTLINE, width=2)


def main(lesson_dir):
    lesson = Path(lesson_dir)
    raw, pub = lesson / "_raw", lesson / "screenshots"
    spec = json.loads((raw / "redact-spec.json").read_text(encoding="utf-8-sig"))   # BOM이 붙어 있어도 읽는다
    pub.mkdir(exist_ok=True)
    report = {}
    for src_name, item in spec.items():
        im = Image.open(raw / src_name).convert("RGB")
        for box in item["boxes"]:
            pixelate(im, tuple(box))
        out = pub / item["out"]
        im.save(out, optimize=True)
        report[item["out"]] = {"source": src_name, "masked_boxes": len(item["boxes"]), "size": im.size}
        print(f"{src_name} -> screenshots/{item['out']} ({len(item['boxes'])} boxes)")
    (pub / "_masking.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
