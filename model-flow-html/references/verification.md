# 검증 절차

페이지를 게시하기 전에 거치는 순서, 스크린샷에서 볼 것, 헤드리스 Chrome(headless Chrome)의 함정, 프레임 시간 예산, 공개 전 유출 검사를 적는다.
스크립트 네 개는 페이지 안을 모른다. 페이지와는 `window.__mf` 시험 손잡이와 `<mf:count>` 셈 블록으로만 이야기한다.
명령은 스킬 폴더에서 실행한다고 본다. 다른 곳에서 부르면 `scripts/` 앞에 스킬 폴더 경로를 붙인다.

## 1. 준비물

| 도구 | 쓰는 곳 | 없을 때 |
|---|---|---|
| Node.js 18 이상 | `params.mjs`, `make_tests.mjs`, `shoot.mjs` | 검증할 수 없다 |
| Chrome 또는 Edge | `shoot.mjs` | `CHROME` 환경 변수에 실행 파일 경로를 넣는다 |
| ffmpeg | `shoot.mjs --sheet` 의 3×3 모음 | 모음만 건너뛰고 낱장은 찍는다 |
| Python 3.9 이상 + transformers | `count_tokens.py` | tokenizers 로 내용 토큰만 잰다(종료 코드 3). `--plain` 은 tokenizers 만으로 끝까지 잰다 |

브라우저는 `CHROME` 환경 변수를 먼저 보고, 없으면 Windows 는 Program Files, Program Files (x86), LOCALAPPDATA 아래의 Chrome 다음 Edge, macOS 는 /Applications 와 ~/Applications 의 Chrome, Chromium, Edge, Linux 는 PATH 의 google-chrome, google-chrome-stable, chromium, chromium-browser, microsoft-edge 순서로 찾는다.

## 2. 순서

### 2-1. 수치: config 에서 MODEL·LORA 만들기

```bash
node scripts/params.mjs --config <model_dir> --lora r=16,alpha=32,targets=all --expect total=<공개 전체 수>,trainable=<공개 학습 수>
```

- `<model_dir>` 자리에는 config.json 이 든 폴더, config.json 파일, 허브 캐시의 `models--<org>--<name>` 폴더 중 하나를 넣는다.
- 셈은 템플릿의 `<mf:count>` 블록이 한다(기본 `assets/template.html`). 출력 끝에 붙여 넣을 `const MODEL = {...}; const LORA = {...};` 가 나온다.
- 종료 코드: 0 = 맞음, 1 = `--expect` 어긋남, 2 = 입력 오류. 1 이면 bias, tied, head_dim 해석부터 다시 본다. 숫자를 페이지에 손으로 적어 맞추지 않는다.
- `--expect` 는 `total=1,235,814,400` 처럼 논문 표기 그대로 써도 된다.
- `targets` 는 `all`, 논리 키(`q,k,v,o,gate,up,down` 또는 `fc,proj`), 모듈 이름(`q_proj`, `qkv_proj`, `c_attn` …)을 받는다.
  phi3·gpt2 처럼 합쳐진 Linear 에 PEFT 로 붙이면 A 를 함께 써서 실제 학습 수가 논리 모듈별 셈보다 적다. 출력의 `주의:` 줄이 두 값을 함께 적는다.
- 모르는 model_type 이면 `--override '<json>'` 으로 넘길 항목과 config 에서 읽은 후보를 보여 주고 멈춘다.
  qk-norm 처럼 층마다 norm 이 더 있는 모델은 셈 블록이 그 값을 빠뜨린다. 공개 합계와 꼭 맞춰 본다.

페이지를 고친 뒤에는 그 페이지의 셈 블록으로 다시 센다. 블록을 건드리지 않았는지도 함께 확인된다.

```bash
node scripts/params.mjs --config <model_dir> --template <page.html> --lora r=16,alpha=32,targets=all --expect total=<N>,trainable=<N> --json
```

### 2-2. 토큰: 예시 입력 재기

