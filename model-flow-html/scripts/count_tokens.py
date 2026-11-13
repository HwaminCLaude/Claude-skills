#!/usr/bin/env python3
"""count_tokens.py: 실제 토크나이저와 채팅 템플릿으로 EXAMPLE.tokens 숫자를 잰다.

usage: python count_tokens.py --model <토크나이저 파일이 있는 폴더> --messages <messages.json>
                              [--template-kwargs '{"date_string":"26 Jul 2024"}'] [--plain] [--json]

  total    = apply_chat_template(전체 메시지)
  prompt   = apply_chat_template(마지막 메시지를 뺀 것, add_generation_prompt=True)
  target   = total - prompt                  손실을 매기는 답 쪽 토큰 (답 내용 + 끝 표시)
  내용     = tokenizer(content, add_special_tokens=False) 를 역할별로 더한 것
  template = prompt - system - user          여러 턴이면 앞선 assistant 본문이 template 에 함께 들어간다 (참고 줄로 알린다)
  --plain  = 채팅 틀이 없는 기본 모델: system 0, prompt = user 쪽 본문(+BOS), target = 답 본문 + eos, template = prompt - user

messages.json 은 [{"role": ..., "content": ...}, ...] 또는 {"messages": [...]} 이다. 마지막 메시지가 답(target)이다.
--template-kwargs 는 채팅 템플릿에 그대로 넘긴다 (Llama-3 템플릿이 넣는 오늘 날짜를 고정할 때 쓴다). JSON 파일 경로를 줘도 된다.
  틀이 쓰지 않는 인자면 '필요 없는 인자'라고 알린다.
messages 에 system 이 없는데 틀이 기본 system 글을 넣으면(예: Qwen2.5) 그 토큰 수를 알린다 (template 에 들어간다).
transformers 가 없거나 채팅 템플릿이 없으면 내용 토큰만 재고, 템플릿 토큰은 잴 수 없었다고 알린 뒤 종료 코드 3 으로 끝낸다.
"""
import argparse
import json
import os
import sys

# 깨진 TensorFlow 나 Flax 가 깔려 있어도 토크나이저만 불러오게 한다
os.environ.setdefault('USE_TF', '0')
os.environ.setdefault('USE_FLAX', '0')
os.environ.setdefault('TRANSFORMERS_NO_ADVISORY_WARNINGS', '1')
if not os.environ.get('PYTHONIOENCODING'):
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding='utf-8', errors='replace')   # 한국어 Windows 의 cp949 기본값 대신 UTF-8 로 쓴다
        except (AttributeError, ValueError):
            pass

