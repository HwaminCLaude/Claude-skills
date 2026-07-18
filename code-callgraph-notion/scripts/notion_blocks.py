#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notion_blocks.py — 가이드북 spec(JSON) → Notion 블록 변환기 (code-guidebook 빌더 이식+확장).

확장점(code-guidebook 대비):
- 인라인 링크 `[text](url)` 지원 (연결·용어집 링크용).
- 코드/문단 2000자 초과 시 rich_text 다중 조각 자동 분할(Notion 제한).
- h1/h2(파란 배경 옵션)/flowmap/toggle(중첩 children) 지원.

spec 타입: h1, h2(+blue), h3, p, callout(emoji,color), bul(items), num(items),
           code(code,language), divider, quote, flowmap(goal,stages[{n,name,role}]),
           toggle(text, children[spec...])
공개 함수: block_from_spec(spec)->dict|list, flatten_specs(specs)->list
"""
import re

MAXLEN = 1900
# NOTE: 코드 가이드북은 snake_case 식별자(밑줄)가 많아 `_이탤릭_` 파싱은 일부러 제외한다
# (안 그러면 local_energies·pi_pos 같은 이름이 깨진다). 강조는 **굵게**·`코드`만.
_INLINE_RE = re.compile(r"(\[[^\]]+\]\([^)]+\)|\*\*.+?\*\*|`[^`]+`)")
_LINK_RE = re.compile(r"^\[([^\]]+)\]\(([^)]+)\)$")

def _split(s, n=MAXLEN):
    return [s[i:i+n] for i in range(0, len(s), n)] or [""]

def _txt_obj(content, ann=None, link=None):
    o={"type":"text","text":{"content":content}}
    if link: o["text"]["link"]={"url":link}
    o["annotations"]={"bold":False,"italic":False,"strikethrough":False,
                      "underline":False,"code":False,"color":"default"}
    if ann: o["annotations"].update(ann)
    return o

def to_rich_text(text):
    """마크다운-ish 인라인(**굵게** _이탤릭_ `코드` [링크](url)) → rich_text. 2000자 분할."""
    if not text: return []
    out=[]
    for part in _INLINE_RE.split(text):
        if not part: continue
        m=_LINK_RE.match(part)
        if m:
            for c in _split(m.group(1)): out.append(_txt_obj(c, link=m.group(2)))
            continue
        ann=None; content=part
        if part.startswith("**") and part.endswith("**"): ann={"bold":True}; content=part[2:-2]
        elif part.startswith("`") and part.endswith("`") and len(part)>2: ann={"code":True}; content=part[1:-1]
        if not content: continue
        for c in _split(content): out.append(_txt_obj(c, ann=ann))
    return out

def _code_rt(code):
    return [_txt_obj(c) for c in _split(code)]

def _heading(level, text, blue=False):
    t=f"heading_{level}"
    body={"rich_text":to_rich_text(text),"is_toggleable":False}
    if blue: body["color"]="blue_background"
    return {"object":"block","type":t,t:body}

def _flowmap(spec):
    goal=spec.get("goal",""); stages=spec.get("stages",[])
    callout={"object":"block","type":"callout","callout":{
        "rich_text":to_rich_text(f"📍 흐름 지도 — {goal}"),
        "icon":{"type":"emoji","emoji":"📍"},"color":"orange_background"}}
    lines=[]
    for s in stages:
        n=s.get("n",""); name=s.get("name",""); role=s.get("role") or s.get("data") or ""
        lines.append(f"{n}. {name}" + (f"  —  {role}" if role else ""))
    code={"object":"block","type":"code","code":{
        "rich_text":_code_rt("\n".join(lines)),"language":"plain text"}}
    return [callout, code]

def block_from_spec(spec):
    t=spec.get("type")
    if t=="h1": return _heading(1, spec.get("text",""), blue=spec.get("blue",True))
    if t=="h2": return _heading(2, spec.get("text",""), blue=spec.get("blue",False))
    if t=="h3": return _heading(3, spec.get("text",""))
    if t=="p":
        return {"object":"block","type":"paragraph","paragraph":{"rich_text":to_rich_text(spec.get("text",""))}}
    if t=="callout":
        return {"object":"block","type":"callout","callout":{
            "rich_text":to_rich_text(spec.get("text","")),
            "icon":{"type":"emoji","emoji":spec.get("emoji","💡")},
            "color":spec.get("color","default_background")}}
    if t=="quote":
        return {"object":"block","type":"quote","quote":{"rich_text":to_rich_text(spec.get("text",""))}}
    if t=="num":
        return [{"object":"block","type":"numbered_list_item",
                 "numbered_list_item":{"rich_text":to_rich_text(it)}} for it in spec.get("items",[])]
    if t=="bul":
        return [{"object":"block","type":"bulleted_list_item",
                 "bulleted_list_item":{"rich_text":to_rich_text(it)}} for it in spec.get("items",[])]
    if t=="code":
        lang=spec.get("language","python")
        if lang=="text": lang="plain text"
        return {"object":"block","type":"code","code":{
            "rich_text":_code_rt(spec.get("code","")),"language":lang}}
    if t=="mermaid":
        return {"object":"block","type":"code","code":{
            "rich_text":_code_rt(spec.get("code","")),"language":"mermaid"}}
    if t=="divider":
        return {"object":"block","type":"divider","divider":{}}
    if t=="eq":
        return {"object":"block","type":"equation","equation":{"expression":spec.get("expression","")}}
    if t=="flowmap":
        return _flowmap(spec)
    if t=="toggle":
        return {"object":"block","type":"toggle","toggle":{
            "rich_text":to_rich_text(spec.get("text","")),
            "children":flatten_specs(spec.get("children",[]))}}
    return None

def flatten_specs(specs):
    out=[]
    for s in specs:
        b=block_from_spec(s)
        if b is None: continue
        if isinstance(b,list): out.extend(b)
        else: out.append(b)
    return out