```bash
python scripts/count_tokens.py --model <model_dir> --messages <messages.json> --template-kwargs '{"date_string":"26 Jul 2024"}'
```

- `<model_dir>` 자리에는 토크나이저 파일이 든 폴더나 허브 캐시의 `models--<org>--<name>` 폴더를 넣는다(`refs/main` → `snapshots/<rev>` 로 푼다).
- `<messages.json>` 은 `[{"role": "system", "content": "..."}, ...]` 이고 마지막 메시지가 답(target)이다.
- total, prompt(`add_generation_prompt=True`), target = total − prompt, 역할별 내용 토큰, template = prompt − system − user 를 재서 `EXAMPLE` 블록으로 찍는다. 여러 턴이면 앞선 assistant 본문은 template 에 함께 들어가고, `참고:` 줄이 그 수를 알린다.
- Llama 3 계열 템플릿은 오늘 날짜를 끼워 넣는다. `date_string` 을 고정해야 매번 같은 토큰이 나온다. 틀이 쓰지 않는 인자를 넘기면 `참고:` 줄이 '필요 없는 인자'라고 알린다.
- messages 에 system 이 없을 때 틀이 기본 system 글을 넣는 모델(Qwen2.5 등)은 `참고:` 줄이 그 토큰 수를 알린다. 그 토큰은 template 에 들어가고 페이지의 대화 상자에는 보이지 않으므로, 예시에 system 을 직접 넣는다.
- 종료 코드 3 은 transformers 나 채팅 템플릿이 없어 내용 토큰만 쟀다는 뜻이다. 비어 있는 값(null)을 페이지에 넣지 않는다.
- 채팅 틀이 없는 기본 모델(GPT-2 등)은 `--plain` 을 붙인다. system 은 넣지 않고(0), prompt = user 본문(+BOS), target = 답 본문 + eos, template = prompt − user 로 잰다. 블록의 messages 에서도 system 이 빠지고, `plain: true` 가 붙는다.
- PowerShell 에서 한글이 깨지면 먼저 `[Console]::OutputEncoding = [Text.Encoding]::UTF8` 을 실행한다.
- PowerShell 7.3 이상은 위 JSON 인자를 그대로 넘긴다. Windows PowerShell 5.1 은 안쪽 큰따옴표를 지우므로 JSON 을 파일에 써서 `--template-kwargs <kwargs.json>` 처럼 경로를 넘긴다. `params.mjs --override` 도 같다.

### 2-3. 문법 검사와 시험판

```bash
node scripts/make_tests.mjs <page.html> <outdir> --ship <outdir>/standalone.html
```

- 인라인 `<script>` 를 `<outdir>/_check.js` 로 꺼내 `node --check` 한다. 틀리면 종료 코드 1.
- 조각 약속도 훑어 `경고:` 로 알린다. `<title>` 로 시작하는지, doctype·html·head·body 가 없는지, Google Fonts 말고 바깥 자원이 없는지, `<mf:count>` 블록과 `window.__mf` 가 있는지 본다.
- `--ship` 사본은 조각 앞머리의 `<title>`, `<meta>`, `<link>` 를 `<head>` 로 옮기고 나머지를 `<body>` 에 넣는다. 테마는 강제하지 않는다.
- `<outdir>/test.html` 하나로 모든 장면을 연다. 주소 뒤에 값을 붙인다.

| 값 | 하는 일 |
|---|---|
| `#s<i>` | 단계 i 를 `__mf.go(i, true)` + `__mf.draw()` 로 바로 그리고, `document.fonts.ready` 뒤에 한 번 더 그린다 |
| `?theme=light` 또는 `dark` | 조각의 스크립트가 돌기 전에 `<html data-theme>` 을 정한다 |
| `&cond=k` | go 보다 먼저 `__mf.setCond(k)` |
| `&sim=1` | `sweepSeconds(i) + 3` 초만큼 `update(0.05, false)` 를 돌린 뒤 그린다 (훑기 끝 장면) |
| `&perf=1` | 제목에 `PERF <ms>ms/frame boxes .. lines .. texts .. fields .. raster <ms>ms/frame` |
| `&info=1` | 제목에 `MF steps=<n> conds=<n> sweep=[...] keys=[...]` (keys 는 손잡이에 있을 때만) |

