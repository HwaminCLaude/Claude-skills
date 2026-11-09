"""Create the data page + master database ("Portfolio Items") from schema.json. Idempotent via state.json.
Adds the self relation (관련 항목) and the half-year formula (시기) after creation."""
from notion_lib import *

state = load_state()
if "data_page_id" not in state:
    pg = api_ok("POST", "/pages", {
        "parent": {"type": "page_id", "page_id": MAIN_PAGE},
        "properties": {"title": {"title": [{"type": "text", "text": {"content": CFG.get("data_page_title", "포트폴리오 데이터(원본)")}}]}},
        "children": [blk("paragraph", {"rich_text": rich(CFG.get("data_page_note", "메인 페이지의 갤러리·차트는 아래 데이터베이스의 연결 뷰입니다. 항목 추가·수정은 여기서 하거나 메인 페이지 뷰에서 바로 할 수 있습니다."))})],
    })
    state["data_page_id"] = pg["id"]
    save_state(state)
    log(f"data page created: {pg['id']} {pg.get('url')}")

if "db_id" not in state:
    props = {
        "이름": {"title": {}},
        "섹션": {"select": {"options": SCHEMA["sections"]}},
        "분류": {"select": {"options": SCHEMA["types"]}},
        "기간": {"date": {}},
        "상태": {"status": {}},
        "한줄 성과": {"rich_text": {}},
        "역할": {"rich_text": {}},
        "기술 스택": {"multi_select": {"options": []}},
        "기관·주최": {"rich_text": {}},
        "GitHub": {"url": {}},
        "배포 링크": {"url": {}},
        "논문/자료 링크": {"url": {}},
        "파일": {"files": {}},
        "정렬": {"number": {"format": "number"}},
    }
    for extra_name, extra_def in SCHEMA.get("extra_properties", {}).items():
        props[extra_name] = extra_def
    db = api_ok("POST", "/databases", {
        "parent": {"type": "page_id", "page_id": state["data_page_id"]},
        "title": [{"type": "text", "text": {"content": CFG.get("db_title", "Portfolio Items")}}],
        "is_inline": True,
        "initial_data_source": {"properties": props},
    })
    state["db_id"] = db["id"]
    state["ds_id"] = db["data_sources"][0]["id"]
    save_state(state)
    log(f"database created: db={db['id']} ds={state['ds_id']}")

ds_id = state["ds_id"]
ds = api_ok("GET", f"/data_sources/{ds_id}")
if "관련 항목" not in ds["properties"]:
    r = api("PATCH", f"/data_sources/{ds_id}", {"properties": {"관련 항목": {"relation": {"data_source_id": ds_id, "type": "single_property", "single_property": {}}}}})
    if "error" in r:
        api_ok("PATCH", f"/data_sources/{ds_id}", {"properties": {"관련 항목": {"relation": {"data_source_id": ds_id, "type": "dual_property", "dual_property": {}}}}})
    log("relation property 관련 항목 added")
if "시기" not in ds["properties"]:
    expr = 'if(empty(prop("기간")), "", formatDate(prop("기간"), "YYYY") + if(toNumber(formatDate(prop("기간"), "M")) <= 6, " 상반기", " 하반기"))'
    r = api("PATCH", f"/data_sources/{ds_id}", {"properties": {"시기": {"formula": {"expression": expr}}}})
    log("formula property 시기 (half-year) added" if "error" not in r else f"formula add failed: {r['body'][:200]}")
# status option names: Notion creates English defaults (Not started / In progress / Done) and
# renaming through the API does not stick -> scripts map 완료/진행 중/예정 onto whatever exists.
ids, ds = prop_ids(state)
state["status_options"] = [o["name"] for o in ds["properties"]["상태"]["status"]["options"]]
save_state(state)
log(f"schema ready: {sorted(ids)}; status options: {state['status_options']}")
