# Widget Recipes

Proven HTML/CSS/JS patterns for the notebook explainer. Adapt values and copy to the page's own palette variables — do not paste verbatim with mismatched var names.

## Base tokens (adapt colors per subject)

```css
:root{
  --paper:#EEF1F6; --ink:#141B2D; --sub:#5A6478; --card:#FFF; --line:#D8DEE9;
  --wire:#2D4FE0;              /* interaction accent */
  --sem-a:#E2703A; --sem-b:#0E9E8A;  /* two SEMANTIC colors from the subject */
  --code-bg:#161D2E; --code-ink:#DCE3F2; --code-dim:#7C88A3; --r:14px;
}
```
Semantic colors must mean something (CPU vs GPU, train vs test, input vs output) and be introduced in a legend in the hero.

Syntax highlight classes (hand-applied in the HTML, no library):
`.k` keyword #8FA6FF · `.s` string #7FD6C2 · `.c` comment #6B7690 italic · `.nu` number #F0B36A · `.fn` function #E8A0C8

## 1. Clickable code lines → explanation panel

The backbone of the page. Every code card follows this shape:

```html
<div class="codecard has-note" data-note-target="n1">
  <div class="codebar">…<span class="tip">줄 클릭 → 설명</span></div>
  <div class="codelines">
    <div class="ln" data-n="이 줄의 설명. 의도와 결과를 가르칠 것.">
      <span class="no">1</span><pre><span class="k">import</span> numpy <span class="k">as</span> np</pre>
    </div>
    <div class="ln plain"><span class="no">2</span><pre> </pre></div> <!-- non-clickable -->
  </div>
</div>
<div class="note idle" id="n1">💡 코드 줄을 클릭하면 설명이 여기에 표시돼요.</div>
```

```css
.ln{display:flex;cursor:pointer;border-left:3px solid transparent}
.ln:hover{background:rgba(255,255,255,.05)}
.ln.on{background:rgba(45,79,224,.22);border-left-color:var(--wire)}
.ln.plain{cursor:default}
.ln .no{flex:0 0 44px;text-align:right;padding-right:14px;color:var(--code-dim);user-select:none}
.note{background:var(--card);border:1px solid var(--line);border-top:none;
      border-radius:0 0 var(--r) var(--r);padding:16px 20px;min-height:56px}
```

One handler wires every card on the page:

```js
document.querySelectorAll('.codecard[data-note-target]').forEach(card=>{
  const note=document.getElementById(card.dataset.noteTarget);
  card.querySelectorAll('.ln[data-n]').forEach(ln=>{
    ln.addEventListener('click',()=>{
      card.querySelectorAll('.ln').forEach(x=>x.classList.remove('on'));
      ln.classList.add('on'); note.classList.remove('idle');
      note.innerHTML=`<span class="who">${ln.querySelector('.no').textContent}번째 줄</span>${ln.dataset.n}`;
    });
  });
});
```

Gotcha: `data-n` text goes through `innerHTML` — keep raw `<` `>` out of explanations, or escape them.

## 2. Click-to-highlight visualizer (matrix / structure)

Render structure as CSS grids; bracket look via `::before/::after` borders. Clicking an output cell highlights its contributing inputs in the two semantic colors and renders the arithmetic.

```html
<div class="matrix" id="matA" style="grid-template-columns:repeat(3,1fr)"></div>
<span class="op">×</span>
<div class="matrix" id="matB" style="grid-template-columns:repeat(2,1fr)"></div>
<span class="op">=</span>
<div class="matrix" id="matC" style="grid-template-columns:repeat(2,1fr)"></div>
<div class="formula" id="matF">결과 칸을 클릭하면 계산 과정이 여기 나와요</div>
```

