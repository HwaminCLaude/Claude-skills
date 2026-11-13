# template.html API

`assets/template.html`의 설정 항목, 단계 형식, 카메라, 그리기 부품, 시험 손잡이를 정리한다. 색과 배치의 뜻, 글 쓰는 법은 `visual-grammar.md`에 있고, 검증 절차는 `verification.md`에 있다.

## 1. 파일 구조

파일 하나가 Artifact용 조각(fragment)이다. 위에서부터 이 순서로 놓인다.

| 순서 | 내용 |
|---|---|
| `<title>` | 두~네 낱말로 된 이름. 기본값은 "모델 구조 흐름도"이고, 마크업에서 손으로 바꾸는 글자는 이것뿐이다 |
| `<meta name="claude:viewport-fit-sides">`, Google Fonts `<link>` | 외부 자원은 이 글꼴 하나뿐이다 |
| `<style>` | `:root` 색 토큰(다크 값은 두 곳에 다시 정의), 레일과 판 배치, 820px 이하 세로 배치 |
| 마크업 | `#eyebrow` `#h1` `#archbox`(구조도 `#arch`), 단계 글(`#where` `#stitle` `#sbody` `#ssrc`), 이전/다음 단추, 판(`#stage` 안의 `canvas#cv`), 범례 `#pick`, 툴팁 `#tip`, 오류 띠 `#err` |
| `<script>` | ① `<mf:config>` 설정 블록 → ② `<mf:count>` 계산 블록 → ③ 엔진(즉시 실행 함수) |

- ①만 고치면 다른 모델이 된다. 숫자, 단계 글, 구조도, 범례, 머리말(`#eyebrow`, `#h1`)을 모두 ①에서 다시 만든다.
- ②는 `scripts/params.mjs`도 그대로 불러 쓰는 셈의 기준이다. 내용도, 여닫는 표시(`/* <mf:count> … */`, `/* </mf:count> */`)도 바꾸지 않는다.
- ③은 사용자 정의 구간을 넣을 때만 고친다(7절).
- 머리말은 마크업이 아니라 엔진이 쓴다. `#eyebrow`는 LoRA가 있으면 "LoRA 미세조정 · 모델 구조 시각화", 없으면 "모델 구조 시각화"이고, `#h1`은 `MODEL.name + ' 구조 흐름도'`다. 논문에 맞춘 머리말이 필요하면 엔진 끝쪽의 `$('#eyebrow').textContent = …`, `$('#h1').textContent = …` 두 줄의 문자열을 바꾼다. 마크업의 `#eyebrow`, `#h1`에 글을 써 넣어도 이 두 줄이 덮어쓴다.
- 설정 블록 밖에는 모델 숫자(hidden, ffn, vocab, 합계)를 손으로 쓰지 않는다. 고친 뒤에는 그런 숫자가 블록 밖에 없는지 grep으로 확인한다.

## 2. 설정 블록

### 2.1 `MODEL`

| 항목 | 뜻 | 기본값 |
|---|---|---|
| `name` | 제목(`h1`)과 구조도에 쓰는 이름 | `'Llama-3.2-1B-Instruct'` |
| `hidden` | 잔차 폭(`hidden_size`) | `2048` |
| `layers` | 디코더 층 수. 이 수만큼 층을 모두 같은 상세도로 그린다 | `16` |
| `heads`, `kvHeads`, `headDim` | 어텐션 헤드 수, K·V 헤드 수(GQA면 더 작다), 헤드 하나의 차원 | `32`, `8`, `64` |
| `ffn` | MLP 중간 폭(`intermediate_size`) | `8192` |
| `vocab` | 어휘 수 | `128256` |
| `norm` | `'rms'`(가중치만) 또는 `'ln'`(가중치 + 편향) | `'rms'` |
| `mlp` | `'gated'`(gate·up → act(gate) × up → down) 또는 `'plain'`(fc → act → proj) | `'gated'` |
| `act` | 화면에 쓰는 활성화 이름 | `'SiLU'` |
| `pos` | `'rope'`(층마다 q·k 회전, 표 없음), `'learned'`(위치 표를 임베딩 뒤에 더함), `'none'` | `'rope'` |
| `maxPos` | `learned`일 때 위치 표의 줄 수 | `0` |
| `bias` | `{ q, k, v, o, mlp }`. `mlp`는 MLP 선형층 전부에 함께 적용된다 | 모두 `false` |
| `tied` | LM head가 임베딩 표를 함께 쓰면 `true`. 화면에 "공유(tied)"로 적고 개수를 더하지 않는다 | `true` |
| `names` | 체크포인트의 모듈 이름. 키는 `q k v o gate up down fc proj norm1 norm2 normF emb pos head` | `q_proj` … |
| `frozen` | 미세조정할 때 원래 가중치를 두는 방식. 미세조정 페이지가 아니면 `''` | `'4비트(NF4)'` |
| `grid` | 모눈 한 칸에 드는 값의 수 = `grid × grid` | `256` |
| `expect` | 공개된 합계 `{ total, trainable }`. 대조하지 않으려면 `null`, LoRA가 없으면 `trainable: null`. 선택 `src`: 전체 단계의 출처 줄에 "<src>와 일치"로 쓸 이름(기본 '공개된 합계') | `{ total: 1235814400, trainable: 11272192 }` |

