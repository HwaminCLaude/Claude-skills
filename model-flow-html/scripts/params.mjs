#!/usr/bin/env node
// params.mjs: Hugging Face config.json 을 템플릿의 MODEL 형식으로 옮기고, 템플릿의 <mf:count> 블록으로 파라미터를 센다.
//
// usage: node params.mjs --config <config.json | model dir> [--template <page.html>]
//                        [--lora r=16,alpha=32,targets=q,k,v,o,gate,up,down] [--expect total=N,trainable=N]
//                        [--name ...] [--frozen '4비트(NF4)'] [--grid 256] [--override '<json>'] [--json]
//
//   - model_type: llama, mistral, qwen2, gemma, phi3, gpt2 를 안다. 그 밖의 것은 --override 로 넘길 항목을 알려 주고 멈춘다.
//     --override '<json>' 은 어느 계열에서나 MODEL 항목을 덮어쓴다 (bias, names 는 키 단위로 합친다). JSON 파일 경로를 줘도 된다.
//   - 셈은 여기서 하지 않는다. --template (기본: 이 스크립트 옆 ../assets/template.html) 의
//     <mf:count> … </mf:count> 블록을 그대로 불러 countParams(MODEL, LORA) 를 부른다. 그 블록이 유일한 기준이다.
//   - --lora 의 targets 는 논리 키(q,k,v,o,gate,up,down,fc,proj), all(= all-linear), 또는 모듈 이름(q_proj, qkv_proj, c_attn …)을 받는다.
//   - --expect 가 하나라도 어긋나면 종료 코드 1, 입력이 잘못되면 2.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const USAGE = `usage: node params.mjs --config <config.json | model dir> [--template <page.html>]
                      [--lora r=16,alpha=32,targets=q,k,v,o,gate,up,down] [--expect total=N,trainable=N]
                      [--name ...] [--frozen '4비트(NF4)'] [--grid 256] [--override '<json>'] [--json]`;
const die = (msg, code = 2) => { console.error(msg); process.exit(code); };

/* ---------------------------------------------------------------- 인자 */
const opt = { config: null, template: null, lora: null, expect: null, name: null, frozen: null, grid: null, override: null, json: false };
const argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i++) {
  let a = argv[i], v = null;
  if (a === '-h' || a === '--help') { console.log(USAGE); process.exit(0); }
  if (!a.startsWith('--')) die('모르는 인자: ' + a + '\n' + USAGE);
  const eq = a.indexOf('=');
  if (eq > 0) { v = a.slice(eq + 1); a = a.slice(0, eq); }
  const key = a.slice(2);
  if (!(key in opt)) die('모르는 옵션: ' + a + '\n' + USAGE);
  if (key === 'json') { opt.json = true; continue; }
  if (v === null) { v = argv[++i]; if (v === undefined) die(a + ' 뒤에 값이 필요합니다'); }
  opt[key] = v;
}
if (!opt.config) die(USAGE);

/* ---------------------------------------------------------------- config.json 읽기 */
function findConfig(p) {
  const abs = path.resolve(p);
  if (!fs.existsSync(abs)) die('config 를 찾지 못했습니다: ' + abs);
  if (fs.statSync(abs).isFile()) return abs;
  if (fs.existsSync(path.join(abs, 'config.json'))) return path.join(abs, 'config.json');
  /* 허브 캐시의 models--org--name 폴더를 받으면 refs/main 이 가리키는 스냅샷을 쓴다 */
  const snaps = path.join(abs, 'snapshots');
  if (fs.existsSync(snaps)) {
    let hash = null;
    try { hash = fs.readFileSync(path.join(abs, 'refs', 'main'), 'utf8').trim(); } catch { /* refs 가 없으면 아래에서 고른다 */ }
    const cands = hash ? [hash] : fs.readdirSync(snaps);
    for (const h of cands) if (fs.existsSync(path.join(snaps, h, 'config.json'))) return path.join(snaps, h, 'config.json');
  }
  die('폴더에 config.json 이 없습니다: ' + abs);
}
const cfgPath = findConfig(opt.config);
let C;
try { C = JSON.parse(fs.readFileSync(cfgPath, 'utf8').replace(/^﻿/, '')); } catch (e) { die('config.json 을 읽지 못했습니다: ' + e.message); }
const mtype = String(C.model_type || '');

/* ---------------------------------------------------------------- 계열(family)별 규칙: transformers 의 config 클래스와 nn.Linear(bias=) 를 따른다 */
const NAMES = { q: 'q_proj', k: 'k_proj', v: 'v_proj', o: 'o_proj', gate: 'gate_proj', up: 'up_proj', down: 'down_proj', fc: 'fc', proj: 'proj',
  norm1: 'input_layernorm', norm2: 'post_attention_layernorm', normF: 'norm', emb: 'embed_tokens', pos: 'wpe', head: 'lm_head' };
const NOBIAS = { q: false, k: false, v: false, o: false, mlp: false };
const attnBias = (c) => { const b = !!c.attention_bias; return { q: b, k: b, v: b, o: b, mlp: false }; };
const FAM = {
  llama: { tied: false, bias: (c) => ({ ...attnBias(c), mlp: !!c.mlp_bias }) },
  mistral: { tied: false, bias: () => NOBIAS },
  qwen2: { tied: false, bias: () => ({ q: true, k: true, v: true, o: false, mlp: false }) },   /* q,k,v 만 bias=True */
  gemma: { tied: true, headDim: 256, bias: attnBias,                                               /* GemmaConfig 기본 head_dim=256 */
    act: (c) => c.hidden_activation || c.hidden_act || 'gelu_pytorch_tanh' },
  phi3: { tied: false, bias: () => NOBIAS,                                                         /* qkv_proj, gate_up_proj 는 합쳐진 Linear */
    names: { q: 'qkv_proj[q]', k: 'qkv_proj[k]', v: 'qkv_proj[v]', gate: 'gate_up_proj[gate]', up: 'gate_up_proj[up]' },
    fused: { qkv_proj: ['q', 'k', 'v'], gate_up_proj: ['gate', 'up'] } },
  gpt2: { tied: true, gpt2: true, fused: { c_attn: ['q', 'k', 'v'] }, alias: { c_attn: ['q', 'k', 'v'], c_proj: ['o', 'proj'], c_fc: ['fc'] },
    names: { q: 'c_attn[q]', k: 'c_attn[k]', v: 'c_attn[v]', o: 'attn.c_proj', gate: 'gate', up: 'up', down: 'down', fc: 'c_fc', proj: 'mlp.c_proj',
      norm1: 'ln_1', norm2: 'ln_2', normF: 'ln_f', emb: 'wte', pos: 'wpe', head: 'lm_head' } },
};
const ACT = { silu: 'SiLU', swish: 'SiLU', gelu: 'GELU', gelu_python: 'GELU', gelu_new: 'GELU(tanh)', gelu_pytorch_tanh: 'GELU(tanh)',
  gelu_fast: 'GELU(tanh)', gelu_tanh: 'GELU(tanh)', relu: 'ReLU', quick_gelu: 'QuickGELU' };
const actLabel = (a) => ACT[String(a).toLowerCase()] || String(a);
const num = (...xs) => xs.find((x) => x !== undefined && x !== null);

function fromConfig(c, fam) {
  if (fam.gpt2) {
    const h = num(c.n_embd, c.hidden_size), heads = num(c.n_head, c.num_attention_heads);
    return { hidden: h, layers: num(c.n_layer, c.num_hidden_layers), heads, kvHeads: heads, headDim: h / heads,
      ffn: num(c.n_inner, 4 * h), vocab: c.vocab_size, norm: 'ln', mlp: 'plain', act: actLabel(num(c.activation_function, 'gelu_new')),
      pos: 'learned', maxPos: num(c.n_positions, c.max_position_embeddings, 1024),
      bias: { q: true, k: true, v: true, o: true, mlp: true }, tied: num(c.tie_word_embeddings, fam.tied) };
  }
  const h = c.hidden_size, heads = c.num_attention_heads;
  return { hidden: h, layers: c.num_hidden_layers, heads, kvHeads: num(c.num_key_value_heads, heads),
    headDim: num(c.head_dim, fam.headDim, h / heads), ffn: c.intermediate_size, vocab: c.vocab_size,
    norm: 'rms', mlp: 'gated', act: actLabel(fam.act ? fam.act(c) : num(c.hidden_act, 'silu')), pos: 'rope', maxPos: 0,
    bias: fam.bias(c), tied: num(c.tie_word_embeddings, fam.tied) };
}

let ov = {};
if (opt.override) {
  /* 큰따옴표를 지우는 셸(Windows PowerShell 5.1 등)에서는 JSON 을 파일로 넘긴다 */
  const raw = fs.existsSync(opt.override) && fs.statSync(opt.override).isFile() ? fs.readFileSync(opt.override, 'utf8') : opt.override;
  try { ov = JSON.parse(raw.replace(/^﻿/, '')); } catch (e) { die('--override 의 JSON 을 읽지 못했습니다: ' + e.message + '\n받은 글자: ' + raw); }
  if (!ov || typeof ov !== 'object' || Array.isArray(ov)) die('--override 는 {"hidden": 4096, ...} 같은 JSON 객체여야 합니다');
  const KEYS = ['name', 'hidden', 'layers', 'heads', 'kvHeads', 'headDim', 'ffn', 'vocab', 'norm', 'mlp', 'act', 'pos', 'maxPos', 'bias', 'tied', 'names', 'frozen', 'grid', 'expect'];
  const unknown = Object.keys(ov).filter((k) => !KEYS.includes(k));
  if (unknown.length) die('--override 에 모르는 키가 있습니다: ' + unknown.join(', ') + '\n쓸 수 있는 키: ' + KEYS.join(', '));
}
const fam = FAM[mtype];
const notes = [];
let M;
if (fam) M = fromConfig(C, fam);
else {
  /* 모르는 계열: 흔한 HF 숫자 이름만 후보로 읽고, 구조(norm, mlp, act, pos, bias, tied)는 --override 로 받는다 */
  const h = C.hidden_size, heads = C.num_attention_heads;
  M = { hidden: h, layers: C.num_hidden_layers, heads, kvHeads: num(C.num_key_value_heads, heads),
    headDim: num(C.head_dim, h && heads ? h / heads : undefined), ffn: C.intermediate_size, vocab: C.vocab_size, maxPos: 0, tied: C.tie_word_embeddings };
  const need = ['norm', 'mlp', 'act', 'pos', 'bias'].filter((k) => !(k in ov));
  if (M.tied === undefined && !('tied' in ov)) need.push('tied');
  for (const k of ['hidden', 'layers', 'heads', 'kvHeads', 'headDim', 'ffn', 'vocab']) if ((M[k] === undefined || Number.isNaN(M[k])) && !(k in ov)) need.push(k);
  if (need.length) {
    const seen = ['hidden_size', 'num_hidden_layers', 'num_attention_heads', 'num_key_value_heads', 'head_dim', 'intermediate_size', 'vocab_size', 'tie_word_embeddings', 'hidden_act', 'max_position_embeddings']
      .filter((k) => C[k] !== undefined).map((k) => k + '=' + JSON.stringify(C[k])).join(', ');
    die([
      `model_type '${mtype || '(없음)'}' 은 이 스크립트가 아는 계열(${Object.keys(FAM).join(', ')})이 아닙니다.`,
      '셈 블록은 pre-norm decoder-only (norm 2개/층, q,k,v,o + MLP, 마지막 norm 1개) 만 셉니다. qk-norm 이나 층마다 norm 이 더 있는 모델은 그대로 넣으면 틀립니다.',
      '구조가 맞다면 아래 항목을 --override \'<json>\' 으로 넘깁니다:',
      '  ' + need.join(', '),
      '  norm: "rms" | "ln",  mlp: "gated" | "plain",  act: 보일 이름 (예 "SiLU"),  pos: "rope" | "learned" | "none" (learned 면 maxPos 도),',
      '  bias: {"q":false,"k":false,"v":false,"o":false,"mlp":false},  tied: true | false,  names: {...} (선택)',
      'config.json 에서 읽은 후보: ' + (seen || '없음'),
      '예: --override \'{"norm":"rms","mlp":"gated","act":"SiLU","pos":"rope","bias":{"q":false,"k":false,"v":false,"o":false,"mlp":false},"tied":false}\'',
    ].join('\n'));
  }
  notes.push(`model_type '${mtype}' 은 모르는 계열이라 구조를 --override 에서 받았습니다`);
}
for (const [k, v] of Object.entries(ov)) {
  if (k === 'bias' || k === 'names') continue;
  M[k] = v;
}
M.bias = { ...NOBIAS, ...M.bias, ...(ov.bias || {}) };
const names = { ...NAMES, ...((fam && fam.names) || {}), ...(ov.names || {}) };
if (Object.keys(ov).length) notes.push('--override 로 바꾼 항목: ' + Object.keys(ov).join(', '));

/* 검사: 셈 블록에 넣기 전에 값이 말이 되는지 본다 */
const bad = [];
for (const k of ['hidden', 'layers', 'heads', 'kvHeads', 'headDim', 'ffn', 'vocab']) if (!Number.isInteger(M[k]) || M[k] <= 0) bad.push(k + ' = ' + JSON.stringify(M[k]) + ' (양의 정수여야 합니다)');
if (!['rms', 'ln'].includes(M.norm)) bad.push("norm 은 'rms' 나 'ln' 입니다");
if (!['gated', 'plain'].includes(M.mlp)) bad.push("mlp 는 'gated' 나 'plain' 입니다");
if (!['rope', 'learned', 'none'].includes(M.pos)) bad.push("pos 는 'rope', 'learned', 'none' 중 하나입니다");
if (M.pos === 'learned' && !(Number.isInteger(M.maxPos) && M.maxPos > 0)) bad.push('pos 가 learned 이면 maxPos 가 양의 정수여야 합니다');
if (typeof M.tied !== 'boolean') bad.push('tied 는 true 나 false 입니다');
if (bad.length) die('MODEL 값이 이상합니다:\n  ' + bad.join('\n  '));
if (M.pos !== 'learned') M.maxPos = 0;
if (M.heads % M.kvHeads) notes.push(`heads ${M.heads} 가 kvHeads ${M.kvHeads} 로 나누어떨어지지 않습니다`);

/* ---------------------------------------------------------------- 셈 블록 불러오기 */
const here = path.dirname(fileURLToPath(import.meta.url));
const tplPath = path.resolve(opt.template || path.join(here, '..', 'assets', 'template.html'));
if (!fs.existsSync(tplPath)) die('셈 블록을 읽을 템플릿이 없습니다: ' + tplPath + '\n--template <page.html> 로 <mf:count> 블록이 든 페이지를 넘깁니다');
function loadCounter(file) {
  const s = fs.readFileSync(file, 'utf8');
  const open = [...s.matchAll(/\/\*\s*<mf:count>[\s\S]*?\*\//g)], close = [...s.matchAll(/\/\*\s*<\/mf:count>\s*\*\//g)];
  if (open.length !== 1 || close.length !== 1) die(`<mf:count> 블록 표시가 여는 것 ${open.length}개, 닫는 것 ${close.length}개입니다. 하나씩이어야 합니다: ${file}`);
  const a = open[0].index + open[0][0].length, b = close[0].index;
  if (b <= a) die('닫는 표시 </mf:count> 가 여는 표시보다 앞에 있습니다: ' + file);
  let fn = null;
  try { fn = new Function(s.slice(a, b) + '\n;return typeof countParams === "function" ? countParams : null;')(); }
  catch (e) { die('셈 블록을 실행하지 못했습니다: ' + e.message); }
  if (!fn) die('셈 블록에 countParams 함수가 없습니다: ' + file);
  return fn;
}
const countParams = loadCounter(tplPath);

/* ---------------------------------------------------------------- LoRA */
const MLPK = M.mlp === 'gated' ? ['gate', 'up', 'down'] : ['fc', 'proj'];
const LIN = ['q', 'k', 'v', 'o', ...MLPK];
function parseLora(s) {
  if (s === null || /^(none|null|off|false)$/i.test(s.trim())) return null;
  const L = { r: null, alpha: null, targets: [] };
  let key = null;
  for (const part of s.split(',').map((x) => x.trim()).filter(Boolean)) {
    const eq = part.indexOf('=');
    if (eq > 0) {
      key = part.slice(0, eq).trim();
      const v = part.slice(eq + 1).trim();
      if (key === 'targets') { if (v) L.targets.push(v); }
      else if (key === 'r' || key === 'alpha') L[key] = Number(v);
      else die('--lora 에서 모르는 키: ' + key + ' (r, alpha, targets 만 받습니다)');
    } else if (key === 'targets') L.targets.push(part);
    else die('--lora 를 읽지 못했습니다: ' + part + ' (예: r=16,alpha=32,targets=q,k,v,o)');
  }
  if (!Number.isInteger(L.r) || L.r <= 0) die('--lora 의 r 은 양의 정수여야 합니다');
  if (L.alpha === null) { L.alpha = 2 * L.r; notes.push('alpha 를 주지 않아 2r = ' + L.alpha + ' 로 두었습니다'); }
  if (!Number.isFinite(L.alpha)) die('--lora 의 alpha 는 숫자여야 합니다');
  /* 모듈 이름 → 논리 키 */
  const alias = {};
  for (const k of LIN) alias[names[k]] = [k];
  Object.assign(alias, (fam && fam.alias) || {});
  for (const [mod, ks] of Object.entries((fam && fam.fused) || {})) alias[mod] = ks;
  const want = new Set();
  for (const t of L.targets) {
    const ks = /^(all|all-linear)$/i.test(t) ? LIN : LIN.includes(t) ? [t] : alias[t];
    if (!ks) die(`LoRA 대상 '${t}' 을 모릅니다. 쓸 수 있는 것: all, ${LIN.join(', ')}, ${Object.keys(alias).filter((x) => !LIN.includes(x)).join(', ')}`);
    for (const k of ks) { if (!LIN.includes(k)) die(`LoRA 대상 '${t}' → '${k}' 는 이 모델에 없습니다 (mlp ${M.mlp})`); want.add(k); }
  }
  if (!want.size) die('--lora 에 targets 가 없습니다 (예: targets=q,v 또는 targets=all)');
  return { r: L.r, alpha: L.alpha, targets: LIN.filter((k) => want.has(k)) };
}
const LORA = parseLora(opt.lora);

/* ---------------------------------------------------------------- 나머지 항목 */
function deriveName() {
  const segs = cfgPath.split(/[\\/]/);
  const hub = segs.find((s) => s.startsWith('models--'));
  if (hub) { const p = hub.split('--'); return p.length > 2 ? p.slice(2).join('--') : p[1]; }
  if (C._name_or_path) return path.basename(String(C._name_or_path).replace(/[\\/]+$/, ''));
  const dir = path.basename(path.dirname(cfgPath));
  return dir && !/^[0-9a-f]{40}$/i.test(dir) ? dir : mtype;
}
M.name = opt.name || ov.name || deriveName();
M.frozen = opt.frozen !== null ? opt.frozen : (ov.frozen !== undefined ? ov.frozen : '');
if (LORA && !M.frozen) notes.push("--frozen 을 주지 않아 frozen 이 비어 있습니다. 기본 가중치를 어떤 형식으로 두는지 적습니다 (예: --frozen '4비트(NF4)')");
const qd = M.heads * M.headDim, kd = M.kvHeads * M.headDim;
if (opt.grid !== null) {
  M.grid = Number(opt.grid);
  if (!Number.isInteger(M.grid) || M.grid <= 0) die('--grid 는 양의 정수여야 합니다');
  const odd = [M.hidden, qd, kd, M.ffn].filter((d) => d % M.grid);
  if (odd.length) notes.push(`grid ${M.grid} 가 ${odd.join(', ')} 를 나누지 못해 행렬 끝에 덜 찬 칸이 생깁니다`);
  if (M.hidden / M.grid < 8) notes.push(`grid ${M.grid} 이면 ${M.hidden} × ${M.hidden} 판의 한 변이 ${Math.floor(M.hidden / M.grid)}칸뿐입니다 (8~16칸을 권합니다)`);
} else if (ov.grid !== undefined) M.grid = ov.grid;
else {
  /* 모든 차원을 나누면서 hidden × hidden 판의 한 변이 8칸 이상이 되는 가장 큰 2의 거듭제곱(256 이하)을 고른다.
     칸이 행렬 끝에 딱 맞고, 판마다 모눈이 충분히 보인다 (2,048→256, 1,536→128, 896→64, 768→64) */
  let g = 256;
  while (g > 1 && ([M.hidden, qd, kd, M.ffn].some((d) => d % g) || M.hidden / g < 8)) g /= 2;
  M.grid = g;
}
let expect = null;
if (opt.expect) {
  expect = {};
  /* 논문 표기 그대로 total=1,235,814,400 처럼 써도 되게, 세 자리 묶음은 앞 숫자에 이어 붙인다 */
  let lastKey = null;
  for (const part of opt.expect.split(',').map((x) => x.trim()).filter(Boolean)) {
    if (lastKey && /^\d{3}$/.test(part)) { expect[lastKey] = expect[lastKey] * 1000 + Number(part); continue; }
    const m = /^(total|trainable)=([\d_]+)$/.exec(part);
    if (!m) die('--expect 를 읽지 못했습니다: ' + part + ' (예: total=1235814400,trainable=11272192)');
    lastKey = m[1];
    expect[lastKey] = Number(m[2].replace(/_/g, ''));
  }
} else if (ov.expect !== undefined) expect = ov.expect;

/* ---------------------------------------------------------------- 세기 */
const MODEL = {
  name: M.name, hidden: M.hidden, layers: M.layers, heads: M.heads, kvHeads: M.kvHeads, headDim: M.headDim, ffn: M.ffn, vocab: M.vocab,
  norm: M.norm, mlp: M.mlp, act: M.act, pos: M.pos, maxPos: M.maxPos,
  bias: { q: !!M.bias.q, k: !!M.bias.k, v: !!M.bias.v, o: !!M.bias.o, mlp: !!M.bias.mlp },
  tied: M.tied, names, frozen: M.frozen, grid: M.grid,
  expect: expect ? { total: expect.total ?? null, trainable: expect.trainable ?? (LORA ? null : 0) } : null,
};
let COUNTS;
try { COUNTS = countParams(MODEL, LORA); } catch (e) { die('셈 블록이 멈췄습니다: ' + e.message); }
const trainable = COUNTS.lora ? COUNTS.lora.total : 0;
const checks = [];
if (expect) {
  if (expect.total !== undefined) checks.push({ key: 'total', computed: COUNTS.total, expected: expect.total, ok: COUNTS.total === expect.total });
  if (expect.trainable !== undefined) checks.push({ key: 'trainable', computed: trainable, expected: expect.trainable, ok: trainable === expect.trainable });
}
/* 합쳐진 Linear 에 PEFT 로 LoRA 를 붙이면 A 하나를 함께 쓰므로 실제 학습 수가 논리 모듈별 셈과 다르다 */
const fusedNotes = [];
let fusedLess = 0;
if (LORA && fam && fam.fused) {
  for (const [mod, ks] of Object.entries(fam.fused)) {
    const hit = ks.filter((k) => LORA.targets.includes(k));
    if (!hit.length) continue;
    if (hit.length < ks.length) { fusedNotes.push(`${mod} 는 ${ks.join(',')} 를 합친 Linear 라 PEFT 로는 ${hit.join(',')} 만 따로 고를 수 없습니다`); continue; }
    const logical = ks.reduce((s, k) => s + COUNTS.lora.perModule[k], 0);
    const fused = LORA.r * (COUNTS.shapes[ks[0]][0] + ks.reduce((s, k) => s + COUNTS.shapes[k][1], 0));
    fusedLess += (logical - fused) * M.layers;
    fusedNotes.push(`${mod}: 여기 셈은 ${ks.join(',')} 마다 A,B 를 따로 둬 층마다 ${fmt(logical)}개, PEFT 가 합친 ${mod} 하나에 붙이면 A 를 함께 써서 층마다 ${fmt(fused)}개`);
  }
  if (fusedLess) fusedNotes.push(`PEFT 가 합친 모듈에 붙였을 때의 trainable 은 ${fmt(trainable - fusedLess)} 입니다 (페이지는 논리 모듈별 셈 ${fmt(trainable)} 을 씁니다)`);
}
function fmt(n) { return Number(n).toLocaleString('en-US'); }

/* ---------------------------------------------------------------- 붙여 넣을 블록 (템플릿의 항목 순서) */
const lit = (v) => (v === null || v === undefined ? 'null' : typeof v === 'string' ? "'" + v.replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'"
  : Array.isArray(v) ? '[' + v.map(lit).join(', ') + ']' : typeof v === 'object' ? '{ ' + Object.entries(v).map(([k, x]) => k + ': ' + lit(x)).join(', ') + ' }' : String(v));
const NK1 = ['q', 'k', 'v', 'o', 'gate', 'up', 'down', 'fc', 'proj'], NK2 = ['norm1', 'norm2', 'normF', 'emb', 'pos', 'head'];
const pick = (o, ks) => Object.fromEntries(ks.map((k) => [k, o[k]]));
/* 줄 끝 설명은 템플릿 설정 블록에 적힌 것을 그대로 빌린다. 템플릿에 없는 항목만 아래 기본 설명을 쓴다 */
const TPL_NOTE = (() => {
  const s = fs.readFileSync(tplPath, 'utf8'), out = {};
  const m = /const MODEL = \{([\s\S]*?)\n\};/.exec(s);
  if (m) for (const line of m[1].split('\n')) { const x = /^\s*(\w+):.*?,\s*(\/\/.*)$/.exec(line); if (x) out[x[1]] = x[2].trim(); }
  const l = /^const LORA = .*?;\s*(\/\/.*)$/m.exec(s);
  if (l) out.LORA = l[1].trim();
  return out;
})();
const line = (key, s, def) => { const c = TPL_NOTE[key] || def; return c ? s + ' '.repeat(Math.max(1, 24 - s.length)) + c : s; };
const block = [
  `// params.mjs: ${MODEL.name} (model_type ${mtype || '?'}) 의 config.json 에서 옮김`,
  'const MODEL = {',
  line('name', `  name: ${lit(MODEL.name)},`),
  line('hidden', `  hidden: ${MODEL.hidden}, layers: ${MODEL.layers}, heads: ${MODEL.heads}, kvHeads: ${MODEL.kvHeads}, headDim: ${MODEL.headDim}, ffn: ${MODEL.ffn}, vocab: ${MODEL.vocab},`),
  line('norm', `  norm: ${lit(MODEL.norm)},`, "// 'rms'(가중치만) | 'ln'(가중치 + 편향)"),
  line('mlp', `  mlp: ${lit(MODEL.mlp)},`, "// 'gated'(gate, up → act(gate)×up → down) | 'plain'(fc → act → proj)"),
  line('act', `  act: ${lit(MODEL.act)},`, '// 페이지에 쓰는 활성화 함수 이름'),
  line('pos', `  pos: ${lit(MODEL.pos)},`, "// 'rope' | 'learned'(maxPos × hidden 표를 임베딩 뒤에 더한다) | 'none'"),
  line('maxPos', `  maxPos: ${MODEL.maxPos},`),
  line('bias', `  bias: ${lit(MODEL.bias)},`),
  line('tied', `  tied: ${MODEL.tied},`, '// LM 헤드가 임베딩 표를 다시 쓴다 (값 추가 없음)'),
  `  names: ${lit(pick(names, NK1)).replace(/ \}$/, ',')}`,
  `           ${lit(pick(names, NK2)).replace(/^\{ /, '')},`,
  line('frozen', `  frozen: ${lit(MODEL.frozen)},`, "// 미세조정할 때 원래 가중치를 두는 방식. 미세조정 페이지가 아니면 ''"),
  line('grid', `  grid: ${MODEL.grid},`, '// 원래 가중치 판의 모눈 한 칸 = grid × grid 값'),
  line('expect', `  expect: ${lit(MODEL.expect)},`, '// 공개된 합계. 검사하지 않으려면 null'),
  '};',
  `const LORA = ${LORA ? lit(LORA) : 'null'};   ${TPL_NOTE.LORA || '// null = 어댑터 없음'}`,
].join('\n');

