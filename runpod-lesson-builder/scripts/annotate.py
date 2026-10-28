"""공개용 스크린샷 위에 '여기를 클릭' 표시(번호 원 + 강조 상자)를 그린 이미지를 만든다.

사용법: python tools/annotate.py <레슨 폴더>

<레슨 폴더>/_raw/annotate-spec.json 형식:
{
  "s02-click-jupyter-lab.png": {
    "src": "s02-pod-connect-panel.png",
    "marks": [{"box": [x0, y0, x1, y1], "n": 1}]
  }
}
번호 원은 기본으로 상자의 왼쪽 위 모서리에 그린다. 그 자리가 중요한 표시(예: 상태 점)를 가리면
mark에 "anchor": "right"를 주어 상자 오른쪽 바깥(세로 가운데)에 그린다(선택, 기존 명세는 그대로 동작).
src는 이미 마스킹된 screenshots/ 안의 이미지여야 한다(원본 위에 그리지 않는다). redact.py를 먼저 돌린다.
표시는 실제 화면이 아니라 설명용이므로 파일 이름(*-click-*)과 manifest에 annotated로 남긴다.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서도 한글·기호 출력

COLOR = (255, 106, 0)          # 주황: 클릭 위치 표시


def font(size):
    for name in ("malgunbd.ttf", "malgun.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)    # Pillow 10.1+: 맑은 고딕이 없는 PC에서도 같은 크기로
    except TypeError:
        return ImageFont.load_default()


def main(lesson_dir):
    pub = Path(lesson_dir) / "screenshots"
    spec = json.loads((Path(lesson_dir) / "_raw" / "annotate-spec.json").read_text(encoding="utf-8-sig"))
    f = font(18)
    for out_name, item in spec.items():
        im = Image.open(pub / item["src"]).convert("RGB")
        d = ImageDraw.Draw(im)
        for m in item["marks"]:
            x0, y0, x1, y1 = m["box"]
            d.rounded_rectangle((x0 - 4, y0 - 4, x1 + 4, y1 + 4), radius=6, outline=COLOR, width=4)
            r = 14
            if m.get("anchor") == "right":
                cx, cy = x1 + 4 + r + 4, (y0 + y1) // 2
            else:
                cx, cy = x0 - 4, y0 - 4
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=COLOR)
            d.text((cx, cy), str(m["n"]), fill="white", font=f, anchor="mm")
        im.save(pub / out_name, optimize=True)
        print(f"{item['src']} -> {out_name} ({len(item['marks'])} marks)")


if __name__ == "__main__":
    main(sys.argv[1])