- `names`에서 빠진 키는 짧은 기본 이름(`q`, `gate`, `norm` …)으로 채운다.
- `grid`는 모든 차원(hidden, q·k·v 폭, ffn)을 나누면서 hidden × hidden 판의 한 변이 8칸 이상(8~16칸)이 되는 가장 큰 2의 거듭제곱이다. `params.mjs`가 이 규칙으로 골라 준다: hidden 2,048~4,096이면 256, 1,536이면 128, 896·768이면 64.
- 계산 블록이 쓰는 모양(`[d_in, d_out]`)은 아래와 같다.
  - q `[hidden, heads·headDim]`, k·v `[hidden, kvHeads·headDim]`, o `[heads·headDim, hidden]`
  - gated: gate·up `[hidden, ffn]`, down `[ffn, hidden]` / plain: fc `[hidden, ffn]`, proj `[ffn, hidden]`
  - norm 하나 = hidden개(`ln`이면 2 × hidden개). 전체 = 임베딩 + 위치 표 + 층 × layers + 마지막 norm + LM head(tied가 아닐 때만)

### 2.2 `LORA`

```js
const LORA = { r: 16, alpha: 32, targets: ['q', 'k', 'v', 'o', 'gate', 'up', 'down'] };   // null = 어댑터 없음
```

- `targets`에는 `q k v o`와 함께, `gated`면 `gate up down`, `plain`이면 `fc proj`를 쓸 수 있다. 모델에 없는 이름을 넣으면 계산 블록이 멈추고 붉은 띠에 `LoRA target not in this model: fc`처럼 뜬다.
- 학습하는 값 = Σ r·(d_in + d_out) × 층 수. 띠는 `targets`에 든 선형층에만 붙는다.
- `null`이면 띠, 구조도의 `+ LoRA` 꼬리표, 조건 단추, `lora`·`conds`·`train` 단계가 모두 빠지고, 글의 "얼린 값"은 "가중치"로 바뀐다.

### 2.3 `CONDS`

```js
const CONDS = [
  { label: 'LoRA 없음(기준 모델)', color: 'base', lora: false },
  { label: 'LoRA 붙임', color: 'k3', lora: true },
];
```

- 배열 순서 = 범례 단추 순서 = `RESULTS.values` 안쪽 배열의 순서다. 페이지는 **마지막 조건**으로 시작한다.
- `color`는 `base`, `k1`, `k2`, `k3` 가운데 하나다. 다른 값이면 `lora`에 따라 `k3`나 `base`로 바꾼다. 띠, 답 글자, 다음 토큰은 지금 고른 조건의 색을 따르고, 결과 막대는 조건마다 제 색으로 그린다.
- `lora: false`인 조건을 고르면 `lora` 표시가 붙은 것(띠, LoRA 글자)이 모두 사라지고, 구조도의 꼬리표가 흐려진다.
- 조건 단추는 LoRA가 있고 조건이 둘 이상일 때만 나온다. 조건이 하나면 범례에 "LoRA" 색 견본만 남는다.
- 어댑터 여러 벌을 비교할 때는 어댑터 하나를 조건 하나로 넣는다. 대상 모듈은 `LORA.targets` 하나로 같이 쓰고, 조건마다 색만 바뀐다. 조건마다 대상이 다르면 `cond` 옵션으로 조건별 띠를 따로 그려야 한다(6.3절).

### 2.4 `EXAMPLE`

```js
const EXAMPLE = {
  messages: [ { role: 'system', content: '…' }, { role: 'user', content: '…' }, { role: 'assistant', content: '…' } ],
  tokens: { system: 11, user: 9, template: 35, prompt: 55, target: 28, total: 83 },
  src: '새로 쓴 합성 예시',   // 선택: 입력·토큰 단계의 출처 줄 앞에 붙는다
};
```

