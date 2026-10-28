export const meta = {
  name: 'runpod-course-lessons',
  description: 'Produce RunPod hands-on lessons in parallel resource lanes on live pods (real execution, headless JupyterLab captures, README with narration blocks unless DECISIONS sets narration: false, no videos), then verify only the lessons of this run, fix with bounded re-checks, and update the indexes',
  phases: [
    { title: 'Lessons', detail: 'resource lanes over pods; lessons run in order inside a lane' },
    { title: 'Verify', detail: 'check_lesson on the lessons of this run, fix failures, re-check (bounded), update README/curriculum indexes' },
  ],
}

// =====================================================================
// 복사한 뒤 고칠 곳: REPO·PILOT·POD_ROOT, 레슨 명세(LANE_*), 의존 관계(아래 Lessons 단계)
// 레인 설계 규칙은 스킬의 references/parallel-production.md, 레슨 내용 규칙은 docs/LESSON_GUIDE.md
// 스크립트 규칙: meta는 순수 리터럴, 일반 JavaScript(TypeScript 문법 금지), 현재 시각·난수 함수 호출 금지(재개가 깨짐)
// 재개: Workflow({ scriptPath, resumeFromRunId }) — 바뀌지 않은 앞부분 agent() 호출은 저장된 결과를 돌려준다
// 실행 전제: 시작 인터뷰 완료 + docs/DECISIONS.md parallel_workflow: true(사용자 동의). false면 이 스크립트를 돌리지 않는다.
// =====================================================================
const REPO = 'D:/<course-repo>'                                     // 과정 저장소(슬래시 /로)
const GUIDE = REPO + '/docs/LESSON_GUIDE.md'
// check_lesson 전부 PASS('N PASS / 0 FAIL')와 README-only 검증을 통과한 파일럿. 파일럿 전에는 이 워크플로를 돌리지 않는다(Phase 5 전제).
// 형식 참고만 필요하면 스킬의 assets/example-lesson/ 이 있다.
const PILOT = REPO + '/chapters/chapter-<NN>/lesson-<MM>-<pilot-slug>'
const POD_ROOT = '/workspace/<course-folder>'                       // Pod 안 학습자 작업 폴더(LESSON_GUIDE 1절, init_course.py --pod-root)
const MAX_FIX_ROUNDS = 2                                           // verify → fix 를 몇 번까지(그 뒤 남은 FAIL은 unresolved로 보고)

// 모든 프롬프트에 붙이는 공통 규칙(레슨 에이전트·수정 에이전트·검사 에이전트)
const CWD = `Run every shell command from the repository root as: cd "${REPO}" && <command> (each shell call may start in another folder). Use the global python of this PC for tools/*.py and Git Bash for tools/*.sh.`
const SECRET = `Secrets: never print environment variable values or process command lines (no env, printenv, set, export -p, declare -x, cat /proc/*/environ, cat or tail /jupyter.log, jupyter server list, ps aux, pgrep -af jupyter); to count variable names use only: compgen -e | grep -ciE "key|token|pass". vLLM keys only via the VLLM_API_KEY environment variable. Never write IPs, ports, pod IDs, tokens, keys or SSH fingerprints into any file or into your returned issues; before quoting a tool error, remove everything after "token=".`
const ISOLATION = `Isolation: on the pod create and delete only files your lesson made under ${POD_ROOT}/chNN/ (lMM_* and logs/lMM_*); develop and test in /root/dev-<lesson id lowercase>/ and take scratch captures in /root/scratch-<lesson id lowercase>/ (container disk), delete both at the end, and reset the chapter folder to the learner's start state before capturing; stop only your own tmux sessions and servers (names containing your lesson id, your ports); close only your own kernels and terminals (jlab shutdown_kernels(), shutdown_terminals()); never press File > Shut Down, never tick JupyterLab checkboxes that change server settings ("Do not ask me again.", "Do not ask for rename on first save.") and never open the Settings menu; never Deploy/Start/Stop/Restart/Edit/Terminate a pod (write such STEPs from the official docs as 실행하지 않음(이유)); do not use the claude-in-chrome browser tools (the main session owns the browser).`

