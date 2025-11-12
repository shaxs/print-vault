<!--
Last Updated: 2025-11-12
Version: 2.7.0
User: shaxs

Auto-loaded at the start of every Copilot Chat. Includes core AGENTS.md behavior for mandatory file loading.

Changelog:
- v2.7.0 (2025-11-12): Integrated AGENTS.md core behavior - get_feedback loop, self-check questions,
  STOP rules for file edits. Auto-loaded file now enforces canonical file loading without manual attachment.
- v2.6.0 (2025-11-12): Updated to self-serving model - AI uses read_file tool to load canonical files proactively
- v2.5.1 (2025-10-30): Initial structured quick reference
-->

# Print Vault — Copilot Quick Reference (AUTO-LOADED)

## READ FIRST (very short)

- I am a router: I tell the AI which canonical instruction file to request and how to behave.
- Do NOT duplicate long rules here attach the canonical file for the domain.

**USAGE RULES:**

1. **AT START OF EVERY NEW CHAT SESSION OR TIMEOUT RESTART:** Immediately call `get_feedback` before any other action.
2. **DURING ANY WORK:** Call `get_feedback` before starting multi-step tasks, after completing significant work, and before asking follow-up questions.
3. **AFTER EVERY RESPONSE:** Call `get_feedback` at the end of your response to check for new instructions - this creates a continuous feedback loop.
4. **WHEN FEEDBACK IS RECEIVED:** If feedback content is not empty, adjust behavior and call `get_feedback` again after addressing the input.
5. **ON TOOL FAILURES:** If the tool call fails, retry until it succeeds (unless explicit termination given).
6. **No Feedback Received:** If the feedback content is not received and the `get_feedback` times out, invoke the `get_feedback` again. DO NOT END THE CHAT.
7. **TERMINATION ONLY:** Stop calling only when user explicitly says "end", "stop", "terminate", "quit", or "no more interaction needed".

## Non-Negotiables (always enforce these)

- Document API contract changes before committing & pushing (see API_DOCUMENTATION_WORKFLOW.md).
- Use `frontend/src/components/BaseModal.vue` for modal UIs — do not create custom modals (see DESIGN_SYSTEM.md).
- Use CSS variables for colors (never hardcode hex colors) (see DESIGN_SYSTEM.md).
- Dev servers run in external PowerShell; AI must not execute dev server commands and must ask the user to run them.
- Use `docker compose` (space) for production Docker commands (see TROUBLESHOOTING_GUIDE.md).
- Test UI changes in BOTH light and dark modes before PR.
- Include code + docs in the same feature branch/commit for API changes.
- **Do NOT bump versions on every merge** — follow chat_docs/instructions/VERSION_UPDATE_CHECKLIST.md for release cycles.

## Self-Serving Canonical Docs (AI loads these proactively)

**Before any specialized work, AI MUST use `read_file` tool to load canonical instructions:**

- **API work** → Load `chat_docs/instructions/API_DOCUMENTATION_WORKFLOW.md`
- **UI work** → Load `chat_docs/instructions/DESIGN_SYSTEM.md`
- **Documentation** → Load `chat_docs/instructions/DOCUMENTATION_STRATEGY.md`
- **Troubleshooting** → Load `chat_docs/instructions/TROUBLESHOOTING_GUIDE.md`
- **Version bumps** → Load `chat_docs/instructions/VERSION_UPDATE_CHECKLIST.md`

**AI must announce what was loaded and key constraints before proceeding.**

**Fallback**: If `read_file` fails, request manual attachment.

For comprehensive protocol, user can attach: `#file:AGENTS.md`

## Quick Decision Tree (self-serve then act)

- "Implement/modify API" → AI loads API doc, confirms constraints, then implements
- "Create/modify UI" → AI loads DESIGN_SYSTEM.md, provides component references, then implements
- "Documenting/Planning" → AI loads DOCUMENTATION_STRATEGY.md and relevant docs

## Self-Check: Am I About To Do Forbidden Work?

**Ask yourself before EVERY file edit:**

- Am I creating `class XXXView(APIView):` → Did I load API_DOCUMENTATION_WORKFLOW.md?
- Am I creating `<BaseModal` or any component → Did I load DESIGN_SYSTEM.md?
- Am I editing `path('api/...` in urls.py → Did I load API_DOCUMENTATION_WORKFLOW.md?
- Am I modifying a `.vue` file → Did I load DESIGN_SYSTEM.md?
- Am I moving `.md` files in `chat_docs/` → Did I load DOCUMENTATION_STRATEGY.md?

**If NO to canonical file question, STOP IMMEDIATELY and use `read_file` tool to load it.**

## Agent Safety & Behavior (short)

- AI MUST self-serve canonical files using `read_file` tool before specialized work:
  - Announce: "UI Work Detected - Loading canonical instructions..." then show what was loaded
  - If `read_file` fails: "Please attach `#file:chat_docs/instructions/DESIGN_SYSTEM.md`"
- **Dev environment:** Non-Docker bare metal servers run in external PowerShell — user must run these:
  - Django: `python manage.py migrate`, `python manage.py makemigrations`, `python manage.py runserver`
  - Frontend: `npm run dev`, `npm install`
  - Dev server restarts/stops
- **Production environment:** Docker commands (`docker compose up`, `docker compose build`, etc.) can be run by AI
- **All other commands** (git, file operations, etc.) can be run by AI via run_in_terminal tool
- Always include 2–3 sentence rationale with generated code examples (user preference).

## Token Optimization Tips (short)

- Attach only the docs you need; use file + line ranges where useful.
- Ask for outlines first for large features.
- Prefer diffs when modifying existing code.

## File map (canonical docs)

- `chat_docs/instructions/DESIGN_SYSTEM.md`
- `chat_docs/instructions/API_DOCUMENTATION_WORKFLOW.md`
- `chat_docs/instructions/DOCUMENTATION_STRATEGY.md`
- `chat_docs/instructions/EFFICIENT_PROMPTING_GUIDE.md`
- `chat_docs/instructions/TROUBLESHOOTING_GUIDE.md`
- `chat_docs/instructions/VERSION_UPDATE_CHECKLIST.md` (AI checklist for version management)
- `chat_docs/features/VERSIONING.md` (Human reference for versioning strategy)
