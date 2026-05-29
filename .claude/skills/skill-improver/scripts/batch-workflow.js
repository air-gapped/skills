export const meta = {
  name: 'skill-improver-batch',
  description: 'Batch improve + freshen N skills via a recon->apply->blind pipeline. Skill list comes from args.',
  phases: [
    { title: 'Recon', detail: 'cold self-score + ranked hypotheses + online freshen probe, one agent per skill' },
    { title: 'Baseline blind', detail: 'independent blind score on the unmodified skill' },
    { title: 'Apply', detail: 'improve loop (<=5 iter) + verified freshen updates + backlog, edits real files' },
    { title: 'Final blind', detail: 'one independent blind score per skill (symmetric with baseline)' },
  ],
}

// ---------------------------------------------------------------------------
// Reusable batch driver for skill-improver. Invoke with:
//
//   Workflow({ scriptPath: "~/.claude/skills/skill-improver/scripts/batch-workflow.js",
//              args: ["keda", "helm", "argo-cd-apps"] })
//
// args forms (all accepted):
//   ["keda", "helm"]                                  bare names -> resolved against BASE
//   ["/abs/path/to/skill", ...]                       absolute dirs
//   [{ dir: "keda", hints: "check kedacore/keda releases" }, ...]   per-skill freshen focus
//   { skills: [...], baseDir: "/some/skills/root" }    override the default skills root
//
// Each agent inherits the main-loop model (Opus) — satisfies the "most capable
// model for validation" rule. No git ops happen inside agents; commit after review.
// ---------------------------------------------------------------------------

// Paths use ~ (home dir) so the committed script never hard-codes a username.
// Agents are told to expand ~ to an absolute path before reading.
const REF = '~/.claude/skills/skill-improver/references'
const DEFAULT_BASE = '~/projects/skills/.claude/skills'
const HOME_NOTE = 'NOTE: paths below starting with ~ are under your home directory — expand ~ to an absolute path (run `echo $HOME` if unsure) before reading or editing.'

// The Workflow tool sometimes delivers `args` as a JSON-encoded string instead
// of a real array/object. Normalize that here so callers can pass either form.
let ARGS = args
if (typeof ARGS === 'string') {
  try { ARGS = JSON.parse(ARGS) }
  catch (e) { ARGS = ARGS.split(/[\s,]+/).filter(Boolean) }
}
const RAW = Array.isArray(ARGS) ? ARGS : (ARGS && Array.isArray(ARGS.skills) ? ARGS.skills : null)
if (!RAW || !RAW.length) {
  throw new Error('skill-improver-batch: pass args as a non-empty array of skill names, dirs, or {dir,hints} objects — e.g. args: ["keda","helm"]')
}
const BASE = (ARGS && !Array.isArray(ARGS) && ARGS.baseDir) || DEFAULT_BASE
const resolveDir = (d) => (d.includes('/') ? d : BASE + '/' + d)
const baseName = (d) => d.split('/').filter(Boolean).pop()
const norm = (it) => {
  if (typeof it === 'string') { const dir = resolveDir(it); return { name: baseName(dir), dir, hints: '' } }
  const dir = resolveDir(it.dir)
  return { name: it.name || baseName(dir), dir, hints: it.hints || '' }
}
const SKILLS = RAW.map(norm)
log(`skill-improver batch over ${SKILLS.length}: ${SKILLS.map(s => s.name).join(', ')}`)

