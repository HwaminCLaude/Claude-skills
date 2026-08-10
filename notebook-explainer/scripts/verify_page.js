/*
verify_page.js — 생성한 해설 HTML을 실제 브라우저에서 검증한다.

정적 검사로는 증명할 수 없는 것을 확인한다:
  · 코드 줄을 클릭하면 설명 패널이 정말 채워지는가
  · 시각화 ↔ 코드 양방향 하이라이트가 실제로 동작하는가
  · 콘솔 에러 0 / 가로 스크롤 없음

사용:
  python -m http.server 8899 --bind 127.0.0.1     # file:// 은 브라우저 제약이 있어 http 로 연다
  node verify_page.js http://127.0.0.1:8899/<파일>.html
  node verify_page.js <url> --shot out.png --expect "269,322|(None, 288)|98.99"

--expect 는 | 로 구분한 문자열 목록. 하드코딩했다고 주장하는 관측값이
페이지에 실제로 들어 있는지 대조한다.

사전 준비 (한 번만):
  npm i -g playwright && npx playwright install chromium-headless-shell
*/

/* playwright 를 어디에 설치했든 찾아낸다.
   스킬 폴더 안에 node_modules 를 두는 방식은 깨지기 쉬워서 쓰지 않는다. */
function loadPlaywright() {
  const path = require('path');
  const tries = [];
  try { return require('playwright'); } catch (e) { tries.push('local: ' + e.code); }
  try {
    const root = require('child_process').execSync('npm root -g', { encoding: 'utf8' }).trim();
    return require(path.join(root, 'playwright'));
  } catch (e) { tries.push('global: ' + (e.code || e.message)); }
  if (process.env.PLAYWRIGHT_PATH) {
    try { return require(process.env.PLAYWRIGHT_PATH); }
    catch (e) { tries.push('PLAYWRIGHT_PATH: ' + e.code); }
  }
  console.error(
    'playwright 를 찾지 못했습니다 (' + tries.join(' / ') + ')\n' +
    '설치:  npm i -g playwright && npx playwright install chromium-headless-shell\n' +
    '또는:  PLAYWRIGHT_PATH=<playwright 경로> 환경변수 지정');
  process.exit(2);
}
const { chromium } = loadPlaywright();

const args = process.argv.slice(2);
const url = args.find(a => !a.startsWith('--'));
const flag = n => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };
const shot = flag('--shot');
const expect = (flag('--expect') || '').split('|').map(s => s.trim()).filter(Boolean);

if (!url) { console.error('사용: node verify_page.js <url> [--shot out.png] [--expect "a|b"]'); process.exit(2); }

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));

  await page.goto(url, { waitUntil: 'networkidle' });
  const out = {};

  out.structure = await page.evaluate(() => ({
    codecards: document.querySelectorAll('.codecard').length,
    clickableLines: document.querySelectorAll('.ln[data-n]').length,
    widgets: document.querySelectorAll('.widget').length,
    sections: document.querySelectorAll('section.sec').length,
    svgDiagrams: document.querySelectorAll('.arch svg').length,
    tracerRows: document.querySelectorAll('.trow[data-i]').length,
    details: document.querySelectorAll('details').length,
    scripts: document.querySelectorAll('script').length,
    externalResources: [...document.querySelectorAll('[src],[href]')]
      .map(e => e.getAttribute('src') || e.getAttribute('href'))
      .filter(u => u && /^https?:/.test(u)),
    horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
  }));

  // ── 코드 줄 클릭 → 설명 패널 ──
  const line = await page.$('.codecard[data-note-target] .ln[data-n]');
  if (line) {
    const noteId = await line.evaluate(el => el.closest('.codecard').dataset.noteTarget);
    const before = await page.textContent('#' + noteId);
    await line.click();
    const after = await page.textContent('#' + noteId);
    out.lineClick = {
      filled: before !== after,
      idleCleared: !(await page.getAttribute('#' + noteId, 'class') || '').includes('idle'),
    };
  } else out.lineClick = 'code card 없음';

  // ── 양방향 결합 (시각화가 있을 때만) ──
  const reset = () => page.evaluate(() =>
    document.querySelectorAll('.ln.on,.blk.on,.trow.on').forEach(e => e.classList.remove('on')));

  const row = await page.$('.trow[data-i]');
  if (row) {
    await reset(); await row.click();
    out.viz2code = await page.evaluate(() => ({
      rowHighlighted: !!document.querySelector('.trow[data-i].on'),
      svgBlockHighlighted: !!document.querySelector('.arch .blk.on'),
      codeLineHighlighted: !!document.querySelector('.ln.on'),
    }));
  }
  const vizLine = await page.$('.ln[data-viz]');
  if (vizLine) {
    await reset(); await vizLine.click();
    out.code2viz = await page.evaluate(() => ({
      rowHighlighted: !!document.querySelector('.trow[data-i].on'),
      svgBlockHighlighted: !!document.querySelector('.arch .blk.on'),
    }));
  }
  // 추적기는 있는데 data-viz 를 단 코드 줄이 하나도 없다 = 양방향 결합의 절반이 빠진 것.
  // 페이지는 멀쩡해 보이고 표도 동작하므로 눈으로는 못 잡는다. 반드시 FAIL로 잡는다.
  if (row && !vizLine) out.bidirectionalBroken =
    'FAIL: .trow[data-i] 는 있는데 .ln[data-viz] 가 0개 — 코드→시각화 방향이 끊겨 있다. ' +
    '각 층을 만든 코드 줄에 data-viz="모델키:층인덱스" 를 달 것.';
  if (!row && !vizLine) out.bidirectional = '시각화 위젯 없음 (비-ML 코드면 정상)';

  // ── 하드코딩한 관측값이 실제로 들어 있는가 ──
  if (expect.length) {
    const body = await page.textContent('body');
    out.expectedValues = Object.fromEntries(expect.map(v => [v, body.includes(v)]));
    out.missingValues = expect.filter(v => !body.includes(v));
  }

  out.consoleErrors = errors;

  // 양방향 결합은 이 스킬의 핵심 기능이다. 시각화가 있는 페이지라면
  // 두 방향 모두 실제로 동작해야 통과다.
  const bidiOK =
    !out.bidirectionalBroken &&
    (!out.viz2code || (out.viz2code.rowHighlighted && out.viz2code.codeLineHighlighted)) &&
    (!out.code2viz || out.code2viz.rowHighlighted || out.code2viz.svgBlockHighlighted);

  out.verdict =
    errors.length === 0 &&
    !out.structure.horizontalOverflow &&
    (out.lineClick === 'code card 없음' || out.lineClick.filled) &&
    bidiOK &&
    (!out.missingValues || out.missingValues.length === 0)
      ? 'PASS' : 'FAIL';
  if (out.verdict === 'FAIL') {
    out.failedChecks = [
      errors.length && 'consoleErrors',
      out.structure.horizontalOverflow && 'horizontalOverflow',
      out.lineClick !== 'code card 없음' && !out.lineClick.filled && 'lineClick',
      !bidiOK && 'bidirectional',
      out.missingValues && out.missingValues.length && 'missingValues',
    ].filter(Boolean);
  }

  if (shot) { await page.screenshot({ path: shot, fullPage: true }); out.screenshot = shot; }
  console.log(JSON.stringify(out, null, 1));
  await browser.close();
  process.exit(out.verdict === 'PASS' ? 0 : 1);
})();