- 마지막 `assistant` 메시지가 모델이 내놓을 답이다. 대화 상자와 출력 구간의 답 상자에 들어간다.
- `system`, `user` = 본문만 토큰화한 수, `template` = 채팅 틀이 넣은 머리표 토큰(`prompt − system − user`), `target` = `total − prompt`(답 본문과 턴 끝 표시)다.
- `system + user + template = prompt`, `prompt + target = total`이 맞지 않으면 붉은 띠가 뜬다.
- 토큰 수는 `scripts/count_tokens.py`로 잰다. 날짜 줄이 들어가는 틀(Llama 3 계열)은 `date_string`을 고정한다. 채팅 틀이 없는 모델(GPT-2 등)은 `--plain`으로 재고, system은 0, template은 토크나이저가 붙이는 BOS 수(GPT-2는 0)다.
- messages에 system이 없을 때 틀이 기본 system 글을 넣는 모델(Qwen2.5 등)은 그 토큰이 template에 들어가고 대화 상자에는 보이지 않는다. `count_tokens.py`가 `참고:` 줄로 알리니, 예시에 system을 직접 넣는다.
- `src`는 예시가 어디서 왔는지다. 기본은 '새로 쓴 합성 예시'이고, 논문에 실린 예시면 '논문 표 <번호>의 예시'처럼 쓴다.
- `plain: true`는 채팅 틀이 없는 모델(`count_tokens.py --plain`으로 잰 값)이다. 입력 단계 제목과 글, 출처 줄이 '채팅 템플릿' 대신 토크나이저로만 잰 값이라고 쓰고, template 띠는 시작 표시(BOS)로 적는다. `--plain` 출력 블록에 들어 있다.
- 좁은 화면(820px 이하)에서는 판 위의 작은 글자가 숨으므로, 엔진이 입력 단계에 prompt 쪽 메시지를, softmax 단계에 답을 레일에 한 번 더 보인다(`.narrow`).
- 화면에는 대화 상자(한글 28자 폭으로 줄바꿈), 토큰 띠(폭은 토큰 수에 비례), 토큰 점(점 하나 = 토큰 하나)이 그려진다.

### 2.5 `TRAIN`

`{ show: true }`이면 출력 구간 끝에 손실 가리개 띠(프롬프트 자리는 −100, 답 토큰에서만 손실)와 `train` 단계를 둔다. LoRA가 없으면 `show`와 상관없이 그리지 않는다. 손실을 어디에 거는지 논문·코드에서 확인하지 못했으면 `false`로 둔다. 선택 `src`는 그 단계의 출처 줄이다(기본은 −100 레이블 설명).

### 2.6 `RESULTS`

```js
const RESULTS = {
  title: '<그래프 제목>', unit: '%',
  metrics: ['<지표 1>', '<지표 2>'],
  values: [[<조건 0 값>, <조건 1 값>], [<조건 0 값>, <조건 1 값>]],   // 지표마다, CONDS 순서로. 없으면 null
  ci: [[[<하한>, <상한>], [<하한>, <상한>]], …],                    // values와 같은 모양. 없으면 ci: null
  src: '<출처: 논문 표 번호>',
};
```

- `null`이면 결과 구간과 `results` 단계가 빠진다.
- 막대는 바닥에 눕혀 지표마다 조건별로 그린다. `unit: '%'`이면 0~100을 길이 22에 맞추고, 아니면 가장 큰 값에 맞춘다. 값은 막대 끝에 쓰고, 툴팁에 조건·지표·값·구간을 쓴다.
- 결과 수치는 논문 표에서만 가져온다. 공개 저장소에 낼 때는 `publishing.md` 4절을 따른다.

### 2.7 예: GPT-2 small (LayerNorm, plain MLP, 학습된 위치 표, 편향, tied, LoRA 없음)

```js
const MODEL = {
  name: 'GPT-2 small',
  hidden: 768, layers: 12, heads: 12, kvHeads: 12, headDim: 64, ffn: 3072, vocab: 50257,
  norm: 'ln', mlp: 'plain', act: 'GELU(tanh)', pos: 'learned', maxPos: 1024,
  bias: { q: true, k: true, v: true, o: true, mlp: true },
  tied: true,
  names: { q: 'c_attn[q]', k: 'c_attn[k]', v: 'c_attn[v]', o: 'attn.c_proj', fc: 'c_fc', proj: 'mlp.c_proj',
           norm1: 'ln_1', norm2: 'ln_2', normF: 'ln_f', emb: 'wte', pos: 'wpe', head: 'lm_head' },
  frozen: '', grid: 64,
  expect: { total: 124439808, trainable: null },
};
const LORA = null;
const CONDS = [{ label: '기준 모델', color: 'base', lora: false }];
const EXAMPLE = {
  messages: [{ role: 'user', content: 'The capital of France is' }, { role: 'assistant', content: ' Paris.' }],
  tokens: { system: 0, user: 5, template: 0, prompt: 5, target: 3, total: 8 },   // count_tokens.py --plain: 답 2 + eos 1
  plain: true,
};
const TRAIN = { show: false };
const RESULTS = null;
```