const DIM = {
  type: 'object', additionalProperties: false,
  properties: { n: { type: 'integer' }, name: { type: 'string' }, score: { type: 'integer' }, justification: { type: 'string' } },
  required: ['n', 'name', 'score', 'justification'],
}
const BLIND_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: { dims: { type: 'array', items: DIM }, total: { type: 'integer' }, topIssues: { type: 'array', items: { type: 'string' } } },
  required: ['dims', 'total', 'topIssues'],
}
const RECON_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    self: { type: 'object', additionalProperties: false, properties: {
      dims: { type: 'array', items: DIM }, total: { type: 'integer' }, borisFindings: { type: 'array', items: { type: 'string' } },
    }, required: ['dims', 'total', 'borisFindings'] },
    hypotheses: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      dim: { type: 'string' }, change: { type: 'string' }, expectedImpact: { type: 'string' }, complexity: { type: 'string' },
    }, required: ['dim', 'change', 'expectedImpact', 'complexity'] } },
    freshen: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      ref: { type: 'string' }, verdict: { type: 'string', enum: ['current', 'stale', 'deprecated', 'unverifiable'] },
      evidence: { type: 'string' }, proposedUpdate: { type: 'string' },
    }, required: ['ref', 'verdict', 'evidence', 'proposedUpdate'] } },
    notes: { type: 'string' },
  },
  required: ['self', 'hypotheses', 'freshen', 'notes'],
}
const APPLY_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    iterations: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      iter: { type: 'integer' }, change: { type: 'string' }, status: { type: 'string' }, deltaNote: { type: 'string' },
    }, required: ['iter', 'change', 'status', 'deltaNote'] } },
    freshenApplied: { type: 'array', items: { type: 'string' } },
    finalSelfTotal: { type: 'integer' },
    finalSelfDims: { type: 'array', items: { type: 'object', additionalProperties: false, properties: { n: { type: 'integer' }, score: { type: 'integer' } }, required: ['n', 'score'] } },
    filesChanged: { type: 'array', items: { type: 'string' } },
    backlogUpdated: { type: 'boolean' },
    summary: { type: 'string' },
  },
  required: ['iterations', 'freshenApplied', 'finalSelfTotal', 'finalSelfDims', 'filesChanged', 'backlogUpdated', 'summary'],
}

function reconPrompt(s) {
  return [
    'You are the RECON stage of the skill-improver autoresearch loop. Score and analyze one Claude Code skill. Your final output IS structured data, not a human-facing message.',
    '',
    HOME_NOTE,
    '',
    'Skill: ' + s.name,
    'Skill directory: ' + s.dir,
    '',
    'STEP 1 — Read these reference files IN FULL:',
    '- ' + REF + '/quality-rubric.md  (the 10-dimension rubric + the Boris Alignment Check caps)',
    '- ' + REF + '/improvement-patterns.md  (before/after patterns organized by dimension)',
    '- ' + REF + '/freshen-patterns.md  (Freshen Mode workflow F0-F6, extraction heuristics, probe templates, classification rules)',
    '',
    'STEP 2 — Read the ENTIRE target skill: ' + s.dir + '/SKILL.md and every file under its references/, scripts/, evals/ subdirs (whatever exists). Note whether references/sources.md and references/improvement-backlog.md exist. If improvement-backlog.md exists, read it; do NOT re-propose its Open items unless new evidence makes them breakable in one iteration now.',
    '',
    'STEP 3 — Score all 10 dimensions COLD against the rubric criteria (read the file fresh, do not anchor on any prior score). Apply the Boris Alignment Check caps where they fire (Dim 6 strict-workflow scaffolding, Dim 4 up-front context dumps, Dim 9 model-version compensation) and the Dim 9 staleness/spec caps. If references/sources.md is absent, Dim 9 is capped at 6 per the rubric; if present, check its Last verified: dates for the staleness cap. Return the dims (n, name, score, justification), the total, and any borisFindings as strings.',
    '',
    'STEP 4 — Produce 3-6 ranked improvement HYPOTHESES (rubric-driven). Rules: prefer hypotheses that lift Boris caps over cosmetic dims of equal magnitude; prefer deletion/simplification over addition; each change must be ATOMIC (a single present-tense verb, no "and"). For each: target dim, the specific change, expected score impact, complexity cost.',
    '',
    'STEP 5 — FRESHEN PROBE. Extract the skill external references (tool/version claims, API endpoints, CLI flags, pinned versions, deprecation-prone statements) per freshen-patterns.md extraction heuristics. For the most staleness-prone claims, verify currency using the gh CLI, WebSearch, and WebFetch. Prefer `gh` for github.com release/tag lookups. Follow freshen-patterns.md classification. For each probed ref return: ref, verdict (current|stale|deprecated|unverifiable), evidence (URL + date/version observed), proposedUpdate (the exact text edit to apply, or empty string if current/unverifiable). Be specific and cite real sources.',
    (s.hints ? 'Domain focus for this skill: ' + s.hints : 'No domain hints supplied — extract probe targets from the skill content itself.'),
    '',
    'Do not edit any files in this stage. Return ONLY the structured output.',
  ].join('\n')
}