예: `<outdir>/test.html?theme=dark&cond=0&sim=1#s8`. 손잡이가 없거나 그리다 오류가 나면 제목이 `MF-ERROR ...` 로 바뀐다.

### 2-4. 찍기

```bash
node scripts/shoot.mjs <outdir> --steps all --sizes 1600x900,520x900 --themes light,dark --sheet --perf all
```

- 먼저 `test.html?info=1` 을 읽어 단계 수, 조건 수, 훑기 단계, 단계 key 를 알린다(예: `페이지: 단계 14개, 조건 2개, 훑기 s8 11.8초`, `단계 key: s0 overview · s1 input · …`). 그 DOM 은 `<outdir>/shots/info-dom.html` 에 남는다.
- `--steps`, `--perf` 에는 번호(`0-3` 같은 범위도 된다) 대신 단계 key 를 써도 된다. 설정에 따라 빠지는 단계(`train`, `results` 등)가 있어 번호는 당겨져도 key 는 그대로다. 없는 key 를 주면 있는 key 를 보여 주고 멈춘다.
- 낱장은 `<outdir>/shots/<theme>-<cond>-<w>x<h>-s<i>.png` 이다. `--conds` 를 주지 않으면 페이지 기본 조건으로 찍고 `<cond>` 자리에 `def` 를, 주면 `c0`, `c1` … 을 쓴다.
- 훑기가 있는 단계는 `sim=1` 을 붙여 끝 장면을 찍는다. 첫 장면을 보려면 `--sim off`. 그 그림은 이름 끝에 `-simoff` 가 붙어(`…-s8-simoff.png`) 끝 장면 그림을 덮어쓰지 않는다.
- 모음은 `<outdir>/sheets/<theme>-<cond>-<w>x<h>-<n>.png` 이다. 단계 순서대로 왼쪽 위부터 9칸씩 채우고, 요약에 `[s0 s1 …]` 로 든 단계를 적는다.
- 찍을 때 DOM 도 받아서, `#err` 가 보이거나 제목에 `MF-ERROR` 가 있거나, 그림이 없거나 크기가 W×H 가 아니면 `문제` 로 센다. 문제가 하나라도 있으면 종료 코드 1.
- `--jobs` 는 동시에 띄울 크롬 수(기본 3), `--budget` 은 `--virtual-time-budget` 밀리초(기본 5000)다.
- 같은 이름의 낱장과 모음은 덮어쓴다. 몇 단계만 `--sheet` 로 다시 찍으면 그 모음에는 그 단계만 들어가고 앞서 만든 전체 모음은 바뀐다. 전체 모음이 필요하면 끝에 `--steps all --sheet` 로 한 번 더 돌린다.
- 전체 실행(기본 템플릿 56장)은 기계 부하에 따라 1~20분 걸렸다(같은 날 84초, 11분, 16분). 백그라운드로 돌리고, 고친 뒤에는 바뀐 단계만 `--steps <key,…>` 로 다시 찍는다.

조건(LoRA 페이지), 훑기 첫 장면, 폰 레일 아래쪽은 따로 찍는다. key 는 기본 템플릿 것이다.

```bash
node scripts/shoot.mjs <outdir> --steps lora,layers --sizes 1600x900 --themes light --conds 0,1 --sheet
node scripts/shoot.mjs <outdir> --steps layers --sizes 1600x900 --themes light --sim off
node scripts/shoot.mjs <outdir> --steps overview,input --sizes 520x2000 --themes dark
```

### 2-5. 보고 고치기

모음을 **전부** Read 로 연다. 작은 칸에서 의심스러우면 낱장을 연다. 고친 뒤에는 2-3 부터 다시 돌리고, 설정 숫자를 바꿨으면 2-1 도 다시 돌린다.

## 3. 스크린샷 점검표