- 한 층 7,087,872개, 전체 124,439,808개. 단계는 11개(`lora`, `conds`, `train` 없음)이고, 범례에는 "가중치"와 "흐르는 값"만 남는다.
- 임베딩 구간에 위치 표(1,024 × 768)와 더하기 마디가 생기고, 구조도에 "위치 임베딩" 블록이 붙는다. 어텐션 안에 RoPE 상자는 없다.
- GPT-2 체크포인트는 q·k·v가 `c_attn` 하나(768 × 2,304)로 합쳐져 있다. 템플릿은 q, k, v를 따로 그리므로 이름을 `c_attn[q]`처럼 쓴다(`params.mjs`가 찍는 이름). 개수는 같다.

### 2.8 예: Qwen2.5-0.5B (q·k·v 편향, GQA, tied, LoRA는 q·v만)

```js
const MODEL = {
  name: 'Qwen2.5-0.5B',
  hidden: 896, layers: 24, heads: 14, kvHeads: 2, headDim: 64, ffn: 4864, vocab: 151936,
  norm: 'rms', mlp: 'gated', act: 'SiLU', pos: 'rope', maxPos: 0,
  bias: { q: true, k: true, v: true, o: false, mlp: false },
  tied: true,
  names: { q: 'q_proj', k: 'k_proj', v: 'v_proj', o: 'o_proj', gate: 'gate_proj', up: 'up_proj', down: 'down_proj',
           norm1: 'input_layernorm', norm2: 'post_attention_layernorm', normF: 'norm', emb: 'embed_tokens', head: 'lm_head' },
  frozen: 'bf16', grid: 64,
  expect: { total: 494032768, trainable: 540672 },
};
const LORA = { r: 8, alpha: 16, targets: ['q', 'v'] };
const CONDS = [{ label: '기준 모델', color: 'base', lora: false }, { label: 'q·v LoRA', color: 'k1', lora: true }];
// EXAMPLE.tokens는 이 모델의 토크나이저와 채팅 틀로 count_tokens.py를 돌려 채운다
```

- 한 층 얼린 값 14,912,384개, LoRA 22,528개(q 14,336 + v 8,192), 전체 학습 540,672개.
- k·v 판은 q 판의 1/7 깊이(128 × 896)라 아주 얕다. 이렇게 얕은 판도 크기 글자를 판 위에 쓴다.
- 띠는 q와 v에만 붙고 k, o, MLP에는 없다. 구조도 꼬리표 `+ LoRA q v`는 어텐션 가지에만 달린다.

## 3. 숫자 대조와 붉은 띠(`#err`)

- `expect.total`이 계산값과 다르거나, `expect.trainable`이 `null`이 아닌데 학습 수와 다르면(LoRA가 없으면 0과 비교) 두 값을 함께 적은 띠를 띄운다. 예: "구성으로 센 값이 공개 값과 다릅니다(전체 1,235,814,400개, 공개 값 1,235,814,401개)".
- `EXAMPLE.tokens`의 합이 맞지 않을 때도 띠를 띄운다.
- 스크립트 오류도 같은 띠에 "그림을 그리지 못했습니다: …"로 뜬다. 오류 감시는 계산보다 먼저 걸어 두었으므로 계산 블록의 오류도 잡힌다.
- 띠가 보이는 채로 게시하지 않는다. 띠가 뜨면 고칠 곳은 설정 블록(bias, tied, headDim, targets)이고, 숫자를 손으로 맞추지 않는다.

## 4. 구간과 단계

### 4.1 구간(`ST`)과 장면 번호

| 번호 | 이름 | `ovp` | 판 |
|---|---|---|---|
| 0 | 입력 | 1 | 대화, 토큰 띠, 토큰 점 |
| 1 | 임베딩 | 0 | 임베딩 표(+ 위치 표) |
| 2 | 층 1 · 어텐션 | 0 | norm1 ~ 첫 더하기 |
| 3 | 층 1 · MLP | 0 | norm2 ~ 둘째 더하기 |
| 4 | 층 2~N | 0 | 층마다 판 하나 |
| 5 | 출력 | 1 | 마지막 norm, LM head, 로짓, softmax, 다음 토큰, 손실 가리개 |
| 6 | 결과 | 0 | `RESULTS` 막대 |

- 장면 번호(phase)는 한 구간 안에서 장면을 나눈다. 지금 구간은 단계의 `ph`로, 다른 구간과 전체 보기는 그 구간의 `ovp`로 보인다.
- 그래서 전체 보기에서도 입력 구간은 색이 든 토큰 점(장면 1)으로, 출력 구간은 답 상자가 놓인 장면 1로 보인다.

### 4.2 단계 형식

```js
STEPS.push({ key: 'attn1', st: 2, ph: 0, row: ['r-n1', 'r-att'], t: '제목', h: '<p>본문</p>', src: '출처', cam: { … }, sweep: [za, zb, 초] });
```