function blindPrompt(s) {
  return [
    'Score this Claude Code skill for quality. Be honest and critical — most decent skills score 50-70, 80+ is excellent, 90+ is rare. You have never seen this skill before; score it blind. Your final output IS structured data.',
    '',
    HOME_NOTE,
    '',
    '1. Read the rubric: ' + REF + '/quality-rubric.md',
    '2. Read the design guide: ' + REF + '/anthropic-skill-design.md',
    '3. Read the skill: ' + s.dir + '/SKILL.md',
    '4. Read all files in: ' + s.dir + '/references/',
    '5. Read any scripts/evals: ' + s.dir + '/scripts/ and ' + s.dir + '/evals/ (if present).',
    '',
    'For Dimension 1: check what falls within the first 1,536 chars of combined description + when_to_use, and penalize if key trigger phrases are past the cutoff. Note whether the skill splits the two fields or stuffs everything into description.',
    'For Dimension 9: check sources.md Last verified: dates (staleness cap), spec validity of name/description (hard-fail cap at 3), and whether appropriate frontmatter fields are used.',
    'Apply the Boris Alignment Check caps where they fire.',
    '',
    'Score each dimension (0-10) with a one-sentence justification (fields: n, name, score, justification). Return the dims array, the total, and a topIssues list (<=3 lines, with file:line where applicable).',
  ].join('\n')
}

function applyPrompt(s, recon) {
  return [
    'You are the APPLY stage of the skill-improver loop for skill "' + s.name + '" at ' + s.dir + '. Make REAL edits to the files with Edit/Write. Your final output IS structured data.',
    '',
    HOME_NOTE,
    '',
    'RECON FINDINGS (scores, ranked hypotheses, freshen verdicts) to act on:',
    '```json',
    JSON.stringify(recon, null, 2),
    '```',
    '',
    'First read ' + REF + '/quality-rubric.md and ' + REF + '/improvement-patterns.md, then re-read the current skill files at ' + s.dir + '.',
    '',
    'WORKSTREAM A — IMPROVE LOOP (rubric-driven), skill-improver methodology:',
    '- Run up to 5 keep/discard iterations. ONE ATOMIC change per iteration (single present-tense verb, no "and"; pure relocation is allowed but must not rewrite prose in the same step).',
    '- After each change, cold-score the affected dimensions. KEEP if the total improves, or is equal but simpler. Otherwise REVERT that exact edit and log it as discard.',
    '- Prefer deletion/simplification over addition. Prioritize hypotheses that lift Boris caps (structural) over cosmetic dims.',
    '- Preserve the author intent and domain knowledge — improve HOW it teaches, not WHAT it teaches.',
    '- Keep SKILL.md under 500 lines; keep file references one level deep; do not break frontmatter (name must match dir, description <=1024 chars, no XML tags).',
    '',
    'WORKSTREAM B — FRESHEN (evidence-driven, apply only what recon VERIFIED):',
    '- Apply ONLY freshen items marked stale or deprecated that carry solid evidence (URL + observed version/date). Skip current and unverifiable. Do NOT apply a version bump you cannot stand behind from the evidence.',
    '- If references/sources.md EXISTS: stamp "Last verified: <today>" on rows you re-confirmed online; add rows for any new sources you used.',
    '- If references/sources.md does NOT exist: CREATE it with a dated per-URL table (columns: Source | URL | Last verified | Notes), each row stamped with today\'s date, covering the skill key external references. This lifts the Dim 9 staleness cap (raises the ceiling above 6).',
    '',
    'WORKSTREAM C — BACKLOG (Phase 6), write/update ' + s.dir + '/references/improvement-backlog.md:',
    '- ## Open: every issue you ATTEMPTED as a hypothesis but could not apply in one iteration (multi-file restructure, author-only domain content, rule-ceiling discards). For each: one-line title, dim number, file:line or file-set, why it could not be applied in one iteration. Open is a work-not-done log, NOT a wishlist — omit hypothetical future risks.',
    '- ## Resolved this pass: one line per change the metric actually registered.',
    '- If the backlog already exists, read it, carry forward still-open items with a "(carried <today>)" marker, and move any resolved ones into Resolved this pass.',
    '',
    'RULES:',
    '- Do NOT run git commit/add/push — the orchestrator commits after review.',
    '- Verify SKILL.md frontmatter remains valid after edits.',
    '- Be truthful: creating an empty placeholder file does not "resolve" a cap.',
    '',
    'Return structured: iterations (iter, change, status[keep|keep (simplification)|discard|crash], deltaNote), freshenApplied (list of applied updates), finalSelfTotal, finalSelfDims (n, score for all 10), filesChanged (paths), backlogUpdated (bool), and a 2-3 sentence summary.',
  ].join('\n')
}