- [ ] **층마다 부품이 다 있다.** 개요와 층 훑기 장면에서 층 N개가 모두 같은 상세도로 보인다. 한 층에는 norm, q·k·v(pos 가 rope 면 q·k 에 RoPE), 마스크드 어텐션, o, 더하기 마디, norm, MLP(gate·up → act(gate)×up → down 또는 fc → act → proj), 더하기 마디가 있다. 마지막 norm 은 하나다.
- [ ] **띠는 대상 선형층에만 붙는다.** `LORA.targets` 의 W₀ 바로 오른쪽에만 B(세로, d_out × r)와 A(가로, r × d_in)가 있다. 대상이 아닌 선형층, norm, 임베딩, LM 헤드에는 없다.
- [ ] **기준 조건은 띠를 모두 숨긴다.** `--conds 0,1` 모음에서 `lora:false` 조건은 판에 띠가 한 개도 없고(확대 장면의 B·A 와 식까지), 레일 구조도의 LoRA 꼬리표는 꺼진 모양(흐림)으로 바뀐다.
- [ ] **글자가 겹치거나 잘리지 않는다.** 이름표끼리, 이름표와 상자, 판 가장자리에서 잘린 글자(메시지 카드의 첫 글자가 판 왼쪽 끝에 걸리는 경우 등), 범례에 가린 부품을 본다.
- [ ] **먼 이름표도 읽힌다.** 개요·층 훑기처럼 멀리서 본 장면에서 층 번호와 큰 이름표가 최소 크기 이상이고 화면 밖으로 밀려나지 않는다.
- [ ] **훑기는 마지막 층에서 끝난다.** `sim=1` 로 찍은 훑기 단계에 층 N 이 화면 안에 있다. `--sim off` 장면은 층 1 근처에서 시작한다.
- [ ] **폰 배치와 다크 모드.** 520px 폭에서 판이 위, 레일이 아래이고 가로 스크롤이 없으며 옆 여백이 16px 이상이다. 다크 테마에서 캔버스 배경, 글자, 선의 대비가 충분하다.
- [ ] **좁은 화면에서도 읽힌다.** 판 위 글자는 7.5px 아래로 작아지면 숨는다. 520px 폭의 입력 단계와 softmax 단계에서 예시 문장이 레일에 다시 나오는지(`.narrow`), 사용자 정의 구간의 중요한 글자가 판에서만 보이지 않는지 본다.
- [ ] **`#err` 가 없다.** shoot 요약이 `문제 없음` 이고, 어느 그림에도 붉은 오류 띠가 없다.
- [ ] **레일 구조도의 숫자가 페이지의 숫자와 같다.** 층마다·전체 얼린 값, 학습 값이 params.mjs 출력과 같고, 범례·이름표·단계 글의 숫자와도 같다. `info-dom.html` 은 0단계의 DOM 이라 레일 구조도와 0단계 글의 숫자만 들어 있다. 아래 명령이 그 자리 구분 숫자를 모두 뽑는다. 모두 params.mjs 출력이나 EXAMPLE 에 있는 값이어야 한다. 다른 단계의 글과 캔버스 이름표는 그림으로 본다.

```bash
grep -oE "[0-9]{1,3}(,[0-9]{3})+" <outdir>/shots/info-dom.html | sort -u
```

```powershell
(Select-String -Path <outdir>/shots/info-dom.html -Pattern '\d{1,3}(,\d{3})+' -AllMatches | ForEach-Object { $_.Matches.Value } | Sort-Object -Unique) -join ' '
```

그리지 않은 것(가중치 값 하나하나)과 과장한 것(LoRA 두께, norm 판 크기, 줄인 임베딩·LM 헤드 폭)을 페이지가 밝히는지도 한 번 읽어 본다.

## 4. 헤드리스 함정

