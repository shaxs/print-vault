<!--
Last Updated: 2026-07-05
Version: 2.0.0
User: shaxs

Auto-loaded at the start of every Copilot Chat session. Copilot equivalent of CLAUDE.md.

CHANGELOG v2.0.0: Removed the TaskSync/Vibe Pilot get_feedback continuous-polling loop —
Vibe Pilot is not currently orchestrating this project; the loop's original purpose (GitHub
Copilot Premium Request Unit billing arbitrage) no longer exists as of Copilot's June 2026
move to usage-based billing. If Vibe Pilot is reactivated for this project later, its own
onboarding should reintroduce whatever loop mechanism it needs at that time — don't hand-restore
this section from history without re-evaluating whether it's still the right approach.
Folded in the File Safety/Backup and Git Workflow protocols from the old AGENTS.md (content
worth keeping, previously undocumented in CLAUDE.md). Updated all canonical file references to
match the current chat_docs/instructions/ file set.
-->

# Print Vault — Copilot Instructions

## Read First

- This file is pointer-first: canonical rules live in `chat_docs/instructions/`. Don't duplicate their detail here.
- Before starting a category of work listed in the router below, use the `read_file` tool to load the matching canonical file — don't wait to be asked, and don't rely on training data for project-specific conventions.
- State which canonical file was read and the key constraint(s) before proceeding with implementation.

## Session Start — Check Memory First

- Use mcp-memory-service's MCP tools as the *only* persistence mechanism for print-vault decisions, conventions, and context. Don't rely on your own conversation history alone across sessions — it doesn't sync to Claude Code, Cline, or the local LLM, which is the whole point of this setup.
- At the start of a session, or before starting a new task/feature, call `memory_search` filtered by this project's tag (`print-vault`) for relevant prior decisions, conventions, or context before asking the user to re-explain anything.
- When a non-trivial decision is made (architecture choice, library selection, tradeoff) or a bug's root cause is found, call `memory_store` to record it — content, tags, and a `type`. For the `type` field, consult `chat_docs/instructions/MEMORY_TAXONOMY.md` before choosing — use the most precise real base type or subtype, not an invented one. Never use `task`, `convention`, or `documentation` as `type` values; see that file for the correct equivalents.
- Always include the `print-vault` tag alongside any content-specific tags.
- Beyond the required `type` field and the `print-vault` tag, additional descriptive tags should be either (a) a free-form topic/component name matching the actual feature or file involved (e.g. `thumbnail-generation`, `django-q`), or (b) one of these fixed cross-cutting tag categories, for things `type` alone doesn't capture: `documentation`, `architecture`. Don't invent synonyms for existing `type` values or this fixed list — if something genuinely doesn't fit either, ask before introducing a new tag.
- Don't log transient state (in-progress step details, one-off file paths) — only things with reuse value across sessions.
- If a mistake or recurring gotcha gets fixed (not just a one-off bug, but something likely to bite again), use `mistake_note_add` rather than a regular memory — check `mistake_note_search` before repeating work you may have already been burned by.
- If a `memory_store` call reports a conflict, or search results seem contradictory, use `memory_conflicts` to check for superseded/contradicting entries.

## Code Exploration — Check the Graph Before Grepping

GitNexus has no skill-file layer for Copilot the way it does for Claude Code, and no automatic hook enrichment either — this section carries the full routing and safety logic directly.