const results = await pipeline(
  SKILLS,
  async (skill) => {
    const [recon, baselineBlind] = await parallel([
      () => agent(reconPrompt(skill), { label: `recon:${skill.name}`, phase: 'Recon', schema: RECON_SCHEMA }),
      () => agent(blindPrompt(skill), { label: `baseline-blind:${skill.name}`, phase: 'Baseline blind', schema: BLIND_SCHEMA }),
    ])
    log(`recon ${skill.name}: self=${recon?.self?.total ?? '?'} baselineBlind=${baselineBlind?.total ?? '?'} freshen=${(recon?.freshen || []).filter(f => f.verdict === 'stale' || f.verdict === 'deprecated').length} actionable`)
    return { skill, recon, baselineBlind }
  },
  async (prev, skill) => {
    if (!prev.recon) { log(`apply ${skill.name}: SKIP (no recon)`); return { ...prev, apply: null } }
    const apply = await agent(applyPrompt(skill, prev.recon), { label: `apply:${skill.name}`, phase: 'Apply', schema: APPLY_SCHEMA })
    const kept = (apply?.iterations || []).filter(i => /keep/i.test(i.status || '')).length
    log(`apply ${skill.name}: kept=${kept} freshenApplied=${(apply?.freshenApplied || []).length} finalSelf=${apply?.finalSelfTotal ?? '?'}`)
    return { ...prev, apply }
  },
  async (prev, skill) => {
    // ONE blind scorer — symmetric with the single baseline scorer so the
    // baseline->final delta is apples-to-apples (a median-of-N final vs a
    // single-sample baseline would credit variance-reduction as "improvement").
    const finalBlind = await agent(blindPrompt(skill), { label: `final-blind:${skill.name}`, phase: 'Final blind', schema: BLIND_SCHEMA })
    log(`final-blind ${skill.name}: ${finalBlind?.total ?? '?'}`)
    return { ...prev, finalBlind }
  }
)

return results.filter(Boolean).map(r => ({
  name: r.skill.name,
  baselineSelf: r.recon?.self?.total ?? null,
  baselineBlind: r.baselineBlind?.total ?? null,
  finalSelf: r.apply?.finalSelfTotal ?? null,
  finalBlind: r.finalBlind?.total ?? null,
  blindDelta: (r.finalBlind?.total != null && r.baselineBlind?.total != null) ? (r.finalBlind.total - r.baselineBlind.total) : null,
  keptChanges: (r.apply?.iterations || []).filter(i => /keep/i.test(i.status || '')).length,
  discardedChanges: (r.apply?.iterations || []).filter(i => /discard/i.test(i.status || '')).length,
  freshenApplied: r.apply?.freshenApplied ?? [],
  filesChanged: r.apply?.filesChanged ?? [],
  backlogUpdated: r.apply?.backlogUpdated ?? false,
  iterations: r.apply?.iterations ?? [],
  borisFindings: r.recon?.self?.borisFindings ?? [],
  finalBlindDims: r.finalBlind?.dims ?? [],
  finalBlindTopIssues: r.finalBlind?.topIssues ?? [],
  baselineBlindDims: r.baselineBlind?.dims ?? [],
  summary: r.apply?.summary ?? '',
}))