| 항목 | 뜻 |
|---|---|
| `key` | 단계 이름. 구조도 단추의 `data-go`와 아래 대체 규칙이 쓴다 |
| `st` | 구간 번호. `-1`은 전체 보기다(모든 구간이 `ov` 투명도로 보인다) |
| `ph` | 그 구간의 장면 번호. 기본 0 |
| `row` | 지금 단계로 테두리를 그을 구조도 블록 id: `r-in r-emb r-pos r-xN r-n1 r-att r-l1 r-add1 r-n2 r-ffn r-l2 r-add2 r-fn r-head r-soft r-res` |
| `t`, `h`, `src` | 제목, 본문 HTML(`<p>` 1~3개), 출처 줄 |
| `cam` | 카메라(5절) |
| `sweep` | 층 훑기 `[시작 z, 끝 z, 초]`. 없으면 넣지 않는다 |

### 4.3 기본 단계와 빠지는 조건

| `key` | 구간·장면 | 보이는 것 | 빠지는 때 |
|---|---|---|---|
| `overview` | −1 | 전체 보기 | — |
| `input` | 0·0 | 대화, 토큰 띠 | — |
| `tokens` | 0·1 | 토큰 점, 프롬프트/답 색 | — |
| `emb` | 1·0 | 임베딩 표(+ 위치 표, 더하기) | — |
| `attn1` | 2·0 | norm1, q·k·v와 크기 | — |
| `lora` | 2·1 또는 3·1 | 첫 대상 선형층 확대: W₀, 저장 방식, B·A, 식, r·α | LoRA 없음. 대상이 MLP에만 있으면 `mlp1` 뒤로 간다 |
| `attn2` | 2·2 | RoPE, 마스크드 어텐션, o, 더하기 | — |
| `mlp1` | 3·0 | norm2, MLP, 더하기 | — |
| `layers` | 4·0 | 층 2부터 마지막 층까지 훑기 | — |
| `conds` | 4·1 | 가운데 층들에서 조건 비교 | LoRA 없음, 또는 조건 하나 |
| `out` | 5·0 | 마지막 norm, LM head, 로짓 | — |
| `soft` | 5·1 | softmax, 다음 토큰, 되돌아가는 고리, 답 상자 | — |
| `train` | 5·2 | 손실 가리개 | `TRAIN.show`가 거짓, 또는 LoRA 없음 |
| `results` | 6·0 | 결과 막대 | `RESULTS`가 `null` |
| `end` | −1 | 전체 보기, "그린 것과 줄인 것" | — |

- 주소는 `#s<번호>`(0부터)다. 빠진 단계만큼 번호가 당겨지므로, 스크립트는 `__mf.keys`로 key에서 번호를 찾는다.
- 없는 key로 가라고 하면 `lora → attn1`, `conds → layers`, `train → soft`, `results → end`로 대신 가고, 그 밖은 0번으로 간다.
- 훑기는 층당 0.6초, 전체 6~24초다. 시작 전에 1.2초 기다린다.

### 4.4 단계 글 고치기

- `STEPS.push({ … })`의 `t`, `h`, `src` 문자열만 고친다. 숫자는 `COUNTS`, `GEO`, `TK` 같은 계산값을 `fmt()`로 끼운다.
- 조사는 `pp(낱말, '을', '를')`, 모듈 이름은 `cj(NN.q, '이', '가')`(`<code>q_proj</code>가`)로 붙인다. 숫자와 로마자는 읽는 소리로 받침을 어림한다.
- 출처 줄에는 `모델 구성(config)`, `논문 표 <번호>`, `이 예시를 따로 잰 값`처럼 숫자가 나온 곳을 적는다. 기본 단계의 출처 줄은 `EXAMPLE.src`, `MODEL.expect.src`, `TRAIN.src`로 바꿀 수 있다.

## 5. 카메라

### 5.1 세 가지 형식

| 형식 | 동작 |
|---|---|
| `{ x, z, span, dz, pitch, yaw }` | 바닥의 점 (x, 0, z)를 본다. 거리 = max(1.94 · span / 화면비, 2.25 · dz · sin(pitch)). span은 가로로 들어올 폭, dz는 깊이로 들어올 길이다 |
| `{ x, z, dist, pitch, yaw }` | 거리를 정한다. 화면비가 1.3보다 좁으면 1.3 / 화면비만큼 멀어진다 |
| `{ fit: [x0, x1, z0, z1], pitch, yaw }` | 바닥 직사각형의 네 모서리가 여백(좌우 5% + 12px, 위 5% + 12px, 아래 5% + 60px, 범례 자리) 안에 드는 가장 가까운 거리를 찾는다. 창 크기가 바뀔 때마다 다시 찾는다 |