- **rAF 가 거의 돌지 않는다.** 헤드리스 Chrome 은 `requestAnimationFrame` 을 몇 번만 부르고 찍는다. rAF 로 끝 장면에 가는 페이지는 페이드 도중을 찍는다. 그래서 시험판은 `go(i, true)` 뒤 `draw()` 로 바로 그리고, 템플릿은 그 한 번으로 맞는 장면을 그려야 한다. 훑기 끝은 `sim=1` 이 고정 dt 로 돌려 만든다.
- **페이드가 중간에 찍힌다.** `setCond(k)` 만 부르고 `go(i, true)` 를 부르지 않으면 띠가 반투명으로 남는다. 조건은 go 보다 먼저 고른다. `go(i, true)` 는 카메라와 모든 투명도를 목표값으로 맞춘다. go 를 다시 부르면 훑기가 처음으로 돌아가므로, 시험판은 글꼴이 온 뒤에도 sim 을 다시 돌린다.
- **첫 resize 전에는 캔버스가 비어 있다.** 캔버스의 기본 크기는 300×150 이고 ResizeObserver 콜백은 나중에 온다. 템플릿은 시작할 때 `resize()` 를 직접 한 번 부르고, 크기를 바꿀 때마다 바로 `draw()` 한다(크기를 바꾸면 캔버스가 지워진다).
- **글꼴이 늦게 온다.** 첫 그림은 대체 글꼴 폭으로 이름표 자리를 잡아 겹침이 실제와 다르다. 시험판은 `document.fonts.ready` 뒤에 다시 그린다. 캔버스에서만 쓰는 글꼴은 DOM 이 쓰지 않으면 받아 오지 않으니 `document.fonts.load()` 로 미리 부른다. 인터넷이 막히면 시스템 글꼴로 찍힌다.
- **가상 시간에서는 시계가 멈출 수 있다.** `--virtual-time-budget` 아래에서는 어떤 콜백 안의 `performance.now()` 와 `Date.now()` 가 멈춰 0ms 가 나온다. 그래서 perf 는 가상 시간 없이 재고, 시험판은 시계가 멈춘 측정을 버린다. PERF 가 0.00 이면 측정이 비었는지부터 의심한다.
- **캔버스 래스터는 미뤄진다.** Chrome 은 2D 캔버스 명령을 기록만 해 두고 나중에 래스터한다. JS 시간만으로는 그리기 비용이 보이지 않는다. 그래서 1픽셀을 읽어 래스터까지 끝내게 한 값을 `raster` 로 함께 잰다.
- **스크린샷은 창 크기만큼만 찍힌다.** 폰 배치에서 레일 아래쪽은 `520x2000` 처럼 키 큰 크기로 따로 본다. 판 높이가 화면 비율(%·vh)이라 키 큰 창에서는 판도 커져 장면이 실제 폰과 다르게 잡힌다. 판은 `520x900` 그림으로 보고, 키 큰 그림에서는 레일만 본다.
- **DPR 은 1 이다.** 얇은 선과 작은 글자가 레티나 화면보다 뭉개져 보인다. 1px 선이 안 보이면 실제 화면에서도 약하다.
- **경로와 프로필.** 주소는 `pathToFileURL` 로 만들어 한글·공백 경로도 열린다. 크롬은 실행마다 시스템 임시 폴더에 새 프로필을 만들어 띄우고 끝나면 지운다. 이미 떠 있는 브라우저와 섞이지 않는다.
- **네트워크.** 페이지가 Google Fonts 스타일시트를 불러오므로 찍을 때 글꼴 요청이 나간다. 그 밖의 바깥 요청은 없다.

## 5. 프레임 시간 예산

`--perf` 는 단계마다 크기별로 `update(0.016)` + `draw()` 를 예열 10프레임 뒤 30프레임 재서 평균을 낸다. 헤드리스, `--disable-gpu`(소프트웨어 래스터), DPR 1, 가상 시간 없음 조건이다.

| 항목 | 뜻 | 예산 (모든 단계, 모든 크기) |
|---|---|---|
| JS | 메인 스레드의 계산과 그리기 기록 | 8ms 이하 |
| 래스터 포함 | 위 + 캔버스 래스터 (`raster`) | 16ms 이하 |