- **Copilot exposes GitNexus's tools in groups, not all at once.** `check`, `detect_changes`, `group_list`, `query`, `rename`, and `tool_map` are available directly. Everything else — including `impact` and `context`, both required by the rules below — sits behind an activator tool and must be unlocked first: call `activate_code_symbol_context_tools` before your first use of `context`/`impact`/`cypher` in a session; `activate_api_route_analysis_tools` before `api_impact`/`route_map`/`shape_check`; `activate_taint_analysis_and_dependence_tools` before `explain`/`pdg_query`. Do this proactively, not only after a direct call fails.
- For structural questions (callers, callees, dependencies, blast radius) — even for a quick/simple-feeling lookup — GitNexus's graph tools are MANDATORY before falling back to grep/glob. "Quick enough to just grep" is not a valid reason to skip this. Key tools: `context` (360° symbol view), `impact` (blast radius before editing), `trace` (shortest path between two symbols), `detect_changes` (git-diff impact), `cypher` (raw graph queries for anything else).
- For textual pattern, concept, or string-literal searches, `query` is unreliable on this machine (upstream native bug in the FTS/VECTOR layer, not a config issue; see GitNexus issues #1217/#1365/#1674). You are explicitly authorized to use `grep`/`glob` as your PRIMARY search tool for this category, not `query` first.
- If `query` returns an empty or suspiciously thin result for something you'd expect to find, don't trust that as conclusive — cross-verify with `grep` before concluding it doesn't exist. This does not apply retroactively to results that already look complete and correct.
- **No automatic staleness check exists for this client.** Claude Code has a hook that flags a stale index automatically after commits — Copilot doesn't. Before trusting a GitNexus result for anything non-trivial, run `gitnexus status` yourself if it's been a while since the last index, or after recent commits/merges. A stale-index answer can look identical to a correct one.
- Reserve manual file exploration for genuinely non-search, non-structural cases (or where the rules above have already authorized grep) — not skipped preemptively because grep felt faster.
- When a grep/glob search returns more than a handful of matches (roughly more than 3-5, or matches spread across many files), delegate filtering to the local LLM (see the Local LLM Routing section) before reading each match's full surrounding context yourself — pass the raw hits (file, line, snippet) and ask it to separate genuinely relevant matches from coincidental name collisions. Only read the files that survive that filter. For a small number of matches, read them directly; the delegation round-trip isn't worth it at that scale.
- Before editing a function/class with more than a couple of call sites, run `impact` first (activating it first, per above, if this is the first GitNexus call this session).

## Local LLM Routing

- Before summarizing, drafting boilerplate, classifying, or extracting structured data from any text — even short or simple content — call the matching `local-llm` tool first (`local_summarize`, `local_draft`, `local_classify`, `local_extract`), before reading the content yourself for the purpose of doing the task directly. Reading the source content is fine and often necessary — to extract what to pass into the tool, or to verify the tool's output — but that reading must feed the delegation call, not substitute for it.
- This applies regardless of how easy the task feels: the local model is free; your tokens are not. "Trivial enough to just do myself" is not a valid reason to skip delegation for these task types.
- Skip delegation only if the task requires judgment about this codebase's architecture, non-trivial multi-file reasoning, or anything in Non-Negotiables — delegate the mechanical parts, keep judgment calls yourself.
- Review delegated output before presenting it — you're still responsible for correctness.

## Documentation Review Pipeline

When a new or updated file lands in `chat_docs/api/`, delegate an initial digest to the local LLM (`local_extract` or `local_summarize`), then review that digest yourself and store only genuinely non-obvious facts (gotchas, rationale not stated elsewhere, cross-cutting conventions) via `memory_store` — don't store restated doc content, and don't skip this step silently; tell the user what you found and stored.

## Non-Negotiables

- API changes (new/modified endpoints, views, serializers, URL params) must have docs created/updated in `chat_docs/api/` before committing.
- Always use `frontend/src/components/BaseModal.vue` for modal UIs — never build a custom modal.
- Always use CSS variables for colors/theme values — never hardcode hex colors.
- Test UI changes in both light and dark mode before considering the work done.
- **Dev environment**: non-Docker, bare-metal dev servers run in the user's own external PowerShell session. Do **not** run `python manage.py migrate`, `python manage.py makemigrations`, `python manage.py runserver`, `npm run dev`, `npm install`, or restart/stop dev servers — ask the user to run these instead.
- **Production environment**: Docker commands (`docker compose up`, `docker compose build`, etc.) may be run directly.
- All other commands (git, file operations, tests, linters) may be run directly, subject to the Git Workflow rule below.
- Don't bump versions on every merge — follow `chat_docs/instructions/VERSION_UPDATE_CHECKLIST.md` for release cadence.
- Include brief (2-3 sentence) rationale alongside non-trivial generated code.

## Git Workflow — User Tests Before Any Commit

- Implement and edit files freely, but do **not** commit or push without the user's explicit go-ahead.
- After implementing a feature, provide: a summary of changes, files modified, testing instructions, and a suggested commit message — for the user to run themselves.
- Exception: if the user explicitly says "commit and push this" (implying they've already tested), proceed directly.
- Never merge branches without explicit approval.

## File Safety — Backups Before Destructive Operations

- Before mass file moves/deletions (3+ files), reorganizing files across directories, or router/config changes affecting multiple imports, create a backup first:
  ```powershell
  mkdir _backups\YYYY-MM-DD_HHMM_brief-description
  Copy-Item -Recurse <affected-path> _backups\YYYY-MM-DD_HHMM_brief-description\
  ```
- Write a short `BACKUP_MANIFEST.md` in that folder (what was backed up, why, how to restore) and get explicit user confirmation before proceeding with the destructive operation.
- Single-file edits under version control don't require this — git itself is the safety net there.

## Canonical File Router

Read the matching file before starting work in that category:

| Trigger | Canonical file to read first |
| --- | --- |
| New/modified API endpoints, views, serializers, URLs, or model changes affecting API contracts | `chat_docs/instructions/API_DOCUMENTATION_WORKFLOW.md` |
| New/modified components, modals, forms, styling, CSS variables/theme | `chat_docs/instructions/DESIGN_SYSTEM.md` |
| Creating, moving, or organizing docs (incl. `PROJECT_HANDOFF.md`) | `chat_docs/instructions/DOCUMENTATION_STRATEGY.md` |
| New test files, test patterns, debugging CI failures | `chat_docs/instructions/TESTING_WORKFLOW.md` (patterns/setup in `TESTING.md`) |
| Debugging dev environment / dark-mode / Docker / server issues | `chat_docs/instructions/TROUBLESHOOTING_GUIDE.md` |
| Responding to PR or code review feedback | `chat_docs/instructions/CODE_REVIEW_PROTOCOL.md` |
| Preparing a version bump / release | `chat_docs/instructions/VERSION_UPDATE_CHECKLIST.md` |

**Note:** `DATABASE_ARCHITECTURE.md`, `IMPLEMENTATION_ROADMAP.md`, and the old "Complete Technical Specification.md" referenced in earlier versions of this file no longer exist in the current canonical set — if you need one of those, ask the user rather than assuming it still exists under that name.

## Self-Check Before Any Edit

- Creating `class XXXView(APIView):` or editing `path('api/...` in `urls.py` → have I read `API_DOCUMENTATION_WORKFLOW.md`?
- Creating/editing a `.vue` file or using `<BaseModal` → have I read `DESIGN_SYSTEM.md`?
- Moving or creating `.md` files under `chat_docs/` → have I read `DOCUMENTATION_STRATEGY.md`?
- Creating `test_*.py` or `*.spec.js` → have I read `TESTING_WORKFLOW.md`?
- About to search/read broadly to understand how something connects to the rest of the codebase → have I checked GitNexus's tools first?
- About to write boilerplate, a docstring, or a summary → could this go to `local-llm` instead?
- About to move/delete 3+ files → have I created a backup?
- About to commit → has the user actually tested this yet?

## Batch File Update Policy

When the same change applies across multiple files in one request, apply it to all of them in a single pass without pausing for per-file confirmation. Summarize the change once at the end, listing affected files.

## Best Practice Behaviors

- Ask clarifying questions (1-3) before generating large code blocks.
- Show targeted diffs/edits rather than reprinting whole files.
- Reuse patterns from canonical docs and existing code instead of inventing new ones.
- Keep rationale for generated code to 2-3 sentences.