- `pitch`는 0이 수평, π/2가 바로 위다. 기본 0.95이고, 끌기로는 0.18~1.48까지 움직인다. `yaw`는 기본 0이고, 음수면 카메라가 왼쪽(−x)으로 돈다.
- 카메라는 +z 쪽에서 −z 쪽(입력)을 바라본다. 그래서 입력이 화면 위쪽(먼 쪽), 출력이 아래쪽에 온다.
- 크기 감: q 판(hidden × hidden)은 4.4, 층 하나의 깊이 `PB`는 8B 기준 64다. 기본 단계의 카메라는 `GEO`와 `PB`로 계산하므로 모델이 바뀌어도 같은 구도가 나온다.
- 전체 보기(`overview`, `end`)와 결과 단계는 `fit`을 쓴다. 휠·핀치 거리는 10 ~ `MAXD`이고, `MAXD` = max(300, 1.2 × 전체 길이, 맞춤 거리 × 1.25)다.

### 5.2 훑기(`sweep`)

- `sweep: [za, zb, T]`이면 단계로 들어간 뒤 1.2초 기다렸다가 T초 동안 카메라가 보는 z를 za에서 zb로 옮긴다(부드럽게 시작하고 멈춤). 가로 위치, 거리, 각도는 `cam` 값 그대로다.
- 기본 `layers` 단계는 층 2의 가운데에서 마지막 층의 가운데까지 훑는다. 거리는 층 하나(`1.15 × PB`)가 위아래로 다 들어오게 잡는다.
- 화면을 끌어 옮기면 훑기가 멈춘다. `prefers-reduced-motion`이면 훑지 않고 바로 끝 장면으로 간다.

## 6. 그리기 부품 `B(st)`

### 6.1 좌표

- x는 오른쪽, y는 위(높이, 뜻 없음), z는 아래(데이터가 흐르는 방향)다. 잔차 줄기는 x = 0에 있다.
- `U = 4.4 / hidden`은 값 하나의 길이다. 선형층 W(d_out × d_in)는 가로 d_in·U, 깊이 d_out·U로 그린다.
- 층 L은 `zbOf(L) = ZB1 + (L − 1) · PB`에서 시작한다. 층 안의 자리는 `GEO`(z는 층 시작에서 잰 값)에 있고, 출력 구간은 `ZO = ZB1 + layers · PB`에서 시작한다.
- 판의 가로 범위(`PXL`, `PXR`)는 다 그린 뒤 상자와 글자에서 다시 잰다. 새 부품을 그 측정보다 앞에서 그리면 판이 알아서 넓어진다.

### 6.2 함수

```js
const b = B(st);                                  // st = 구간 번호
b.box(x, z, w, d, y0, h, color, opts);            // 가운데 (x, z), 가로 w, 깊이 d, 바닥 높이 y0, 높이 h
b.text(x, y, z, s, opts);                         // 화면을 향해 서 있는 글자
b.line([[x, y, z], [x, y, z], …], opts);          // 꺾은선
b.dots(n, size, [{ pos: (k) => [x, y, z], col: (k) => '색' }, …], opts);   // 점 n개, 장면마다 자리·색
b.unit(x, z, din, dout, name, { target, bias, …opts });                    // 선형층 하나
```

- `unit`의 (x, z)는 W₀의 왼쪽 위 모서리다. W₀(파랑, 높이 0.6, 모눈 `[din/grid, dout/grid]`)와 툴팁(모양, 개수, 편향, 저장 방식, 모눈 축척)을 알아서 만든다.
  - `target: true`이고 LoRA가 있으면 W₀ 오른쪽에 B(두께 × dout·U, W₀에서 0.3 띄움)와 A(din·U × 두께, B 오른쪽 끝에서 0.3 띄움, W₀ 윗변에 맞춤)를 붙인다. 둘 다 `lora: true`다.
  - `bias`는 편향 개수로, 툴팁에만 쓴다.
  - 돌려주는 값: `{ x0, x1, cx, z0, z1, cz, xr, bx, ax }`. `xr`은 띠까지 넣은 오른쪽 끝, `bx`·`ax`는 B·A의 가운데 x다.
- `dots`의 장면 배열은 그 구간의 장면 번호 순서다. 장면이 바뀌면 점이 새 자리와 색으로 옮겨 간다. `gridPos(cols, pitch, cx, cz, y, n)`이 격자 배치 함수를 만들어 준다.
- 색 이름: `bg plate plateOn plateDone cell dot faint w act base k1 k2 k3 bad onc ink ink2 line accent lora`. CSS 토큰 `--c-<이름>`에서 읽고, `lora`는 지금 조건의 색이다.

### 6.3 공통 옵션