// L(id, slug, title, pod, port, notes)
//   id   'C03-L01' 꼴(폴더 chapters/chapter-03/lesson-01-<slug>)
//   pod  'A' | 'B' … (.env.local의 POD_<글자>_*)
//   port 이 레슨만 쓰는 jlab 로컬 포트(과정 전체에서 겹치지 않게, 예: 188xx)
//   notes 무엇을 실제로 실행·촬영하는지, 어떤 venv·포트·GPU 한도를 쓰는지, 다음 레슨에 남길 산출물 경로,
//         메인 세션이 미리 찍어 둔 콘솔 원본(_raw 파일 이름·마스킹 상자), 의존 산출물이 없을 때의 대안
const L = (id, slug, title, pod, port, notes) => ({ id, slug, title, pod, port, notes })

// 레인 = 같은 자원(Pod·GPU·포트)을 순서대로 쓰는 레슨 줄. 레인 안은 순서대로, 레인끼리는 동시에. 같은 챕터는 한 레인에만.
const LANE1 = [   // Pod A — 모델 로딩 레슨(한 번에 모델 1개, 끝나면 커널 종료)
  L('C03-L01', 'choose-model', '<레슨 제목>', 'A', 18811, '<train venv 노트북으로 무엇을 비교·출력하는지, 보여 줄 화면>'),
  L('C03-L02', 'download-and-cache', '<레슨 제목>', 'A', 18812, '<Terminal(jlab)에서 실행할 명령, 남길 폴더 — 다음 레슨이 사용>'),
]
const LANE2 = [   // Pod A — 학습(flock /root/gpu-train.lock 안에서), 산출물을 다른 레인이 기다린다. 벤치마크는 레인 1이 끝난 뒤
  L('C06-L03', 'lora-train', '<레슨 제목>', 'A', 18829, '<tmux + flock으로 학습, loss 로그, 산출물 경로(예: ' + POD_ROOT + '/ch06/outputs/lora-r16)>'),
  L('C10-L01', 'metrics', '<레슨 제목>', 'A', 18861, '<벤치마크: 같은 GPU의 레인 1이 끝난 뒤 시작(before 훅), vLLM 8000 --gpu-memory-utilization 0.5, 측정 전 nvidia-smi --query-compute-apps 로 다른 GPU 작업 기록>'),
]
const LANE3 = [   // Pod B — 서빙(vLLM 8000, --gpu-memory-utilization 0.45 이하)
  L('C07-L05', 'lora-serving', '<레슨 제목>', 'B', 18838, '<C06-L03 산출물을 쓴다. 시작할 때 산출물 경로를 확인하고, 없으면(만드는 레슨이 실패) 작은 대체 산출물을 직접 만들고 그 사실을 README에 밝힌다>'),
]
const LANE_LOCAL = [   // Pod B — GPU가 거의 필요 없는 레슨(개념·공개 웹 화면은 tools/webshot.py)
  L('C01-L01', 'concepts', '<레슨 제목>', 'B', 18851, '<공개 웹 페이지 캡처(webshot.py) + Pod에서 짧은 확인 명령>'),
]
const FINAL = []  // 다른 레인이 모두 끝난 뒤 실행할 레슨(예: 처음부터 재구축·재현 검증, Pod 상태를 바꾸는 레슨은 전용 Pod에서)

const LESSON_SCHEMA = {
  type: 'object',
  properties: {
    lesson_id: { type: 'string' },
    status: { type: 'string', enum: ['done', 'partial', 'failed'] },
    lesson_dir: { type: 'string' },
    check_lesson: { type: 'string' },
    outputs_for_next: { type: 'array', items: { type: 'string' } },
    not_executed: { type: 'array', items: { type: 'string' } },
    facts_observed: { type: 'array', items: { type: 'string' } },
    issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['lesson_id', 'status', 'lesson_dir', 'check_lesson', 'issues'],
}
const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    lessons: {
      type: 'array',
      items: {
        type: 'object',
        properties: { dir: { type: 'string' }, summary: { type: 'string' }, fails: { type: 'array', items: { type: 'string' } } },
        required: ['dir', 'summary', 'fails'],
      },
    },
  },
  required: ['lessons'],
}

