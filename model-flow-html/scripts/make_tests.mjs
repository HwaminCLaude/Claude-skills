#!/usr/bin/env node
// make_tests.mjs: 조각(fragment) 페이지 하나로 문법 검사와 시험판(test.html)을 만든다.
//
// usage: node make_tests.mjs <page.html> <outdir> [--ship <standalone.html>]
//
//   1) 인라인 <script> 를 <outdir>/_check.js 로 꺼내 `node --check` 로 문법을 본다. 틀리면 0 이 아닌 코드로 끝낸다.
//   2) <outdir>/test.html 하나를 쓴다. 주소 뒤에 붙인 값으로 움직인다.
//        ?theme=light|dark  조각의 스크립트가 돌기 전에 <html data-theme> 을 정한다
//        &cond=k            __mf.setCond(k)
//        #s<i>              단계 i 를 __mf.go(i, true) + __mf.draw() 로 바로 그리고, document.fonts.ready 뒤에 한 번 더 그린다
//        &sim=1             __mf.sweepSeconds(i) + 3 초만큼 update(0.05, false) 를 돌린 뒤 그린다 (카메라 훑기의 끝 장면)
//        &perf=1            update(0.016) + draw() 30번의 평균을 document.title 에 "PERF <ms>ms/frame boxes .. lines .. texts .. fields .. raster <ms>ms/frame" 로 쓴다
//                           (raster 는 캔버스 1픽셀을 읽어 래스터까지 끝내게 한 한 프레임 값. 예열 10프레임은 재지 않는다)
//        &info=1            document.title 에 "MF steps=<n> conds=<n> sweep=<단계별 sweepSeconds JSON>" 을 쓴다
//                           (손잡이에 keys 가 있으면 뒤에 " keys=<단계 key JSON>" 을 붙인다)
//   3) --ship 을 주면 테마를 강제하지 않는 단독 페이지(doctype/html/head/body 로 감싼 것)도 쓴다.
//
// 페이지와는 window.__mf 손잡이로만 이야기한다. 손잡이가 없거나 그리다 오류가 나면 제목에 "MF-ERROR ..." 를 쓴다.
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

const USAGE = 'usage: node make_tests.mjs <page.html> <outdir> [--ship <standalone.html>]';
const argv = process.argv.slice(2), pos = [];
let ship = null;
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '-h' || a === '--help') { console.log(USAGE); process.exit(0); }
  else if (a === '--ship') { ship = argv[++i]; if (!ship) die('--ship 뒤에 파일 경로가 필요합니다'); }
  else if (a.startsWith('--ship=')) ship = a.slice(7);
  else if (a.startsWith('--')) die('모르는 옵션: ' + a);
  else pos.push(a);
}
if (pos.length !== 2) die(USAGE);
const [src, outdir] = pos.map((p) => path.resolve(p));
function die(msg, code = 2) { console.error(msg); process.exit(code); }

if (!fs.existsSync(src)) die('페이지가 없습니다: ' + src);
const html = fs.readFileSync(src, 'utf8').replace(/^﻿/, '');
fs.mkdirSync(outdir, { recursive: true });

