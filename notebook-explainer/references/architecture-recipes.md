# Architecture & Shape Recipes

ML/딥러닝 코드 전용 위젯. `widget-recipes.md`(범용 5종)와 함께 쓴다.
아래 패턴은 전부 `mnist_workflow_인터랙티브_해설.html` 에서 **실제로 동작하는 것을 추출**한 것이다.
값과 색은 페이지 팔레트에 맞게 바꾸되, 구조는 그대로 두는 편이 안전하다.

## 언제 이 파일을 읽나

소스에 다음이 하나라도 있으면 읽는다:
`nn.Module` · `Sequential` · `Model(` · `Conv` · `LSTM`/`GRU` · `Embedding` ·
`model.summary()` · `.reshape(` · `.view(` · `transforms.` · `DataLoader`

---

## 0. 차원 의미색 — 이 파일의 전제

shape 시각화는 색이 의미를 가질 때만 효과가 있다. 최소 네 종류를 구분한다.

```css
--spatial:#E8833A;   /* 공간 차원 28×28, 26×26 — 이미지의 가로세로 */
--feature:#2D5BE0;   /* 특징 차원 784, 256, 288 — 한 줄로 편 벡터 */
--klass:#12A594;     /* 클래스 차원 10 — 정답 후보 개수 */
--batch:#8A93A6;     /* 배치 차원 None/B — 실행 시점에 정해짐 */
```

이 색이 있으면 "MLP는 시작하자마자 주황→파랑, CNN은 Flatten까지 주황 유지"가
**설명 없이 그림만으로** 전달된다. 히어로에 범례를 반드시 넣는다.

shape 칩과 출처 배지:

```html
<span class="shp sp">(None, 26, 26, 32)</span>
<span class="badge obs">관측값</span>   <!-- 출력에 실제로 찍힘 -->
<span class="badge inf">추정</span>     <!-- 코드에서 계산 -->
<span class="badge sym">기호</span>     <!-- None/B 등 런타임 결정 -->
```

**출처를 섞지 말 것.** `model.summary()` 가 있으면 그 표가 정답이다.
없으면 전부 `추정` 이고, 그 사실을 셀 단위로 명시한다.

---

## 1. 단일 데이터 배열 — R6와 R7이 어긋나지 않게

가장 중요한 구조적 결정. **추적기 표와 블록 다이어그램을 같은 배열에서 그린다.**
따로 쓰면 반드시 어긋난다(층을 하나 고칠 때 한쪽만 고치게 된다).

```js
const ARCH = {
  cnn: {
    card:'n15',                    // 이 모델을 만든 코드 카드의 note id
    tracer:'cnnTracer', tout:'cnnTracerOut',
    arch:'cnnArch',     aout:'cnnArchOut',
    input:{n:'Input', shape:'(None, 28, 28, 1)', kind:'sp'},
    total:'21,706',
    layers:[
      {n:'conv2d (Conv2D)', shape:'(None, 26, 26, 32)', kind:'sp', p:'320', line:25,
       why:'3×3 필터는 가장자리에서 벗어날 수 없어 <b>28 − 3 + 1 = 26</b>. 파라미터는 <b>3×3×1×32 + 32 = 320</b>개뿐.'},
      // …
    ]
  }
};
const KINDCSS={sp:'var(--spatial)',fe:'var(--feature)',kl:'var(--klass)'};
```

`line` 은 그 층을 만든 **코드 줄 번호**다. 이게 A-5 양방향 결합의 열쇠다.
`why` 는 "모양이 왜 그렇게 됐는지"를 **계산식과 함께** 쓴다 — 이름만 반복하면 가치가 없다.

### 배열을 만드는 절차 (이걸 건너뛰면 양방향이 조용히 끊긴다)

1. 소스에서 층을 만드는 호출을 **등장 순서대로** 모은다
   (`model.add(...)` / `Dense(...)(x)` 같은 functional 호출 / `nn.Sequential` 내부 항목).
2. 그 순서 번호가 곧 `layers[]` 의 인덱스다. **`model.summary()` 표의 행 순서와 일치해야 한다** —
   어긋나면 shape을 엉뚱한 층에 붙이게 되므로 반드시 대조한다.
   (`Activation`·`Dropout` 을 별도 층으로 쓴 경우 summary에도 별도 행으로 나온다는 점에 주의)