function lessonDir(x) {
  const [c, l] = x.id.replace('C', '').split('-L')
  return `${REPO}/chapters/chapter-${c}/lesson-${l}-${x.slug}`
}

function lessonPrompt(x, prev) {
  const ch = x.id.slice(1, 3)
  return `You are producing ONE lesson of a Korean hands-on course for the audience recorded in docs/DECISIONS.md (default: non-developers), end to end, with REAL execution on a live RunPod pod.

Read first, fully: ${GUIDE} (the production contract: environment, pods, SSH helpers, GPU/port lanes, evidence rules, secrets, isolation, README format, quality gate) and ${REPO}/docs/DECISIONS.md (the user's decisions from the start interview — scope, deliverables, narration on/off, video lessons, audience, review depth; they override the contract's defaults and this prompt). Use the finished pilot lesson as the format reference: ${PILOT} (README.md, playbook.yaml, troubleshooting.md, _raw/redact-spec.json, _raw/annotate-spec.json, expected-output/). Tools are in ${REPO}/tools (pod.sh, pod_get.sh, jlab.py, webshot.py, redact.py, annotate.py, check_lesson.py).
${CWD}

Lesson: ${x.id} 「${x.title}」
Lesson folder (create): ${lessonDir(x)}
Pod for this lesson: ${x.pod} (learner files only under ${POD_ROOT}/ch${ch}/ on the pod; never touch other chapters' folders or other lessons' files)
Your jlab local port: ${x.port} (use only this one); jlab workspace name: ${x.id.toLowerCase()}
Content requirements: ${x.notes}
${prev ? 'Results of the previous lesson in this lane (reuse its files/state where relevant): ' + prev : ''}

If the lesson folder or the pod folder already contains partial work from an earlier interrupted run, inspect it and continue from it instead of starting over. Do the work for real: write the code/notebooks, run them on the pod, collect logs, capture real JupyterLab screens with jlab.py at every key STEP (1600x900) — for code-file STEPs use jlab's new_file_paste() so the README shows the pasted code, the Rename file dialog and the result like a learner sees them — mask via redact.py, write README.md (14 sections, every STEP with its screenshot directly below the action, PLUS — unless docs/DECISIONS.md has narration: false — the '🎙️ 해설 대본' collapsible narration blocks described in the guide section 4: one '— 시작' block under the header table, one '— STEP N' block at the end of EVERY STEP section, one '— 마무리' block before the checklist; spoken-style Korean a lecturer would say while showing that exact screen, with the real numbers), playbook.yaml (scene_id may be any short section label), troubleshooting.md, expected-output files — do NOT make storyboard.md, narration.md or any video (videos are made only when the user asks), then run python tools/check_lesson.py on the folder until every check is PASS (never edit tools/check_lesson.py). Never fake outputs: if something cannot run, state it clearly in the README as "실행하지 않음(이유)". RunPod console screens come only from the _raw captures named in the content requirements; if a STEP needs a console screen that was not provided, write it from the official docs and record playbook not_captured with the same reason text in the README. Clean up everything you started on the pod (servers, tmux sessions, notebook kernels, terminals, the dev and scratch folders).
${SECRET}
${ISOLATION}

Return the structured result: status, lesson_dir, the last summary line of check_lesson ("N PASS / M FAIL"), outputs_for_next (pod paths later lessons can use), not_executed items, facts_observed (UI labels/behaviours you verified on the pod that the guide lacked or marked 조사/미확인 — one line each with the STEP; do not edit shared docs yourself), issues.`
}

// 다른 레인의 결과를 기다리는 약속(promise). 두 번 resolve해도 문제없다.
function deferred() { let r; const p = new Promise((res) => { r = res }); return { p, r } }
const adapterReady = deferred()   // 예: C06-L03 학습이 끝나야 C07-L05 서빙을 시작
const lane1Done = deferred()      // 예: 레인 1(같은 GPU)이 끝나야 레인 2의 벤치마크 C10-L01을 시작