if (opt.json) {
  console.log(JSON.stringify({ source: { config: path.basename(cfgPath), model_type: mtype, template: path.basename(tplPath) },
    model: MODEL, lora: LORA, counts: COUNTS, checks, ok: checks.every((c) => c.ok), notes: [...notes, ...fusedNotes], block }, null, 2));
  process.exit(checks.every((c) => c.ok) ? 0 : 1);
}

/* ---------------------------------------------------------------- 사람이 읽는 출력 */
const wide = (ch) => /[ᄀ-ᅟ⺀-꓏가-힣豈-﫿︰-﹏＀-｠￠-￦]/.test(ch);
const dw = (s) => [...String(s)].reduce((n, ch) => n + (wide(ch) ? 2 : 1), 0);
const L = (s, n) => String(s) + ' '.repeat(Math.max(1, n - dw(s)));
const R = (s, n) => ' '.repeat(Math.max(0, n - dw(s))) + String(s);
const out = [];
const nm = MODEL.norm === 'ln' ? 'LayerNorm' : 'RMSNorm';
const biasOn = Object.entries(MODEL.bias).filter(([, v]) => v).map(([k]) => k);
out.push(`${MODEL.name}  (model_type ${mtype || '?'} → MODEL)`);
out.push(`  hidden ${MODEL.hidden} · layers ${MODEL.layers} · heads ${MODEL.heads} · kvHeads ${MODEL.kvHeads} · headDim ${MODEL.headDim} · ffn ${MODEL.ffn} · vocab ${fmt(MODEL.vocab)}`);
out.push(`  ${nm} · mlp ${MODEL.mlp}(${MODEL.act}) · pos ${MODEL.pos}${MODEL.pos === 'learned' ? ' ' + MODEL.maxPos : ''} · ${MODEL.tied ? 'tied(LM 헤드 공유)' : 'untied'} · bias ${biasOn.length ? biasOn.join(',') : '없음'} · grid ${MODEL.grid}`);
out.push(`  셈 블록: ${path.basename(tplPath)} 의 <mf:count>`);
out.push('');
out.push('층 하나 (per layer)');
const lr = COUNTS.lora;
out.push('  ' + L('키', 7) + L('이름', 27) + L('모양(d_in × d_out)', 20) + R('파라미터', 14) + (lr ? R('LoRA r=' + lr.r, 14) : ''));
const order = ['norm1', 'q', 'k', 'v', 'o', 'norm2', ...MLPK];
for (const k of order) {
  const isNorm = k.startsWith('norm'), sh = COUNTS.shapes[k];
  const shape = isNorm ? String(MODEL.hidden) + (MODEL.norm === 'ln' ? ' (+bias)' : '') : sh[0] + ' × ' + sh[1] + (COUNTS.layer[k] > sh[0] * sh[1] ? ' +b' : '');
  const lv = lr ? (lr.perModule[k] !== undefined ? fmt(lr.perModule[k]) : '-') : null;
  out.push('  ' + L(k, 7) + L(names[k], 27) + L(shape, 20) + R(fmt(COUNTS.layer[k]), 14) + (lr ? R(lv, 14) : ''));
}
out.push('  ' + L('합계', 54) + R(fmt(COUNTS.layer.total), 14) + (lr ? R(fmt(lr.perLayer), 14) : ''));
out.push('');
out.push('전체 (total)');
out.push('  ' + L(names.emb, 22) + L(MODEL.vocab + ' × ' + MODEL.hidden, 20) + R(fmt(COUNTS.emb), 16));
if (MODEL.pos === 'learned') out.push('  ' + L(names.pos, 22) + L(MODEL.maxPos + ' × ' + MODEL.hidden, 20) + R(fmt(COUNTS.pos), 16));
out.push('  ' + L('층 × ' + MODEL.layers, 22) + L(fmt(COUNTS.layer.total) + ' × ' + MODEL.layers, 20) + R(fmt(COUNTS.layers), 16));
out.push('  ' + L(names.normF + ' (마지막 ' + nm + ')', 22) + L(String(MODEL.hidden), 20) + R(fmt(COUNTS.normF), 16));
out.push('  ' + L(names.head, 22) + L(MODEL.tied ? '공유(tied)' : MODEL.hidden + ' × ' + MODEL.vocab, 20) + R(fmt(COUNTS.head), 16));
out.push('  ' + L('합계 (얼린 전체)', 42) + R(fmt(COUNTS.total), 16));
out.push('');
if (lr) {
  out.push(`학습(LoRA r=${lr.r}, alpha=${lr.alpha}, 대상 ${LORA.targets.join(',')}): 층마다 ${fmt(lr.perLayer)} × ${MODEL.layers}층 = ${fmt(lr.total)}  (얼린 전체의 ${(lr.ratio * 100).toFixed(3)}%, 붙는 곳 ${lr.sites}곳)`);
  out.push(`  PEFT 의 print_trainable_parameters 는 all params = total + trainable = ${fmt(COUNTS.total + lr.total)} 로 나눠 ${(100 * lr.total / (COUNTS.total + lr.total)).toFixed(4)}% 로 적습니다`);
} else out.push('학습(LoRA): 없음 (LORA = null)');
for (const n of fusedNotes) out.push('  주의: ' + n);
if (checks.length) {
  out.push('');
  out.push('확인 (--expect)');
  for (const c of checks) out.push('  ' + L(c.key, 11) + R(fmt(c.computed), 16) + (c.ok ? ' = ' : ' ≠ ') + R(fmt(c.expected), 16) + (c.ok ? '  OK' : `  어긋남 (차이 ${fmt(c.computed - c.expected)})`));
}
if (notes.length) { out.push(''); for (const n of notes) out.push('참고: ' + n); }
out.push('');
out.push('붙여 넣을 블록 (템플릿의 EDIT HERE 자리):');
out.push(block);
console.log(out.join('\n'));
process.exit(checks.every((c) => c.ok) ? 0 : 1);