3. 각 층의 코드 줄 번호를 `line` 에 넣는다. 이때 줄 번호는 **해설 페이지의 코드 카드에 찍는
   번호**(`.no` 텍스트) 기준이다 — 원본 셀의 물리적 줄 번호와 같게 유지하는 편이 안전하다.
4. **같은 코드 줄에 `data-viz="모델키:층인덱스"` 를 단다.** 이게 코드→시각화 방향이다.
   빠뜨리면 표와 다이어그램은 멀쩡히 동작하는데 코드 줄을 눌러도 아무 일이 없고,
   페이지만 봐서는 알아채기 어렵다. `verify_page.js` 가 이 경우를 FAIL로 잡는다.

```html
<!-- layers[5] 가 flatten 이고, 그 층을 만든 줄이 30번이면 -->
<div class="ln" data-viz="cnn:5" data-n="드디어 편다. 3×3×32 = 288짜리 벡터가 된다.">
  <span class="no">30</span><pre>model.add(Flatten())</pre>
</div>
```

---

## 2. R6 · 텐서 Shape 추적기

`레이어 | 입력 모양 | 출력 모양 | 파라미터` 4열 표. 입력 모양은 앞 층의 출력을 물려 쓴다.

```js
let prev=A.input.shape, h=
  '<div class="trow head"><span>레이어</span><span>입력 모양</span><span>출력 모양</span><span class="pcount">파라미터</span></div>'+
  '<div class="trow" style="cursor:default"><span class="lname">'+A.input.n+'</span><span>—</span>'+
  '<span><span class="shp '+A.input.kind+'">'+A.input.shape+'</span></span><span class="pcount">0</span></div>';
A.layers.forEach((L,i)=>{
  h+='<div class="trow" data-k="'+key+'" data-i="'+i+'">'+
     '<span class="lname">'+L.n+'</span>'+
     '<span><span class="shp '+(i===0?A.input.kind:A.layers[i-1].kind)+'">'+prev+'</span></span>'+
     '<span><span class="shp '+L.kind+'">'+L.shape+'</span></span>'+
     '<span class="pcount">'+L.p+'</span></div>';
  prev=L.shape;
});
h+='<div class="trow" style="cursor:default;font-weight:600"><span>합계</span><span></span><span></span>'+
   '<span class="pcount">'+A.total+'</span></div>';
```

> **함정 (실제로 밟았음).** 하이라이트할 때 행을 `.trow:not(.head)` 로 고르면
> **입력 행과 합계 행까지 섞여 인덱스가 한 칸씩 밀린다.**
> 반드시 `.trow[data-i]` 로 층 행만 고른다.

```css
.trow{display:grid;grid-template-columns:1.4fr 1fr 1fr .8fr;gap:10px;padding:11px 15px;
      align-items:center;border-top:1px solid var(--paper);cursor:pointer}
.trow.on{background:rgba(45,79,224,.07);box-shadow:inset 3px 0 0 var(--wire)}
@media(max-width:700px){.trow{grid-template-columns:1fr 1fr;row-gap:5px}}
```

---

## 3. R7 · 블록 다이어그램 (인라인 SVG, 라이브러리 금지)

세로 블록 + 화살표. **화살표마다 다음 층의 출력 모양을 라벨로 단다.**