| 옵션 | 뜻 |
|---|---|
| `ph: [장면…]` | 그 구간이 이 장면일 때만 보인다 |
| `dim: [장면…]` | 그 구간이 지금이고 이 장면이면 투명도 0.14로 흐리게 한다(LoRA 확대 때 나머지를 흐리는 데 쓴다) |
| `cond: k` | 조건 k를 골랐을 때만 보인다 |
| `lora: true` | `lora: false` 조건에서 감춘다 |
| `always: true` | 언제나 보인다(줄기, 흐르는 점) |
| `rest`, `ov` | 다른 구간이 지금일 때, 전체 보기일 때의 투명도. 기본값: box 0.9 / 0.97, line 0.7 / 0.85, dots 0.9 / 0.97, text 0 / 0 |
| `meta` | 툴팁. box는 문자열, dots는 `(k, 장면) => 문자열` |
| `grid: [가로 칸, 깊이 칸]` | box 윗면 모눈. `unit`이 알아서 넣는다 |
| `fixw: true` | line 굵기를 고정한다. 멀리 있는 선은 원래 가늘어진다 |
| `c`, `w` | 색 이름과 굵기. line 기본값은 `'ink2'`, 1.5px. text의 `w`는 글자 굵기다 |
| `size`, `al`, `mono` | text 크기(세계 단위), 맞춤(`'left'`, `'right'`, 기본 가운데), 고정폭 글꼴 |

- 보일지 정하는 순서: `lora` → `cond` → `always` → `ph` → 전체 보기면 `ov` → 다른 구간이면 `rest` → `dim` → 1.
- 글자는 화면에서 7.5px보다 작으면 숨기고, 30px에서 더 커지지 않는다. 그래서 층 2~N의 이름표는 가까이 갈 때만 보인다.

### 6.4 판(`PL`)

```js
PL.push({ z0, z1, st, name, far, L });
```

- `name`은 가까이 볼 때 판 왼쪽에 쓰는 이름이다. `far`는 멀리서도 남길 이름이고, 없으면 멀 때 숨긴다. 층 판은 `farOf(L)`로 4개 안팎과 마지막 층만 `far`를 받는다. `L`이 있으면 판을 눌렀을 때 그 층으로 간다.
- 전체 보기(`st: -1`)에서는 크게 다가가기 전까지 `far` 이름표만 보인다. 층 수가 적어 카메라가 가까워도 이름표가 4개 안팎으로 남는다.
- 판은 z 순서대로 넣는다. 마지막 판의 `z1`이 전체 끝(`ZEND`)이 되고, 전체 보기 맞춤과 확대 한계가 그 값을 쓴다.

## 7. 사용자 정의 구간 넣기 (예: 논문의 평가)

논문에만 있는 내용은 같은 부품으로 구간을 하나 덧붙인다. 점 하나 = 한 개(count-true)를 지키고, 색은 토큰 이름으로만 쓴다(실패나 오류 개수는 `bad`).

1. `ST` 배열 끝에 구간을 더한다: `{ name: '평가', ovp: 0 }`(번호 7).
2. 결과 구간(`const RS = …`) 뒤, "판의 가로 범위" 블록 앞에서 그린다.

```js
/* ---- 7 평가(논문 고유): 점 하나 = 평가 문항 하나 */
const EV = (() => {
  const b = B(7), z0 = PL[PL.length - 1].z1 + 1.6;
  const n = <문항 수>, ok = <통과 수>;                      // 논문 표의 값. 출처는 단계의 src에 적는다
  const cols = 20, p = 0.9, gp = gridPos(cols, p, 0, z0 + 6, 0.12, n);
  b.text(-9, 0.3, z0 + 2.2, '평가 문항 ' + fmt(n) + '개', { al: 'left', size: 0.8, w: 600 });
  b.dots(n, p * 0.5, [{ pos: gp, col: () => 'cell' }, { pos: gp, col: (k) => (k < ok ? 'lora' : 'bad') }],
    { meta: (k, ph) => (ph === 0 ? '평가 문항 한 개' : k < ok ? '통과' : '실패') });
  const z1 = z0 + 6 + Math.ceil(n / cols) * p + 2;
  PL.push({ z0, z1, st: 7, name: '평가', far: '평가' });
  return { z0, z1, n };
})();
```

3. 단계는 `end` 바로 앞(`STEPS.push({ key: 'end', …` 위)에 넣는다. 장면 0과 1을 나누면 점이 회색에서 결과 색으로 바뀐다.

```js
STEPS.push({ key: 'eval', st: 7, ph: 0, row: ['r-eval'], t: '평가 문항', h: '<p>…</p>', src: '논문 표 <번호>',
  cam: { fit: [-12, 12, EV.z0, EV.z1], yaw: -0.15, pitch: 1.15 } });
STEPS.push({ key: 'eval2', st: 7, ph: 1, row: ['r-eval'], t: '통과와 실패', h: '<p>…</p>', src: '논문 표 <번호>',
  cam: { fit: [-12, 12, EV.z0, EV.z1], yaw: -0.15, pitch: 1.15 } });
```

- 점은 화면을 향한 네모라서 비스듬히 보면(pitch가 낮으면) 줄끼리 겹쳐 막대처럼 보인다. 점 무늬는 위에서 내려다보는 각도(pitch 1.1 안팎)로 보고, 점 크기는 간격의 절반쯤으로 둔다.