// 무거운 작업의 동시 실행 수 제한(예: Pod를 쓰는 수정 에이전트, 요청받은 영상 렌더)
function makeSemaphore(n) {
  let active = 0
  const q = []
  const next = () => {
    if (active < n && q.length) {
      active++
      const { fn, res } = q.shift()
      fn().then(res, () => res(null)).finally(() => { active--; next() })
    }
  }
  return (fn) => new Promise((res) => { q.push({ fn, res }); next() })
}

const results = {}

// 재개할 때 레인 구조를 바꿨다면: 원래 실행 journal.jsonl의 'started' 순서대로 끝난 레슨 ID를 적는다.
// 재개 캐시 키가 호출 순서에 묶여 있어서, 이 순서를 지켜야 끝난 레슨이 캐시에서 돌아온다(처음 실행이면 빈 목록).
const REPLAY = []
const replayGate = REPLAY.map(() => deferred())

async function runLesson(x, prev) {
  const gi = REPLAY.indexOf(x.id)
  if (gi > 0) await replayGate[gi - 1].p
  else if (gi < 0 && REPLAY.length) await replayGate[REPLAY.length - 1].p
  let r = null
  // 첫 시도는 프롬프트·옵션을 그대로 둔다(재개 캐시가 맞도록). StructuredOutput 없이 끝나면 agent()가 예외를 던진다.
  for (let attempt = 1; attempt <= 3 && !r; attempt++) {
    const prompt = attempt === 1 ? lessonPrompt(x, prev)
      : lessonPrompt(x, prev) + `\n\nRetry ${attempt}: an earlier attempt of this lesson stopped without returning the structured result. The lesson folder and the pod folder may already hold its partial or finished work: inspect them, finish only what is missing, re-run check_lesson, and end by returning the structured result.`
    const label = attempt === 1 ? `lesson:${x.id}` : `lesson:${x.id}#${attempt}`
    try {
      const call = agent(prompt, { label, phase: 'Lessons', schema: LESSON_SCHEMA })
      if (gi >= 0) replayGate[gi].r(true)
      r = await call
    } catch (e) {
      if (gi >= 0) replayGate[gi].r(true)
      log(`${x.id}: attempt ${attempt} failed (${String((e && e.message) || e).slice(0, 120)})`)
    }
  }
  results[x.id] = r
  log(`${x.id}: ${r ? r.status + ' / ' + r.check_lesson : 'no result after 3 attempts'}`)
  return r
}
function summarize(r) {
  if (!r) return ''
  return `${r.lesson_id} ${r.status}; outputs: ${(r.outputs_for_next || []).join(', ')}; issues: ${(r.issues || []).join(' | ')}`
}
async function lane(lessons, hooks) {
  let prev = ''
  for (const x of lessons) {
    if (hooks && hooks.before && hooks.before[x.id]) await hooks.before[x.id]()
    const r = await runLesson(x, prev)
    prev = summarize(r)
    if (hooks && hooks.after && hooks.after[x.id]) hooks.after[x.id](r)   // 실패(null)여도 부른다 → 기다리는 레인이 멈추지 않음
  }
}

phase('Lessons')
await Promise.allSettled([
  lane(LANE1).finally(() => lane1Done.r(true)),
  // 산출물을 만든 레슨 직후에 풀고, 그 레슨이 목록에서 빠졌어도 레인이 끝나면 한 번 더 푼다(교착 방지)
  lane(LANE2, {
    after: { 'C06-L03': () => adapterReady.r(true) },
    before: { 'C10-L01': () => lane1Done.p },          // 같은 GPU를 쓰는 레인 1이 끝난 뒤 벤치마크
  }).finally(() => adapterReady.r(true)),
  lane(LANE3, { before: { 'C07-L05': () => adapterReady.p } }),
  lane(LANE_LOCAL),
])
if (FINAL.length) await lane(FINAL)