```js
const all=[A.input].concat(A.layers);
const BW=286, BH=42, GAP=40, X=60, W=560;
const H=all.length*BH+(all.length-1)*GAP+16;
let s='<svg viewBox="0 0 '+W+' '+H+'" width="'+W+'" role="img" aria-label="모델 구조 다이어그램">';
all.forEach((L,i)=>{
  const y=8+i*(BH+GAP), col=KINDCSS[L.kind];
  s+='<g class="blk" data-k="'+key+'" data-i="'+(i-1)+'">'+   // -1 = 입력 블록
     '<rect x="'+X+'" y="'+y+'" width="'+BW+'" height="'+BH+'" rx="9" '+
       'fill="'+col+'" fill-opacity="0.11" stroke="'+col+'" stroke-width="1.4"/>'+
     '<text x="'+(X+14)+'" y="'+(y+26)+'" font-size="13">'+L.n+'</text>'+
     // 입력 블록은 파라미터가 없다 → 그 자리에 자기 모양을 적는다
     '<text x="'+(X+BW-14)+'" y="'+(y+26)+'" text-anchor="end" font-size="11.5" '+
       'fill="'+(L.p!==undefined?'#5B6478':col)+'">'+(L.p!==undefined?L.p:L.shape)+'</text>'+
     '</g>';
  if(i<all.length-1){
    const y1=y+BH, y2=y+BH+GAP, cx=X+BW/2;
    s+='<line x1="'+cx+'" y1="'+y1+'" x2="'+cx+'" y2="'+(y2-7)+'" stroke="#8A93A6" stroke-width="1.4"/>'+
       '<path d="M'+(cx-4)+','+(y2-7)+' L'+cx+','+y2+' L'+(cx+4)+','+(y2-7)+'" fill="#8A93A6"/>'+
       '<text x="'+(X+BW+12)+'" y="'+(y1+GAP/2+4)+'" font-size="12" '+
         'fill="'+KINDCSS[all[i+1].kind]+'">'+all[i+1].shape+'</text>';
  }
});
s+='</svg>';
```

> **함정 (실제로 밟았음).** 화살표 라벨은 *다음* 층의 출력이다. 그래서 입력 블록의 모양은
> 어떤 화살표에도 안 나온다 — 위처럼 블록 안에 직접 적지 않으면 **입력 모양이 그림에서 통째로 빠진다.**

> **함정.** 블록 인덱스는 입력이 0번이라 `layers` 보다 1 크다. `data-i="i-1"` 로 맞추고
> 하이라이트할 때 `blocks[i+1]` 로 되돌린다. 클릭 시 `i<0`(입력)이면 무시한다.

`.arch{overflow-x:auto}` 로 감싼다 — 좁은 화면에서 페이지 전체가 가로로 밀리면 안 된다.

---

## 4. A-5 · 양방향 결합 (이 스킬의 핵심)

시각화와 코드가 **서로** 켜져야 한다. 한 방향만 되면 반쪽이다.

```js
/* 시각화 → 코드 */
function selectLayer(key,i){
  const A=ARCH[key];
  highlightViz(key+':'+i,false);
  const line=A.layers[i].line;
  const card=document.querySelector('.codecard[data-note-target="'+A.card+'"]');
  const target=[...card.querySelectorAll('.ln')].find(
    ln=>ln.querySelector('.no') && ln.querySelector('.no').textContent.trim()===String(line));
  if(target){
    card.querySelectorAll('.ln').forEach(x=>x.classList.remove('on'));
    target.classList.add('on');
    const note=document.getElementById(A.card);
    if(note && target.dataset.n){ note.classList.remove('idle');
      note.innerHTML='<span class="who">'+line+'번째 줄</span>'+target.dataset.n; }
    target.scrollIntoView({block:'center',behavior:'smooth'});
  }
}

/* 코드 → 시각화 : 공통 줄 클릭 핸들러 끝에 3줄만 덧붙인다 */
if(ln.dataset.viz) highlightViz(ln.dataset.viz,false);
```

코드 줄에는 `data-viz="cnn:5"` 를 단다(모델키:층인덱스).

```html
<div class="ln" data-viz="cnn:5" data-n="드디어 편다. 3×3×32 = 288짜리 벡터가 된다.">
```

---

## 5. R9 · 변환 체인 스테퍼

전처리 한 셀이 여러 변환을 몰아서 하는 경우(`reshape` + `/255` + `to_categorical`),
**한 단계씩** 끊어 보여준다. 단계 배열을 만들고 인덱스만 렌더한다.

```js
const steps=[
  {v:()=>grid(28),                        c:'<b>0단계 · 원본</b> — (60000, 28, 28) 값 0~255'},
  {v:()=>grid(28)+arrow+strip(784),       c:'<b>1단계 · reshape(-1, 784)</b> — 여기서 위아래 이웃 관계가 사라진다'},
  {v:()=>strip(784)+arrow+rangeBox(),     c:'<b>2단계 · /255.0</b> — 모양은 그대로, 값 범위만 0~1로'},
  {v:()=>oneHot(3),                       c:'<b>3단계 · to_categorical</b> — (60000,) → (60000, 10)'}
];
let sp=0,timer=null;
function render(){ view.innerHTML=steps[sp].v(); cap.innerHTML=steps[sp].c;
  dots.querySelectorAll('.sd').forEach((d,i)=>d.classList.toggle('on',i<=sp)); }
```

