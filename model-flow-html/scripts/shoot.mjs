#!/usr/bin/env node
// shoot.mjs: make_tests.mjs 가 만든 <outdir>/test.html 을 헤드리스 크롬(headless Chrome)으로 찍는다.
//
// usage: node shoot.mjs <outdir> [--steps all|0,4,5|lora,layers] [--sizes 1600x900,520x900] [--themes light,dark] [--conds k,..]
//                       [--sim auto|off] [--sheet] [--perf all|0,8|layers] [--budget 5000] [--jobs 3]
//
//   - test.html?info=1 을 --dump-dom 으로 읽어 단계 수, 조건 수, 단계별 훑기(sweep) 시간, 단계 key 를 안다.
//     --steps, --perf 에는 번호(0-3 처럼 범위도 됨) 대신 단계 key(__mf.keys)를 써도 된다. 빠진 단계가 있어도 key 는 그대로다.
//   - 단계 × 크기 × 테마 × 조건마다 <outdir>/shots/<theme>-<cond>-<w>x<h>-s<i>.png 를 찍는다 (--sim off 로 찍은 훑기 단계는 -s<i>-simoff.png).
//     --conds 를 안 주면 페이지 기본 조건으로 찍고 이름의 <cond> 자리에 def 를 쓴다 (주면 c0, c1 …).
//     훑기가 있는 단계는 sim=1 을 붙여 훑기가 끝난 장면을 찍는다 (--sim off 면 첫 장면).
//   - 찍을 때 DOM 도 함께 받아 #err 배너가 보이는지, 제목에 MF-ERROR 가 있는지 본다.
//   - --sheet: 묶음(테마·조건·크기)마다 단계 순서대로 3×3 모음(contact sheet)을 ffmpeg 로 <outdir>/sheets/ 에 만든다.
//   - --perf: 고른 단계를 크기마다 한 번씩 재어 PERF 줄을 보여 준다 (첫 테마, 첫 조건, 가상 시간 없이).
//   - --budget: 크롬의 --virtual-time-budget (ms). --jobs: 동시에 띄울 크롬 수 (perf 는 늘 하나씩).
//   - 브라우저는 CHROME 환경 변수 → Chrome → Edge 순서로 찾는다.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const USAGE = `usage: node shoot.mjs <outdir> [--steps all|0,4,5|lora,layers] [--sizes 1600x900,520x900] [--themes light,dark] [--conds k,..]
                      [--sim auto|off] [--sheet] [--perf all|0,8|layers] [--budget 5000] [--jobs 3]`;
const die = (msg, code = 2) => { console.error(msg); process.exit(code); };

/* ---------------------------------------------------------------- 인자 */
const opt = { steps: 'all', sizes: '1600x900,520x900', themes: 'light,dark', conds: '', sim: 'auto', sheet: false, perf: '', budget: '5000', jobs: '3' };
const pos = [], argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i++) {
  let a = argv[i], v = null;
  if (a === '-h' || a === '--help') { console.log(USAGE); process.exit(0); }
  if (!a.startsWith('--')) { pos.push(a); continue; }
  const eq = a.indexOf('=');
  if (eq > 0) { v = a.slice(eq + 1); a = a.slice(0, eq); }
  const key = a.slice(2);
  if (!(key in opt)) die('모르는 옵션: ' + a + '\n' + USAGE);
  if (key === 'sheet') { opt.sheet = true; continue; }
  if (v === null) { v = argv[++i]; if (v === undefined) die(a + ' 뒤에 값이 필요합니다'); }
  opt[key] = v;
}
if (pos.length !== 1) die(USAGE);
const outdir = path.resolve(pos[0]), testHtml = path.join(outdir, 'test.html');
if (!fs.existsSync(testHtml)) die('test.html 이 없습니다: ' + testHtml + '\n먼저 node make_tests.mjs <page.html> ' + pos[0] + ' 를 돌립니다');
const list = (s) => String(s).split(',').map((x) => x.trim()).filter(Boolean);
const sizes = list(opt.sizes).map((s) => { const m = /^(\d+)x(\d+)$/i.exec(s); if (!m) die('크기는 1600x900 처럼 씁니다: ' + s); return [+m[1], +m[2]]; });
const themes = list(opt.themes);
for (const t of themes) if (t !== 'light' && t !== 'dark') die('테마는 light 나 dark 입니다: ' + t);
if (opt.sim !== 'auto' && opt.sim !== 'off') die('--sim 은 auto 나 off 입니다');
const budget = Math.max(0, parseInt(opt.budget, 10) || 0), jobs = Math.max(1, parseInt(opt.jobs, 10) || 1);
if (!sizes.length || !themes.length) die(USAGE);
function idx(s, n, what, keys = []) {
  if (s === 'all') return [...Array(n).keys()];
  const out = [];
  for (const p of list(s)) {
    const m = /^(\d+)(?:-(\d+))?$/.exec(p);
    if (!m) {
      const k = keys.indexOf(p);   /* 단계 key 로 준 경우 */
      if (k < 0) die(what + ' 값을 읽지 못했습니다: ' + p + (keys.length ? ' (단계 key: ' + keys.join(', ') + ')' : ''));
      if (!out.includes(k)) out.push(k);
      continue;
    }
    const a = +m[1], b = m[2] === undefined ? a : +m[2];
    for (let k = Math.min(a, b); k <= Math.max(a, b); k++) {
      if (k >= n) die(what + ' ' + k + ' 은 없습니다 (0..' + (n - 1) + ')');
      if (!out.includes(k)) out.push(k);
    }
  }
  return out;
}

/* ---------------------------------------------------------------- 브라우저 찾기 */
function findChrome() {
  if (process.env.CHROME) {
    if (fs.existsSync(process.env.CHROME)) return process.env.CHROME;
    die('CHROME 환경 변수의 파일이 없습니다: ' + process.env.CHROME);
  }
  const c = [];
  if (process.platform === 'win32') {
    const roots = [process.env.ProgramFiles || 'C:\\Program Files', process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)', process.env.LOCALAPPDATA].filter(Boolean);
    for (const exe of ['Google\\Chrome\\Application\\chrome.exe', 'Microsoft\\Edge\\Application\\msedge.exe']) for (const r of roots) c.push(path.join(r, exe));
  } else if (process.platform === 'darwin') {
    for (const app of ['Google Chrome.app/Contents/MacOS/Google Chrome', 'Chromium.app/Contents/MacOS/Chromium', 'Microsoft Edge.app/Contents/MacOS/Microsoft Edge']) {
      c.push(path.join('/Applications', app), path.join(os.homedir(), 'Applications', app));
    }
  } else {
    for (const name of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'microsoft-edge']) {
      for (const dir of (process.env.PATH || '').split(path.delimiter)) if (dir) c.push(path.join(dir, name));
    }
  }
  const hit = c.find((p) => { try { return fs.statSync(p).isFile(); } catch { return false; } });
  if (!hit) die('Chrome 이나 Edge 를 찾지 못했습니다. CHROME 환경 변수에 실행 파일 경로를 넣습니다.');
  return hit;
}
const CHROME = findChrome();

/* 크롬 하나를 띄운다. 프로필은 매번 새로 만들어 이미 떠 있는 브라우저와 섞이지 않게 한다 */
function chrome(flags, url, timeoutMs) {
  return new Promise((resolve) => {
    const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'mf-shoot-'));
    const args = ['--headless=new', '--disable-gpu', '--hide-scrollbars', ...flags,
      '--no-first-run', '--no-default-browser-check', '--user-data-dir=' + prof, url];
    const t0 = Date.now(), p = spawn(CHROME, args, { windowsHide: true });
    let out = '', err = '', done = false;
    p.stdout.setEncoding('utf8'); p.stderr.setEncoding('utf8');
    p.stdout.on('data', (d) => { out += d; });
    p.stderr.on('data', (d) => { err += d; });
    const timer = setTimeout(() => { err += '\n[시간 초과]'; p.kill(); }, timeoutMs);
    const end = (code) => {
      if (done) return; done = true; clearTimeout(timer);
      try { fs.rmSync(prof, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch { /* 지우지 못한 임시 프로필은 남겨 둔다 */ }
      resolve({ code, out, err, sec: (Date.now() - t0) / 1000 });
    };
    p.on('close', end);
    p.on('error', (e) => { err += String(e); end(-1); });
  });
}
const base = pathToFileURL(testHtml).href;
const urlFor = (q, i) => base + '?' + new URLSearchParams(q).toString() + '#s' + i;
const timeout = budget + 60000;

/* 받은 DOM 에서 제목, MF-ERROR, 보이는 #err 를 꺼낸다. 시험 운전 스크립트의 글자와 헷갈리지 않게 <title> 안만 본다 */
const unesc = (s) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
function inspect(dom) {
  const title = [...dom.matchAll(/<title>([^<]*)<\/title>/gi)].map((m) => unesc(m[1])).join('\n');
  const mfErr = (/^MF-ERROR.*$/m.exec(title) || [])[0] || '';
  let err = '';
  const m = /<([a-z][a-z0-9]*)\b([^>]*?\bid\s*=\s*["']?err(?=["'\s>])[^>]*)>([\s\S]*?)<\/\1>/i.exec(dom);
  if (m && !/\shidden(?=[\s=>]|$)/i.test(' ' + m[2])) err = unesc(m[3].replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()) || '(빈 #err 가 보입니다)';
  return { title, mfErr, err };
}
function pngSize(f) {
  try {
    const b = Buffer.alloc(24), fd = fs.openSync(f, 'r');
    fs.readSync(fd, b, 0, 24, 0); fs.closeSync(fd);
    return b.toString('latin1', 1, 4) === 'PNG' ? [b.readUInt32BE(16), b.readUInt32BE(20)] : null;
  } catch { return null; }
}
async function pool(items, n, fn) {
  let k = 0;
  const worker = async () => { while (k < items.length) { const it = items[k++]; await fn(it); } };
  await Promise.all(Array.from({ length: Math.min(n, items.length) }, worker));
}

/* ---------------------------------------------------------------- 1) 단계·조건·훑기 읽기 */
const shotsDir = path.join(outdir, 'shots');
fs.mkdirSync(shotsDir, { recursive: true });
const [w0, h0] = sizes[0];
const info = await chrome(['--window-size=' + w0 + ',' + h0, '--virtual-time-budget=' + budget, '--dump-dom'], urlFor({ info: 1, theme: themes[0] }, 0), timeout);
fs.writeFileSync(path.join(shotsDir, 'info-dom.html'), info.out);
const ii = inspect(info.out), im = /MF steps=(\d+) conds=(\d+) sweep=(\[[^\]]*\])(?: keys=(\[[^\]]*\]))?/.exec(ii.title);
if (!im) {
  console.log('test.html?info=1 에서 단계 정보를 읽지 못했습니다 (크롬 종료 코드 ' + info.code + ')');
  if (ii.mfErr) console.log('  ' + ii.mfErr);
  if (ii.err) console.log('  #err: ' + ii.err);
  if (!info.out) console.log('  ' + info.err.split('\n').filter((l) => l.trim()).slice(-3).join('\n  '));
  process.exit(1);
}
const STEPS = +im[1], CONDS = +im[2], SWEEP = JSON.parse(im[3]), KEYS = im[4] ? JSON.parse(im[4]).map(String) : [];
const steps = idx(opt.steps, STEPS, '단계', KEYS);
const conds = opt.conds ? idx(opt.conds, CONDS, '조건') : [null];
const perfSteps = opt.perf ? idx(opt.perf, STEPS, 'perf 단계', KEYS) : [];
const swept = steps.filter((i) => SWEEP[i] > 0);
console.log('페이지: 단계 ' + STEPS + '개, 조건 ' + CONDS + '개, 훑기 ' + (SWEEP.some((s) => s > 0) ? SWEEP.map((s, i) => s > 0 ? 's' + i + ' ' + s + '초' : '').filter(Boolean).join(', ') : '없음'));
if (KEYS.length) console.log('단계 key: ' + KEYS.map((k, i) => 's' + i + ' ' + k).join(' · '));
console.log('브라우저: ' + CHROME);
const problems = [];
if (ii.err) problems.push('info: #err 가 보입니다: ' + ii.err);
if (ii.mfErr) problems.push('info: ' + ii.mfErr);

/* ---------------------------------------------------------------- 2) 찍기 */
const shots = [];
for (const theme of themes) for (const cond of conds) for (const [w, h] of sizes) for (const i of steps) {
  const tag = theme + '-' + (cond === null ? 'def' : 'c' + cond) + '-' + w + 'x' + h;
  const q = { theme };
  if (cond !== null) q.cond = cond;
  const sim = opt.sim === 'auto' && SWEEP[i] > 0;
  if (sim) q.sim = 1;
  const sfx = opt.sim === 'off' && SWEEP[i] > 0 ? '-simoff' : '';   /* 훑기 첫 장면은 끝 장면 그림을 덮어쓰지 않게 이름을 나눈다 */
  shots.push({ tag, i, w, h, sim, file: path.join(shotsDir, tag + '-s' + i + sfx + '.png'), url: urlFor(q, i) });
}
console.log('찍기: ' + shots.length + '장 (단계 ' + steps.length + ' × 크기 ' + sizes.length + ' × 테마 ' + themes.length + ' × 조건 ' + conds.length + ', 동시 ' + jobs + ')');
const t0 = Date.now();
await pool(shots, jobs, async (s) => {
  try { fs.rmSync(s.file, { force: true }); } catch { /* 지난 파일이 잠겨 있으면 덮어쓰기에 맡긴다 */ }
  const r = await chrome(['--window-size=' + s.w + ',' + s.h, '--virtual-time-budget=' + budget, '--screenshot=' + s.file, '--dump-dom'], s.url, timeout);
  const size = pngSize(s.file), dom = inspect(r.out), name = path.basename(s.file);
  s.ok = !!size;
  if (!size) problems.push(name + ': 그림이 만들어지지 않았습니다 (크롬 종료 코드 ' + r.code + ') ' + r.err.split('\n').filter((l) => l.trim()).slice(-1)[0]);
  else if (size[0] !== s.w || size[1] !== s.h) problems.push(name + ': 크기가 ' + size.join('x') + ' 입니다 (' + s.w + 'x' + s.h + ' 이어야 합니다)');
  if (dom.err) problems.push(name + ': #err 가 보입니다: ' + dom.err);
  if (dom.mfErr) problems.push(name + ': ' + dom.mfErr);
  console.log((s.ok ? 'ok   ' : '실패 ') + name + (s.sim ? '  (sim ' + SWEEP[s.i] + '+3초)' : '') + '  ' + r.sec.toFixed(1) + 's');
});
const okShots = shots.filter((s) => s.ok);

/* ---------------------------------------------------------------- 3) perf: 헤드리스 소프트웨어 래스터 기준 예산 (references/verification.md) */
const PERF_JS = 8, PERF_FRAME = 16;
const perfLines = [];
for (const i of perfSteps) for (const [w, h] of sizes) {
  const q = { perf: 1, theme: themes[0] };
  if (conds[0] !== null) q.cond = conds[0];
  /* perf 는 가상 시간 없이 잰다: 가상 시간이 멈춘 콜백에서는 performance.now() 와 Date.now() 가 멈춰 0 이 나온다 */
  const r = await chrome(['--window-size=' + w + ',' + h, '--dump-dom'], urlFor(q, i), timeout);
  const d = inspect(r.out), m = /PERF ([\d.]+)ms\/frame boxes (\d+) lines (\d+) texts (\d+) fields (\d+)(?: raster ([\d.]+)ms\/frame)?/.exec(d.title);
  if (d.err) problems.push('perf s' + i + ' ' + w + 'x' + h + ': #err 가 보입니다: ' + d.err);
  if (!m) { problems.push('perf s' + i + ' ' + w + 'x' + h + ': PERF 줄을 읽지 못했습니다 ' + (d.mfErr || '')); continue; }
  const over = +m[1] > PERF_JS || (m[6] && +m[6] > PERF_FRAME);
  perfLines.push('s' + String(i).padEnd(3) + (w + 'x' + h).padEnd(10) + ' JS ' + (m[1] + 'ms').padStart(9) + (m[6] ? '  래스터 포함 ' + (m[6] + 'ms').padStart(9) : '')
    + '   boxes ' + m[2] + ' lines ' + m[3] + ' texts ' + m[4] + ' fields ' + m[5] + (over ? '   ← 예산 넘음' : ''));
}

/* ---------------------------------------------------------------- 4) 모음 */
const sheets = [];
let sheetNote = '';
if (opt.sheet) {
  const ff = spawnSync('ffmpeg', ['-version'], { encoding: 'utf8' });
  if (ff.error || ff.status !== 0) sheetNote = 'ffmpeg 가 없어 모음을 건너뜁니다 (PATH 에 ffmpeg 를 두면 만듭니다)';
  else {
    const sheetsDir = path.join(outdir, 'sheets');
    fs.mkdirSync(sheetsDir, { recursive: true });
    const groups = new Map();
    for (const s of okShots) { if (!groups.has(s.tag)) groups.set(s.tag, []); groups.get(s.tag).push(s); }
    for (const [tag, arr] of groups) {
      arr.sort((a, b) => a.i - b.i);
      for (let k = 0; k * 9 < arr.length; k++) {
        const part = arr.slice(k * 9, k * 9 + 9), out = path.join(sheetsDir, tag + '-' + (k + 1) + '.png');
        const lst = path.join(sheetsDir, '.' + tag + '-' + (k + 1) + '.txt');
        /* 파일 이름에 따옴표·공백·한글이 있어도 되게 목록 파일로 넘긴다 */
        fs.writeFileSync(lst, 'ffconcat version 1.0\n' + part.map((s) => "file '" + s.file.replace(/\\/g, '/').replace(/'/g, "'\\''") + "'\n").join(''));
        const th = Math.min(part[0].h, 450);
        const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
          '-vf', 'scale=-2:' + th + ',tile=3x3:padding=8:margin=8:color=0x808080', '-frames:v', '1', out], { encoding: 'utf8' });
        try { fs.rmSync(lst, { force: true }); } catch { /* 목록 파일은 남아도 된다 */ }
        if (r.status === 0 && pngSize(out)) sheets.push(out + '   [' + part.map((s) => 's' + s.i).join(' ') + ']');
        else problems.push('모음 ' + path.basename(out) + ' 실패: ' + (r.stderr || '').trim().split('\n').slice(-1)[0]);
      }
    }
  }
}

/* ---------------------------------------------------------------- 5) 요약 */
console.log('');
console.log('== 요약');
console.log('그림 ' + okShots.length + '/' + shots.length + '장 → ' + shotsDir + '   (' + ((Date.now() - t0) / 1000).toFixed(1) + 's)');
if (swept.length) console.log('훑기 단계 ' + swept.map((i) => 's' + i).join(' ') + (opt.sim === 'auto' ? ' 는 끝 장면(sim=1)으로 찍었습니다' : ' 는 첫 장면으로 찍었습니다 (--sim off)'));
if (opt.sheet) {
  if (sheetNote) console.log(sheetNote);
  for (const s of sheets) console.log('모음 ' + s);
}
if (perfLines.length) {
  console.log('perf (테마 ' + themes[0] + (conds[0] !== null ? ', 조건 c' + conds[0] : '') + ', 30프레임 평균, 예산 JS ' + PERF_JS + 'ms · 래스터 포함 ' + PERF_FRAME + 'ms):');
  for (const l of perfLines) console.log('  ' + l);
}
if (problems.length) { console.log('문제 ' + problems.length + '개:'); for (const p of problems) console.log('  - ' + p); }
else console.log('문제 없음: 모든 그림의 크기가 맞고, #err 와 MF-ERROR 가 보이지 않습니다');
process.exit(problems.length ? 1 : 0);