```css
.matrix{display:grid;gap:5px;padding:10px 14px;position:relative}
.matrix::before,.matrix::after{content:"";position:absolute;top:0;bottom:0;width:10px;border:2.5px solid var(--ink)}
.matrix::before{left:0;border-right:none;border-radius:6px 0 0 6px}
.matrix::after{right:0;border-left:none;border-radius:0 6px 6px 0}
.m-cell{width:44px;height:44px;display:flex;align-items:center;justify-content:center;
        border-radius:8px;font-family:"JetBrains Mono";background:var(--paper);transition:.15s}
.m-cell.hl-a{background:var(--sem-a);color:#fff}
.m-cell.hl-b{background:var(--sem-b);color:#fff}
```

```js
function fill(el,M){M.forEach((row,i)=>row.forEach((v,j)=>{
  const d=document.createElement('div');d.className='m-cell';d.textContent=v;
  d.dataset.i=i;d.dataset.j=j;el.appendChild(d);}));}
// on click of C cell (i,j): highlight row i of A (.hl-a), col j of B (.hl-b),
// then formula.innerHTML = A[i].map((a,k)=>`${a}·${B[k][j]}`).join(' + ') + ' = ' + C[i][j]
```

Use event delegation on the container (`e.target.closest('.m-cell')`) so it works on mobile taps.

## 3. Step animator (loops / algorithms)

Precompute the full step list, then render index `sp` (steps played). This makes play / single-step / reset trivially consistent.

```js
const steps=[];  // {i,j,k,a,b,acc} per iteration — build with the same loops as the real code
let sp=0, timer=null;
function render(){ /* rebuild grid, apply all steps < sp, highlight current, update readout */ }
playBtn.onclick=function(){
  if(timer){clearInterval(timer);timer=null;this.textContent='▶ 재생';return;}
  if(sp>=steps.length)sp=0; this.textContent='⏸ 정지';
  timer=setInterval(()=>{ sp<steps.length ? (sp++,render())
    : (clearInterval(timer),timer=null,playBtn.textContent='▶ 재생'); },700);
};
```

Readout panel shows loop variables (i/j/k) plus the live expression with values substituted, colored by the semantic palette. Announce completion in the readout ("✅ 12스텝 완료").

## 4. Slider calculator (formula / threshold)

One `<input type=range>` per formula input; on `input`, update value labels, proportional bars (widths normalized to the max), and a verdict box that states the *actual function call* with current values:

```js
v.innerHTML = worth
  ? `gpu_is_worth_it(${cpu}, ${g}, ${t}) → <b>True</b> — GPU가 이득이에요`
  : `…→ <b>False</b> — 전송 비용까지 치면 CPU가 나아요`;
```

Stacked bar trick for composite costs: two `.bar-fill` divs in one track, second at lower opacity, so "compute + transfer" reads as one bar with two parts. Call the update function once on load so the widget never starts empty.

## 5. Path simulator (try/except, branching)

One button per scenario. Clicking shows (a) the exact console output that branch produces in the real notebook, in a `white-space:pre-wrap` monospace box, and (b) a one-line flow trace: `호출 → NotImplementedError 발생 → except NotImplementedError 분기`. Store scenarios in a plain object keyed by `data-g`.

## 6. Parameter sweep (trade-off sliders)

Discrete slider over an array of valid values (`const sizes=[5,10,20,40,100,200]; sizes[+slider.value]`) — avoids invalid intermediate states like a chunk size that doesn't divide evenly. Redraw a strip/tile visualization and 2–3 big-number counters (calls, overhead, "결과 값: 항상 동일 ✓") on every input event.

## Page chrome

- Sticky nav: `position:sticky;top:0;backdrop-filter:blur(8px)`, horizontally scrollable chip row (`overflow-x:auto`, hidden scrollbar), anchor links; give sections `scroll-margin-top:70px`.
- TOC as a bordered grid of rows: cell number | chapter + one-line role.
- Collapsed answers: `<details>` with a dashed warning-colored border and a summary that repeats the original notebook's warning.
- `@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}`
- Mobile ≤640px: shrink cells, tighten grid columns.