▶ 재생 / 한 단계 / 처음으로 3버튼 + 진행 점(`.sd`)을 둔다.

> **설계 원칙 — 없는 데이터를 지어내지 말 것.**
> 실제 픽셀값은 노트북 출력에 없다. 그래서 격자는 **값이 아니라 인덱스 구조**만 보여준다.
> 시그니처 위젯도 같은 이유로 `(row, col) → row*28+col` 매핑만 다룬다:
> 가르칠 내용은 다 담기면서 날조 위험이 0이다.

> **레이아웃 함정.** 784 벡터를 28칸씩 끊으면 왼쪽 28×28 격자와 똑같이 보여서
> "같은 행은 벡터에서도 붙어 있다"는 요점이 사라진다. **56칸처럼 격자와 다른 폭으로 끊는다.**
> ```css
> #strip{display:grid;grid-template-columns:repeat(56,7px);gap:1px;width:max-content}
> ```

---

## 6. R8 · 데이터 흐름 파이프라인

노트북 전체를 한 줄로 요약. 스테이지마다 **그 시점의 실제 모양**을 붙인다.

```html
<div class="stage" data-s="1">
  <div class="sn">CELL 4</div><div class="st">평탄화 · 정규화</div>
  <span class="shp fe">(60000, 784)</span>
</div>
```

클릭하면 `입력 | 처리 | 출력` 설명을 아래 패널에 띄운다. 설명 배열은 스테이지 인덱스로 접근.
로드 직후 첫 스테이지를 `.click()` 해서 빈 화면으로 시작하지 않게 한다.

---

## 7. R10 · 호출 관계 그래프

노트북에 **직접 정의한 함수가 3개 미만이면 만들지 않는다.**
교재형 노트북은 대개 함수를 안 만들고 위에서 아래로 흐르므로 해당 없음이 흔하다.
생략했다면 푸터에 한 줄로 밝힌다 — 빠뜨린 게 아니라 없어서 안 만든 것임을 알려야 한다.

---

## 8. 관측값 하드코딩 체크리스트

페이지를 다 쓴 뒤 반드시 대조한다.

- [ ] 페이지의 모든 shape·파라미터·정확도가 노트북 출력에 실제로 있는 문자열인가
- [ ] `model.summary()` 표의 `Total params` 와 층별 합이 맞는가
- [ ] 관측값이 아닌 것에 `추정` 배지가 붙었는가
- [ ] 학습 로그를 옮길 때 **과학표기**를 놓치지 않았는가
      (`- loss: 9.6555e-04` 를 `9.6555` 로 읽으면 있지도 않은 손실 폭증을 그리게 된다.
       정규식은 `- loss: ([\d.]+(?:e-?\d+)?)` 처럼 지수부까지 잡아야 한다)
- [ ] `evaluate()` 결과 줄을 에폭 기록으로 착각하지 않았는가
      (로그 끝의 `313/313 … accuracy:` 는 에폭이 아니라 평가다)
- [ ] **summary를 찍은 모델과 실제로 학습된 모델이 같은 모델인가**
      (다르면 파라미터 수와 정확도를 나란히 놓아선 안 된다 — 실제로 이 함정이 있었다)

---

## 9. 검증 (정적 검사로는 증명 안 되는 것)

`scripts/verify_page.js` 로 실제 브라우저에서 확인한다.

```bash
python -m http.server 8899 --bind 127.0.0.1   # file:// 은 확장/보안 제약이 있어 http 로 연다
node scripts/verify_page.js http://127.0.0.1:8899/<파일>.html
```

통과 기준: `consoleErrors` 0 · `horizontalOverflow` false ·
`viz2code`/`code2viz` 양쪽 `rowOn`·`svgBlockOn` true · 관측값 문자열 전부 present.
