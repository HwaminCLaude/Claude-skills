# config.json 스키마

작업 폴더(`--work` 로 지정, 기본은 현재 폴더)에 `config.json` 을 둔다.
산출물은 전부 `<작업폴더>/_out/` 에 쌓인다.

```jsonc
{
  // ── 입력 ─────────────────────────────────────────────
  "source_dir": "C:\\Users\\...\\강의영상",   // <source_dir>/<그룹>/<basename>.mp4
  "groups": ["0_사전학습", "1주차", "2주차"],   // 생략하면 하위 폴더 전부 (이름순)
  "transcript_priority": ["merged.md", "vtt", "srt"],
  "meta_file": "config/lectures.json",        // (선택) 제목·길이 등 외부 메타데이터
  "probe_duration": true,                     // 메타에 길이가 없으면 ffprobe 로 실측
  "ffprobe_bin": "ffprobe",

  // ── 구글드라이브 ──────────────────────────────────────
  "rclone_bin": "C:\\Users\\정화민\\rclone\\rclone.exe",
  "drive_remote": "gdrive:메타코드/강의영상",
  "bandwidth_limit": "1600k",   // Notion 작업과 병행할 때 필수. 끝나면 --bw off

  // ── Notion ──────────────────────────────────────────
  "notion": {
    "token": null,              // null 이면 NOTION_TOKEN → ~/.claude.json 순으로 찾음
    "title_prop": "이름",        // 대상 DB 의 title 속성 이름 (DB마다 다름! 반드시 확인)
    "mode": "child_db",         // "flat" | "child_db"

    // mode=flat 일 때
    "database_id": "…",

    // mode=child_db 일 때: 그룹 → 그 그룹 페이지가 들어갈 child DB id
    "group_db_map": {
      "0_사전학습": "3ac734f9-1be4-80ae-8205-c066e3045fec",
      "1주차":     "3ac734f9-1be4-807e-b3c2-d4d7a132765d"
    },

    // (선택) 절대 건드리면 안 되는 원본 DB — 06_verify.py 가 무변경을 증명한다
    "protected_dbs": { "원본 1주차": "370734f9-…" }
  },

  // ── 페이지 제목 형식 ──────────────────────────────────
  "page_title_format": "{seq}. {subtitle} — {title}"
}
```

## meta_file 형식 두 가지

**(A) 강의 인덱스형** — `{"weeks": {"7주차": [{basename, Mtitle, Ctitle, duration, vimeo_url}, ...]}}`
**(B) 평면 배열** — `[{group, basename, title, subtitle, duration, url}, ...]`

없어도 된다. 없으면 파일명이 제목이 되고 길이는 ffprobe 로 잰다.

---

# 대상 Notion DB 구조 파악하기

작업 전에 **반드시** 대상 DB 를 열어 구조와 title 속성 이름을 확인한다. 추측하면 실패한다.

## 1. DB 가 통합앱에 공유돼 있는지

공유가 안 돼 있으면 `404 object_not_found` 가 난다. 사용자에게 이렇게 안내한다:

> Notion 에서 해당 DB → 우측 상단 `⋯` → **연결(Connections)** → 통합앱 이름 추가

## 2. title 속성 이름 확인

DB 마다 다르다(`이름`, `제목`, `주차별`, `Name` …). 틀리면 페이지 생성이 400 으로 실패한다.

```python
import vt_common as C
C.init("<작업폴더>")
db = C.api("https://api.notion.com/v1/databases/<DB_ID>")
print([ (k, v["type"]) for k, v in db["properties"].items() ])
```

## 3. child DB 구조인 경우 id 수집

"주차 행 → 그 행 안에 인라인 DB → 거기에 실제 페이지" 구조가 흔하다.
이때 페이지를 만들 대상은 **부모 DB 가 아니라 각 행 안의 child DB** 다.

```python
for row in C.query_db("<부모 DB id>"):
    title = C.title_of(row)
    for block in C.get_children(row["id"]):
        if block["type"] == "child_database":
            print(title, "->", block["id"], block["child_database"]["title"])
```

출력을 그대로 `notion.group_db_map` 에 넣는다.

## 4. 그룹 이름이 어긋날 때

로컬 폴더명과 Notion 주차 행 이름이 한 칸씩 밀리는 경우가 실제로 있었다
(로컬 `0_사전학습` → Notion `1주차`). `group_db_map` 의 키를 **로컬 폴더명**으로 두고
값을 해당 Notion child DB id 로 맞추면 그대로 해결된다. 사용자에게 대응표를 확인받을 것.