phase('Verify')
// 이번 실행의 레슨만 검사·수정한다. 범위 밖 레슨(파일럿·이전 실행)은 검사하지도 고치지도 않는다.
const all = [...LANE1, ...LANE2, ...LANE3, ...LANE_LOCAL, ...FINAL]
const slash = (d) => String(d).replace(/\\/g, '/').replace(/\/+$/, '')
const key2 = (d) => slash(d).split('/').filter(Boolean).slice(-2).join('/')   // 'chapter-NN/lesson-MM-slug'
const specOf = (dir) => all.find((x) => key2(lessonDir(x)) === key2(dir))
const podSem = makeSemaphore(4)

function verifyPrompt(dirs) {
  return `${CWD}
Run python tools/check_lesson.py on EACH of these lesson folders and only these (do not check or report any other folder):
${dirs.map((d) => '- ' + d).join('\n')}
For each folder report: dir exactly as given above (absolute path with forward slashes), summary (the last line "N PASS / M FAIL"), fails (the FAIL lines). Do not modify anything (the checker itself rewrites evidence-manifest.json; that is fine). Return JSON {lessons:[{dir, summary, fails:[...]}]}.`
}
function fixPrompt(l, i, round) {
  const x = specOf(l.dir)
  const where = x
    ? `If you need the pod, use Pod ${x.pod}, jlab local port ${x.port} and jlab workspace ${x.id.toLowerCase()}-fix${round}.`
    : `If you need a pod, use jlab local port ${18990 + i} (no one else uses it).`
  return `Fix ONLY the lesson folder ${l.dir} so that python tools/check_lesson.py passes. Current FAIL lines: ${l.fails.join(' | ')}.
Read ${GUIDE} and ${REPO}/docs/DECISIONS.md first. ${CWD} ${where}
Fix the real cause (missing screenshot → capture it with jlab.py on the right pod; missing link → correct the README; secret hit → remove the value from the file; missing narration block → write it from the real screenshots and logs; missing reason → write the playbook not_captured text in that STEP). Never fake outputs. Never edit tools/check_lesson.py or any other lesson.
${SECRET}
${ISOLATION}
Return the final summary line.`
}

const rounds = []
let toCheck = all.map(lessonDir)
let unresolved = []
for (let round = 1; toCheck.length; round++) {
  const v = await agent(verifyPrompt(toCheck), { label: `verify:${round}`, phase: 'Verify', schema: VERIFY_SCHEMA })
  if (!v) { unresolved = toCheck.map((d) => ({ dir: d, summary: 'verify agent returned nothing', fails: [] })); log(`verify ${round}: no result`); break }
  const failing = v.lessons.filter((l) => l.fails.length)
  rounds.push({ round, checked: toCheck.length, failing: failing.map((l) => l.dir) })
  log(`verify ${round}: ${failing.length}/${toCheck.length} lessons with FAIL`)
  if (!failing.length) break
  if (round > MAX_FIX_ROUNDS) { unresolved = failing; log(`stop after ${MAX_FIX_ROUNDS} fix rounds: ${failing.length} lessons still FAIL (see unresolved)`); break }
  await parallel(failing.map((l, i) => () => podSem(() =>
    agent(fixPrompt(l, i, round), { label: `fix${round}:${key2(l.dir)}`, phase: 'Verify' }))))
  toCheck = failing.map((l) => l.dir)
}

const index = await agent(`${CWD}
Update ${REPO}/README.md (the course front page) so its lesson table lists every lesson folder under ${REPO}/chapters in order with a link to its README.md and its title (first heading of the README). Also update the 상태 column in ${REPO}/curriculum.md (✅ when the lesson README exists and its latest check_lesson passed, 🟡 when it exists but did not). Edit only these two files and keep the rest of both files. Return a one-paragraph summary.`,
  { label: 'index:update', phase: 'Verify' })

// facts_observed는 메인 세션이 워크플로가 끝난 뒤 environment/versions.md에 옮긴다(레슨 에이전트는 공유 문서를 고치지 않는다).
return { results, rounds, unresolved, index }