/* ---------------------------------------------------------------- 조각 약속 점검 (경고만 하고 멈추지 않는다) */
const warn = [];
if (!/^\s*<title>[^<]+<\/title>/i.test(html)) warn.push('조각은 <title> 로 시작해야 합니다');
for (const t of ['!doctype', 'html', 'head', 'body']) if (new RegExp('<' + t + '[\\s>]', 'i').test(html)) warn.push('<' + t + '> 가 들어 있습니다 (조각에는 넣지 않습니다)');
for (const m of html.matchAll(/(?:src|href)\s*=\s*["']?((?:https?:)?\/\/[^"'\s>]+)/gi)) {
  if (!/^(?:https?:)?\/\/fonts\.(?:googleapis|gstatic)\.com\//i.test(m[1])) warn.push('바깥 자원: ' + m[1] + ' (Google Fonts 말고는 쓸 수 없습니다)');
}
for (const m of html.matchAll(/@import\s+(?:url\()?\s*["']?((?:https?:)?\/\/[^"')\s]+)/gi)) {
  if (!/^(?:https?:)?\/\/fonts\.(?:googleapis|gstatic)\.com\//i.test(m[1])) warn.push('바깥 자원(@import): ' + m[1]);
}
const nOpen = (html.match(/<mf:count>/g) || []).length, nClose = (html.match(/<\/mf:count>/g) || []).length;
if (nOpen !== 1 || nClose !== 1) warn.push('<mf:count> 블록 표시가 여는 것 ' + nOpen + '개, 닫는 것 ' + nClose + '개입니다 (하나씩이어야 합니다)');
if (!/window\.__mf\s*=/.test(html)) warn.push('window.__mf 손잡이를 찾지 못했습니다');
if (Buffer.byteLength(html) > 16 * 1024 * 1024) warn.push('16MB 를 넘습니다');

/* ---------------------------------------------------------------- 1) 문법 검사 */
const scripts = [];
for (const m of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)) {
  const attrs = m[1];
  if (/\bsrc\s*=/i.test(attrs)) continue;
  const type = (/\btype\s*=\s*["']?([^"'\s>]+)/i.exec(attrs) || [])[1] || '';
  if (type && !/^(module|text\/javascript|application\/javascript)$/i.test(type)) continue;   /* JSON 같은 자료 블록은 건너뛴다 */
  scripts.push({ code: m[2], module: /^module$/i.test(type) });
}
if (!scripts.length) die('인라인 <script> 가 없습니다: ' + src);
/* 브라우저의 보통 스크립트처럼 읽히게 한다: 위쪽 package.json 의 "type":"module" 이나 모듈 추측(detect-module)을 막는다 */
const pkg = path.join(outdir, 'package.json');
if (!fs.existsSync(pkg)) fs.writeFileSync(pkg, '{ "type": "commonjs", "private": true }\n');
let bad = 0;
scripts.forEach((s, k) => {
  const name = (k === 0 ? '_check' : '_check-' + (k + 1)) + (s.module ? '.mjs' : '.js');
  const file = path.join(outdir, name);
  fs.writeFileSync(file, s.code);
  const r = spawnSync(process.execPath, ['--check', file], { encoding: 'utf8' });
  if (r.status === 0) console.log('node --check ' + name + ' OK (' + s.code.length + ' 글자)');
  else { bad++; console.log('node --check ' + name + ' 실패'); process.stdout.write(r.stderr || r.stdout || ''); }
});

/* ---------------------------------------------------------------- 2) test.html */
const NL = '\n';
const BASE = 'body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}';
const head = (extra) => '<!doctype html>' + NL + '<html lang="ko"><head>' + NL
  + '<meta charset="utf-8">' + NL
  + '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">' + NL
  + extra + '<style>' + BASE + '</style>' + NL + '</head><body>' + NL;
const tail = NL + '</body></html>' + NL;

const THEME = '<script>/* 조각의 스크립트보다 먼저 테마를 정한다 */' + NL
  + '(function () { var t = new URLSearchParams(location.search).get("theme");' + NL
  + '  if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t); })();' + NL
  + '</script>' + NL;

const DRIVER = `
<script>
/* 시험 운전: 주소 뒤 값(cond, sim, perf, info)과 #s<i> 로 한 장면을 rAF 없이 바로 그린다 */
(function () {
  'use strict';
  var q = new URLSearchParams(location.search), mf = window.__mf;
  function say(t) { document.title = t; }
  if (!mf) { say('MF-ERROR window.__mf 가 없습니다 (조각의 스크립트가 끝까지 돌지 못했거나 손잡이를 내놓지 않았습니다)'); return; }
  var m = /^#s(\\d+)$/.exec(location.hash), i = m ? +m[1] : 0, c = q.get('cond');
  /* 조건을 먼저 고르고 go(i, true) 로 카메라와 페이드를 한 번에 맞춘다. go 를 다시 부르면 훑기가 처음으로 돌아가므로 sim 도 매번 다시 돌린다 */
  function show() {
    if (c !== null && c !== '') mf.setCond(+c);
    mf.go(i, true);
    if (q.get('sim') === '1') {
      var n = Math.ceil((mf.sweepSeconds(i) + 3) / 0.05);
      for (var j = 0; j < n; j++) mf.update(0.05, false);
    }
    mf.draw();
  }
  /* 헤드리스의 가상 시간(--virtual-time-budget)이 멈춘 콜백에서는 performance.now() 도 멈춘다. 그때 잰 0 은 버린다 */
  function clockAlive() {
    var a = performance.now(), z = 0;
    for (var k = 0; k < 2e5; k++) z += Math.sqrt(k);
    return performance.now() > a || z < 0;
  }
  function perf() {
    if (!clockAlive()) return;   /* 앞선 측정이 있으면 그대로 둔다 */
    for (var w = 0; w < 10; w++) { mf.update(0.016, false); mf.draw(); }   /* JIT 예열: 재지 않는다 */
    var t0 = performance.now();
    for (var j = 0; j < 30; j++) { mf.update(0.016, false); mf.draw(); }
    var ms = (performance.now() - t0) / 30, s = mf.stats();
    /* 크롬은 캔버스 래스터(raster)를 미뤄 두므로 위 값에는 JS 와 그리기 기록만 들어간다.
       캔버스마다 1픽셀을 읽어 래스터까지 끝내게 한 값을 raster 로 덧붙인다 (손잡이 밖이지만 어떤 캔버스든 똑같이 다룬다) */
    var cx = [].slice.call(document.querySelectorAll('canvas')).map(function (el) { try { return el.getContext('2d'); } catch (e) { return null; } }).filter(Boolean);
    var t1 = performance.now();
    for (j = 0; j < 30; j++) {
      mf.update(0.016, false); mf.draw();
      for (var n = 0; n < cx.length; n++) { try { cx[n].getImageData(0, 0, 1, 1); } catch (e) { /* 크기가 0인 캔버스는 건너뛴다 */ } }
    }
    var rs = (performance.now() - t1) / 30;
    say('PERF ' + ms.toFixed(2) + 'ms/frame boxes ' + s.boxes + ' lines ' + s.lines + ' texts ' + s.texts + ' fields ' + s.fields + ' raster ' + rs.toFixed(2) + 'ms/frame');
  }
  function run() {
    try { show(); if (q.get('perf') === '1') perf(); }
    catch (e) { say('MF-ERROR ' + ((e && e.message) || e)); throw e; }
  }
  if (q.get('info') === '1') {
    try {
      var sw = [];
      for (var k = 0; k < mf.steps; k++) sw.push(Math.round(mf.sweepSeconds(k) * 1000) / 1000);
      say('MF steps=' + mf.steps + ' conds=' + mf.conds + ' sweep=' + JSON.stringify(sw) + (Array.isArray(mf.keys) ? ' keys=' + JSON.stringify(mf.keys) : ''));
    } catch (e) { say('MF-ERROR ' + ((e && e.message) || e)); }
  }
  run();
  /* 글꼴이 늦게 오면 글자 폭이 바뀌므로 다 온 뒤에 같은 장면을 한 번 더 그린다 */
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(run);
})();
</script>`;

const test = path.join(outdir, 'test.html');
fs.writeFileSync(test, head(THEME) + html + DRIVER + tail);

/* ---------------------------------------------------------------- 3) 단독 페이지 */
if (ship) {
  ship = path.resolve(ship);
  fs.mkdirSync(path.dirname(ship), { recursive: true });
  /* 조각 앞머리의 <title>, <meta>, <link> 는 <head> 로 옮기고 나머지를 <body> 에 넣는다 */
  const lead = /^\s*(?:(?:<title>[^<]*<\/title>|<meta\b[^>]*>|<link\b[^>]*>)\s*)+/i.exec(html);
  const headExtra = lead ? lead[0].trim() + NL : '';
  fs.writeFileSync(ship, head(headExtra) + (lead ? html.slice(lead[0].length) : html) + tail);
}

const url = pathToFileURL(test).href;
console.log('test.html  ' + test);
console.log('  보기 예: ' + url + '?theme=dark#s0');
console.log('           ' + url + '?theme=light&cond=0&sim=1#s1   (info=1, perf=1 은 제목에 결과를 쓴다)');
if (ship) console.log('ship       ' + ship);
for (const w of warn) console.log('경고: ' + w);
console.log('bytes ' + Buffer.byteLength(html) + ', scripts ' + scripts.length + (bad ? ', 문법 오류 ' + bad : ''));
process.exit(bad ? 1 : 0);