4. 구조도: `railHTML()`의 `r-res` 줄 아래에 `s += blk('r-eval', 'eval', '', '평가', '문항 ' + fmt(EV.n) + '개');`를 넣는다.
5. 확인: 전체 보기에 새 판까지 들어오는지, `__mf.keys`에 `eval`이 있는지, 툴팁, 다크 테마, 520px 폭에서 글자가 겹치지 않는지 스크린샷으로 본다.

- 조건마다 결과가 다르면 `cond: k`로 조건별 점이나 막대를 따로 그린다. 범례 단추로 바꿔 볼 수 있다.
- 개수가 수만 개라 점이 너무 작아지면, 점 하나가 몇 개인지 정하고 그 단위를 판 위 글자와 툴팁에 적는다.
- 이용 조건이 붙은 데이터나 개인 정보가 든 원본은 그리지 않는다. 예시는 합성으로 쓰고 출처 줄에 "합성 예시"라고 적는다.

## 8. 시험 손잡이 `window.__mf`

| 항목 | 뜻 |
|---|---|
| `go(i, snap)` | 단계 i로 간다. `snap`이면 카메라와 투명도를 바로 끝 상태로 맞춘다(훑기는 처음부터) |
| `setCond(k, snap)` | 조건 k를 고른다. `snap`이면 바로 끝 상태로 맞춘다 |
| `update(dt, snap)` | dt초만큼 진행한다(카메라, 페이드, 훑기, 흐르는 점) |
| `draw()` | 지금 상태를 한 장 그린다 |
| `steps` | 단계 수 |
| `sweepSeconds(i)` | 단계 i의 훑기가 끝나고 카메라가 자리 잡을 때까지의 초(1.2 + T + 1.0). 훑기가 없으면 0 |
| `counts` | `countParams()` 결과: `shapes`, `layer`, `emb`, `pos`, `head`, `normF`, `layers`, `total`, `lora` |
| `conds` | 조건 수 |
| `stats()` | `{ boxes, lines, texts, fields }` 부품 개수 |
| `keys` | 단계 key 배열(번호 순) |

- 끝 장면: `setCond(k); go(i, true); draw();`. 훑기 단계는 `go` 뒤에 `update(0.05, false)`를 `ceil(sweepSeconds(i) / 0.05)`번 이상 돌리고 그린다(`make_tests.mjs`의 시험판은 카메라가 자리 잡을 여유로 3초를 더 돈다).
- 헤드리스 Chrome에서는 rAF가 거의 돌지 않으므로 손잡이로 직접 그린다. 글꼴이 늦게 오면 글자 폭이 바뀌므로 `document.fonts.ready` 뒤에 한 번 더 그린다. `scripts/make_tests.mjs`의 시험판이 이렇게 한다.
- 프레임 시간: `update(0.016, false)` + `draw()` 30번의 평균. 8B(층 32개) 전체 보기도 몇 ms 안에 든다.
- 시험은 이 손잡이로만 페이지와 이야기한다. 안쪽 변수에 기대는 시험은 만들지 않는다.

## 9. 일부러 다르게 그린 것과 그 까닭

실제 비율대로 그리면 보이지 않거나 화면을 벗어나는 것만 바꾸었다. 바꾼 것은 툴팁과 마지막 단계 글에 적혀 있고, 보고할 때도 말한다(`visual-grammar.md` 10절).

| 무엇 | 템플릿 값 | 실제 비율이라면 | 까닭 |
|---|---|---|---|
| LoRA 띠 두께 | 0.34 | r·U(r 16, hidden 2,048이면 0.034) | 모눈 한 칸보다 훨씬 얇아 보이지 않는다 |
| norm 판 | 6 × 1.0 | 값 hidden개, 한 줄(4.4 × U) | 보이지 않는다 |
| 임베딩 표, LM head | 가로 19 | vocab·U(128,256 × 2,048이면 약 276) | 판이 화면 밖까지 길어진다 |
| 위치 표(`learned`) | min(19, maxPos·U) | maxPos·U | 짧으면 실제 길이 그대로다(GPT-2는 약 5.9) |
| 어텐션 상자 | 8.4 × 6.6, 삼각형 16줄 | 학습하는 값 없음 | 가림 모양만 보여 준다. 실제 점수가 아니다 |
| 더하기, 활성화, RoPE, softmax 상자 | 고정 크기 | 학습하는 값 없음 | 연산의 자리 표시다 |
| 결과 막대 | 바닥에 눕힘, 길이 22 = 100% 또는 최댓값 | — | 막대와 숫자가 서로 가리지 않게 |
| 줄기 위 흐르는 점 | 장식 | — | 흐름 방향만 보여 준다. 개수에 뜻이 없다 |

실제 그대로인 것: 층 수, 모든 선형층의 가로·깊이, 모눈 축척(한 칸 = grid × grid 값), 토큰 점의 개수, 화면의 모든 개수. 값 하나하나(가중치의 숫자)는 그리지 않는다.