- 넘으면 shoot 의 perf 줄 끝에 `← 예산 넘음` 이 붙는다. 실패로 세지는 않지만 고친다. 픽셀이 가장 많은 1600×900 이 보통 가장 무겁다.
- 값은 실행마다 크게는 두 배까지 흔들린다. 단계별 최댓값으로 보고, 예산 근처면 한 번 더 잰다.
- 기준점: 기본 템플릿(Llama-3.2-1B, 16층, boxes 496, lines 378, texts 337)은 1600×900 에서 가장 무거운 단계(개요·조건·마무리)가 JS 약 3.5~6ms, 래스터 포함 약 4~7ms 였고(실행마다 다름), 가까이 본 단계는 JS 1ms 안팎이었다. 설정만 Llama-3.1-8B(32층, boxes 976)로 바꾼 사본은 JS 약 3ms, 래스터 포함 약 4ms 로, 층이 두 배여도 프레임 시간이 두 배가 되지 않았다.
- 템플릿에는 화면 밖 부품 건너뛰기(`inView`), 작게 보이는 상자를 윗면 하나로 그리기(LOD), 너무 촘촘한 모눈 생략이 이미 들어 있다. 부품을 덧붙여 예산을 넘으면 새 부품도 이 길을 타는지부터 보고, 그다음 이름표 수, 흐름 점(fields) 수, 매 프레임 정렬하는 목록 크기를 줄인다.
- 폰 크기는 캔버스 픽셀이 적어 래스터가 가볍지만, 실제 폰 CPU 는 데스크톱보다 몇 배 느리다. 1600×900 예산을 지키는 것이 폰 대비다.

## 6. 공개 전 유출 검사

공개 저장소에 올리거나 공개 링크로 나눌 페이지는, 그리고 스킬 폴더 자체도 올리기 전에 검사한다. 걸린 것이 0건이 될 때까지 고친다.

1. 비공개 용어 목록을 저장소 **밖** 파일(`<private-terms.txt>`, UTF-8)에 한 줄에 하나씩 적는다. 사람·기관 이름, 계정 이름, 내부 과제명, 비공개 데이터셋 이름, 미발표 수치, 로컬 경로 조각을 넣는다. 빈 줄은 두지 않고(빈 줄은 모든 줄과 맞는다), 줄끝은 LF 로 저장한다(CRLF 면 리눅스·macOS 의 grep 이 놓칠 수 있다). 이 목록 파일은 공개 저장소에 넣지 않는다.
2. 목록으로 찾는다. grep 은 아무것도 못 찾으면 종료 코드 1 이다.

```bash
grep -n -F -f <private-terms.txt> <page.html>
grep -rn -F -f <private-terms.txt> <skill_dir>
```

```powershell
Select-String -Path <page.html> -SimpleMatch -Pattern (Get-Content -Encoding utf8 <private-terms.txt>)
Get-ChildItem -Recurse -File <skill_dir> | Select-String -SimpleMatch -Pattern (Get-Content -Encoding utf8 <private-terms.txt>)
```

3. 모양으로 찾는다: 개인 경로, 이메일, 토큰 모양의 문자열. 스킬 폴더는 bash 에서 `grep -rn -E`, PowerShell 에서 `Get-ChildItem -Recurse -File <skill_dir> |` 로 넘긴다. 이 정규식은 이 문서에 적힌 자기 자신과는 맞지 않는다.

```bash
grep -n -E '[A-Za-z]:\\Users\\|/(Users|home)/[A-Za-z0-9._-]+/|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}' <page.html>
```

```powershell
Select-String -Path <page.html> -Pattern '[A-Za-z]:\\Users\\|/(Users|home)/[A-Za-z0-9._-]+/|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}'
```

4. 눈으로 본다. 이용 조건이 붙은 데이터나 개인 정보 대신 새로 쓴 중립 예시를 쓰는지 확인한다. 평가 결과는 논문에 실린 값만 쓰고, 미발표라면 빼거나 가상값으로 바꾼다(`references/publishing.md`). 스킬 파일에는 기계 경로를 쓰지 않고 `<model_dir>` 같은 자리표시를 쓴다.