def die(msg, code=2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def model_name(path):
    """허브 캐시 경로(models--org--name)면 name, 아니면 폴더 이름."""
    parts = os.path.abspath(path).replace('\\', '/').rstrip('/').split('/')
    for p in parts:
        if p.startswith('models--'):
            seg = p.split('--')
            return '--'.join(seg[2:]) if len(seg) > 2 else seg[1]
    return parts[-1]


TOK_FILES = ('tokenizer.json', 'tokenizer_config.json', 'tokenizer.model', 'vocab.json')


def resolve_model_dir(path):
    """허브 캐시의 models--org--name 폴더를 받으면 refs/main → snapshots/<rev> 로 풀어 토크나이저가 있는 폴더를 돌려준다."""
    has_tok = lambda d: any(os.path.isfile(os.path.join(d, f)) for f in TOK_FILES)
    if not os.path.isdir(path) or has_tok(path):
        return path
    snaps = os.path.join(path, 'snapshots')
    ref = os.path.join(path, 'refs', 'main')
    if os.path.isfile(ref):
        with open(ref, encoding='utf-8') as f:
            d = os.path.join(snaps, f.read().strip())
        if os.path.isdir(d) and has_tok(d):
            return d
    if os.path.isdir(snaps):
        cands = [os.path.join(snaps, n) for n in os.listdir(snaps)]
        cands = [d for d in cands if os.path.isdir(d) and has_tok(d)]
        if cands:
            return max(cands, key=os.path.getmtime)
    return path


def js(s):
    return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n') + "'"


def load_messages(path):
    try:
        with open(path, encoding='utf-8-sig') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        die(f'메시지 파일을 읽지 못했습니다: {e}')
    msgs = data.get('messages') if isinstance(data, dict) else data
    if not isinstance(msgs, list) or len(msgs) < 2:
        die('messages 는 메시지가 두 개 이상인 목록이어야 합니다 (마지막이 답)')
    for i, m in enumerate(msgs):
        if not isinstance(m, dict) or not isinstance(m.get('role'), str) or not isinstance(m.get('content'), str):
            die(f'{i}번째 메시지에 role, content 문자열이 없습니다')
    return msgs


def ids_of(x):
    """apply_chat_template 결과(목록, 묶음, BatchEncoding)를 토큰 id 목록 하나로."""
    if hasattr(x, 'keys'):
        x = x['input_ids']
    if hasattr(x, 'tolist'):
        x = x.tolist()
    if x and isinstance(x[0], list):
        x = x[0]
    return list(x)


def main():
    ap = argparse.ArgumentParser(description='채팅 템플릿 토큰 수를 잰다 (EXAMPLE.tokens)')
    ap.add_argument('--model', required=True,
                    help='tokenizer.json / tokenizer_config.json 이 있는 폴더, 또는 허브 캐시의 models--<org>--<name> 폴더(snapshots/<rev> 로 푼다)')
    ap.add_argument('--messages', required=True, help='메시지 JSON 파일')
    ap.add_argument('--template-kwargs', default='{}',
                    help='채팅 템플릿에 넘길 JSON 또는 그 JSON 파일 경로 (예: {"date_string":"26 Jul 2024"})')
    ap.add_argument('--plain', action='store_true',
                    help='채팅 틀이 없는 기본 모델(GPT-2 등): system 0, prompt = user 본문(+BOS), target = 답 본문 + eos 로 잰다')
    ap.add_argument('--json', action='store_true', help='기계가 읽을 JSON 으로 출력')
    a = ap.parse_args()

    raw = a.template_kwargs
    if os.path.isfile(raw):   # 큰따옴표를 지우는 셸(Windows PowerShell 5.1 등)에서는 JSON 을 파일로 넘긴다
        with open(raw, encoding='utf-8-sig') as f:
            raw = f.read()
    try:
        kw = json.loads(raw)
    except ValueError as e:
        die(f'--template-kwargs 의 JSON 을 읽지 못했습니다: {e}\n받은 글자: {raw}')
    if not isinstance(kw, dict):
        die('--template-kwargs 는 JSON 객체여야 합니다')
    msgs = load_messages(a.messages)
    if msgs[-1]['role'] != 'assistant':
        print(f"참고: 마지막 메시지의 role 이 '{msgs[-1]['role']}' 입니다. 보통 답(assistant)이 마지막에 옵니다", file=sys.stderr)
    name = model_name(a.model)
    resolved = resolve_model_dir(a.model)
    if resolved != a.model:
        print(f'참고: 허브 캐시 폴더라 {os.path.relpath(resolved, a.model)} 의 토크나이저를 씁니다', file=sys.stderr)
        a.model = resolved
    local = os.path.isdir(a.model)

    why = None          # 템플릿 토큰을 잴 수 없었던 까닭
    lib = None
    tok = None
    try:
        import transformers
        from transformers import AutoTokenizer
        transformers.logging.set_verbosity_error()
        lib = 'transformers ' + transformers.__version__
        tok = AutoTokenizer.from_pretrained(a.model, local_files_only=local)
    except ImportError:
        why = 'transformers 가 없습니다 (pip install transformers)'
    except Exception as e:   # 깨진 설치나 읽을 수 없는 폴더
        why = f'transformers 로 토크나이저를 열지 못했습니다: {type(e).__name__}: {e}'

    if tok is not None:
        count = lambda s: len(tok(s, add_special_tokens=False)['input_ids'])
        count_sp = lambda s: len(tok(s)['input_ids'])          # 토크나이저가 붙이는 BOS 등 포함
        eos_known = tok.eos_token_id is not None
    else:
        try:
            from tokenizers import Tokenizer
        except ImportError:
            die(why + '\ntokenizers 도 없어 아무것도 잴 수 없습니다 (pip install transformers)')
        tj = os.path.join(a.model, 'tokenizer.json')
        if not os.path.exists(tj):
            die(why + f'\ntokenizers 로 대신 재려 했지만 {tj} 가 없습니다')
        raw = Tokenizer.from_file(tj)
        lib = 'tokenizers (transformers 없이)'
        count = lambda s: len(raw.encode(s, add_special_tokens=False).ids)
        count_sp = lambda s: len(raw.encode(s, add_special_tokens=True).ids)
        eos_known = False
        for fn in ('tokenizer_config.json', 'special_tokens_map.json'):   # eos 토큰 이름은 이 두 파일에서 찾는다
            try:
                with open(os.path.join(a.model, fn), encoding='utf-8-sig') as f:
                    eos = json.load(f).get('eos_token')
                eos = eos.get('content') if isinstance(eos, dict) else eos
                if isinstance(eos, str) and raw.token_to_id(eos) is not None:
                    eos_known = True
                    break
            except (OSError, ValueError, AttributeError):
                pass

    content = [count(m['content']) for m in msgs]
    side = list(zip(msgs[:-1], content[:-1]))                # prompt 쪽 메시지
    sys_n = sum(n for m, n in side if m['role'] == 'system')
    user_only = sum(n for m, n in side if m['role'] == 'user')
    prior_assistant = sum(n for m, n in side if m['role'] == 'assistant')   # 여러 턴이면 앞선 답
    other = sum(content[:-1]) - sys_n - user_only            # 앞선 assistant 턴, tool 등
    answer = content[-1]

    kw_txt = ', '.join(f'{k}={v!r}' for k, v in kw.items())
    notes = []
    total = prompt = None
    prefix_ok = None
    if a.plain:
        # 채팅 틀이 없는 기본 모델: system 은 쓰지 않고, prompt = user 쪽 본문(+BOS), target = 답 본문 + eos
        text = '\n'.join(m['content'] for m in msgs[:-1] if m['role'] != 'system')
        prompt = count_sp(text)
        eos_n = 1 if eos_known else 0
        total = prompt + answer + eos_n
        prefix_ok = True
        tokens = {'system': 0, 'user': user_only, 'template': prompt - user_only, 'prompt': prompt, 'target': answer + eos_n, 'total': total}
        if other:
            notes.append(f'template {tokens["template"]} 에는 앞선 assistant 등 본문 {other} 토큰과 줄바꿈이 함께 들어 있습니다')
        if sys_n:
            notes.append(f'평문(--plain)이라 system 메시지 {sys_n} 토큰은 넣지 않았습니다 (system 0)')
        if kw:
            notes.append('평문(--plain)에서는 --template-kwargs 를 쓰지 않습니다')
        if not eos_known:
            notes.append('eos 토큰을 몰라 target 에 끝 표시를 더하지 않았습니다')
    else:
        if tok is not None and why is None:
            try:
                total_ids = ids_of(tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=False, **kw))
                prompt_ids = ids_of(tok.apply_chat_template(msgs[:-1], tokenize=True, add_generation_prompt=True, **kw))
                total, prompt = len(total_ids), len(prompt_ids)
                prefix_ok = total_ids[:prompt] == prompt_ids
            except Exception as e:   # 채팅 템플릿이 없는 기본(base) 모델 등
                why = f'채팅 템플릿을 적용하지 못했습니다: {type(e).__name__}: {e}'
        if total is not None:
            def plen(ms, **k):
                return len(ids_of(tok.apply_chat_template(ms, tokenize=True, add_generation_prompt=True, **k)))
            # system 이 없으면 기본 system 글을 넣는 틀이 있다 (예: Qwen2.5). 빈 system 을 준 것과 비교해 그만큼을 알린다
            if not any(m['role'] == 'system' for m in msgs):
                try:
                    d = prompt - plen([{'role': 'system', 'content': ''}] + msgs[:-1], **kw)
                    if d > 0:
                        notes.append(f'messages 에 system 이 없어서 채팅 틀이 기본 system 글(약 {d} 토큰)을 넣었습니다. 그 토큰은 template 에 들어가고 페이지의 대화 상자에는 보이지 않습니다. 예시에 system 을 직접 넣거나 단계 글에 밝히세요')
                except Exception:
                    pass
            # 틀이 쓰지 않는 인자(예: Llama 3 전용 date_string)를 넘겼는지
            if kw:
                try:
                    if plen(msgs[:-1]) == prompt and ids_of(tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=False)) == total_ids:
                        notes.append(f'--template-kwargs({kw_txt})를 빼도 결과가 같습니다. 이 채팅 틀에는 필요 없는 인자입니다')
                except Exception:
                    pass
        ok = total is not None
        tokens = {'system': sys_n, 'user': user_only, 'template': (prompt - sys_n - user_only) if ok else None,
                  'prompt': prompt, 'target': (total - prompt) if ok else None, 'total': total}
        if ok and not prefix_ok:
            notes.append('prompt 토큰이 total 의 앞부분과 다릅니다. 템플릿이 마지막 턴에 따라 앞을 바꾸므로 target 이 실제 손실 마스크와 다를 수 있습니다')
        if other and ok:
            notes.append(f'template {tokens["template"]} 에는 앞선 assistant 등 본문 {other} 토큰이 함께 들어 있습니다 (틀이 넣은 토큰만은 {tokens["template"] - other})')
        elif other:
            notes.append(f'prompt 쪽에 앞선 assistant 등 본문 {other} 토큰이 있습니다. 템플릿을 잴 수 있으면 template 에 함께 들어갑니다')
        if not ok:
            notes.append(why + ' → 템플릿·prompt·target·total 은 잴 수 없었고, 내용 토큰만 쟀습니다'
                         + ('. 채팅 틀이 없는 기본 모델이면 --plain 으로 잽니다' if '채팅 템플릿' in why else ''))
    measured = total is not None
    extra = (tokens['target'] - answer) if measured else None

    if a.json:
        print(json.dumps({'model': name, 'library': lib, 'mode': 'plain' if a.plain else 'chat_template', 'template_kwargs': kw,
                          'complete': measured, 'tokens': tokens,
                          'content': {'system': sys_n, 'user': user_only, 'assistant_in_prompt': prior_assistant, 'other_in_prompt': other, 'answer': answer},
                          'target_extra': extra, 'prefix_ok': prefix_ok, 'notes': notes}, ensure_ascii=False, indent=2))
        sys.exit(0 if measured else 3)

    print(f'{name}  ({lib})' + ('  평문(채팅 틀 없음)' if a.plain else (f'  템플릿 인자: {kw_txt}' if kw_txt else '')))
    for m, n in zip(msgs, content):
        print(f"  {m['role']:9s} 내용 {n:5d} 토큰  {m['content'][:40]}{'…' if len(m['content']) > 40 else ''}")
    if measured:
        print(f"  prompt {prompt} = system {tokens['system']} + user {tokens['user']} + template {tokens['template']}")
        print(f"  target {tokens['target']} = total {total} - prompt {prompt}  (답 내용 {answer} + 끝 표시 {extra})")
    for n in notes:
        print('참고: ' + n)
    v = lambda x: 'null' if x is None else str(x)
    print()
    print('붙여 넣을 블록 (템플릿의 EXAMPLE 자리):')
    print('const EXAMPLE = {   // 모델에 넣어 볼 입력 하나. 토큰 수는 실제 토크나이저'
          + ('로 잰 값 (채팅 틀 없음)' if a.plain else '와 채팅 템플릿으로 잰 값'))
    print('  messages: [')
    for m in msgs:
        if a.plain and m['role'] == 'system':
            continue   # 평문에서는 system 을 넣지 않았으므로 블록에서도 뺀다 (tokens.system 0 과 맞춘다)
        print(f"    {{ role: {js(m['role'])}, content: {js(m['content'])} }},")
    print('  ],')
    if a.plain:
        how = f'{lib} 평문(채팅 틀 없음, system 은 넣지 않음)'
    else:
        how = (f'{lib} apply_chat_template' if measured else f'{lib} (템플릿 토큰은 재지 못함)') + (f', {kw_txt}' if kw_txt else '')
    print(f'  // {how}, {name} 토크나이저로 잼:')
    print('  tokens: { ' + ', '.join(f'{k}: {v(tokens[k])}' for k in ('system', 'user', 'template', 'prompt', 'target', 'total')) + ' },')
    if measured:
        print(f'  // target = total − prompt (assistant 본문 {answer} + ' + ('끝 표시(eos)' if a.plain else '턴 끝 표시') + f' {extra})')
    if a.plain:
        print("  plain: true,   // 채팅 틀 없음: 입력 단계 글과 출처 줄이 '채팅 템플릿'을 말하지 않는다")
    print('};')
    sys.exit(0 if measured else 3)


if __name__ == '__main__':
    main()
