export const meta = {
  name: 'readme-only-check',
  description: 'README-only verification for one lesson: literal action list + adversarial beginner critique (read-only)',
  phases: [
    { title: 'README-only', detail: 'two independent context-free readers of the README' },
  ],
}

// 실행: Workflow({ script 또는 scriptPath, args: { lesson: 'D:/<repo>/chapters/chapter-NN/lesson-MM-slug',
//        start: 'the RunPod console Pods page', end: 'STEP 25' } })
// end 고르기: 결제·삭제·Pod 상태를 바꾸는 STEP(Stop, Terminate, Deploy, Restart Pod …) 바로 앞 STEP까지(파일럿은 STEP 26이 Stop → 'STEP 25').
//   그 앞의 행동이라도 그런 성격이면 에이전트가 do_not_execute=true로 표시한다 — 실행 대조 때 누르지 않고 보이는지만 확인한다.
// 두 에이전트 모두 README와 그 안의 그림만 읽는다(브라우저·SSH·다른 파일 금지).
// Workflow 도구가 없으면 아래 두 프롬프트(RULES + Task)를 그대로 서브에이전트 두 개에게 따로 준다.
const LESSON = (args && args.lesson) || 'D:/<course-repo>/chapters/chapter-<NN>/lesson-<MM>-<slug>'
const README = LESSON + '/README.md'
const START = (args && args.start) || 'the first STEP'
const END = (args && args.end) || 'the last STEP before any Stop/Terminate STEP'

const ACTION_SCHEMA = {
  type: 'object',
  properties: {
    actions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          n: { type: 'number' },
          readme_step: { type: 'string' },
          screen: { type: 'string' },
          do: { type: 'string', description: 'exact UI action: click <exact label>, type <exact text>, press <keys>, wait' },
          input: { type: 'string' },
          expect: { type: 'string', description: 'exact text/state the README says should appear' },
          underivable: { type: 'boolean' },
          do_not_execute: { type: 'boolean', description: 'true when the action costs money, destroys data or changes the pod state (Deploy, Start, Stop, Terminate, Restart Pod, Edit Pod, File > Shut Down, Delete, Web terminal toggle, account settings): the executor must not perform it and only checks that the control/dialog is visible' },
          note: { type: 'string' },
        },
        required: ['n', 'readme_step', 'screen', 'do', 'expect', 'underivable', 'do_not_execute'],
      },
    },
    blocking_gaps: { type: 'array', items: { type: 'string' } },
  },
  required: ['actions', 'blocking_gaps'],
}

const CRIT_SCHEMA = {
  type: 'object',
  properties: {
    issues: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          step: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
          problem: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['step', 'severity', 'problem', 'fix'],
      },
    },
  },
  required: ['issues'],
}

const RULES = `You must read ONLY this file: ${README}
and the images it links (relative to ${LESSON}; open them with the Read tool). Do NOT read any other file in the repository (no playbook.yaml, no logs, no code folder) and do not use a browser or SSH. You have no other context: you are a beginner with a RunPod account, a running GPU Pod and Chrome, and nothing else.`

phase('README-only')
const [actionList, critique] = await parallel([
  () => agent(`${RULES}

Task: convert the README into a LITERAL action list that a robot could execute in the browser without interpretation, from ${START} to the end of ${END}. One atomic action per item (one click, one typed line + Enter, one key chord, one wait/check). Use the exact UI labels and exact text exactly as written in the README. For each action give the expected visible result exactly as the README states it. If an action cannot be derived unambiguously from the README alone (missing label, unclear location, unclear order, unclear what to type, missing success criterion), set underivable=true and explain in note. Set do_not_execute=true for every action that costs money, destroys data or changes the pod state (Deploy, Start, Stop, Terminate, Restart Pod, Edit Pod, File > Shut Down, Delete, toggling Web terminal, account settings); otherwise false. List anything that would block a beginner in blocking_gaps.`, { label: 'readme:action-list', phase: 'README-only', schema: ACTION_SCHEMA }),
  () => agent(`${RULES}

Task: act as an adversarial reviewer on behalf of a NON-DEVELOPER who has never used a terminal. Walk through every STEP and find where they would get stuck or make a mistake: ambiguous wording, a needed action that is implied but not written, wrong or inconsistent labels between text and screenshots, an image placed far from its action, jargon used before it is explained, success criteria that cannot be checked, safety risks not warned about, inconsistencies (numbers, file names, step references), a missing or unclear Python environment (which venv/kernel, where it is created, what to do after a Pod restart). Check that every screenshot actually shows what the sentence above it claims (open the images). Be concrete: cite the STEP and quote the text. Rate severity: blocker (cannot continue), major (likely mistake), minor (polish). Do not suggest restructuring the whole document; give targeted fixes.`, { label: 'readme:beginner-critic', phase: 'README-only', schema: CRIT_SCHEMA }),
])
return { actionList, critique }
