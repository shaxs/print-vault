<!--
Last Updated: 2025-10-30
Version: 2.5.1
User: shaxs

Auto-loaded at the start of every Copilot Chat. Keep small. Attach canonical instruction files for specialized work.
-->

# Print Vault — Copilot Quick Reference (AUTO-LOADED)

## Non-Negotiables (always enforce these)

- Document API contract changes before committing & pushing (see API_DOCUMENTATION_WORKFLOW.md).
- Use `frontend/src/components/BaseModal.vue` for modal UIs — do not create custom modals (see DESIGN_SYSTEM.md).
- Use CSS variables for colors (never hardcode hex colors) (see DESIGN_SYSTEM.md).
- Dev servers run in external PowerShell; AI must not execute dev server commands and must ask the user to run them.
- Use `docker compose` (space) for production Docker commands (see TROUBLESHOOTING_GUIDE.md).
- Test UI changes in BOTH light and dark modes before PR.
- Include code + docs in the same feature branch/commit for API changes.
- **Do NOT bump versions on every merge** — follow chat_docs/instructions/VERSION_UPDATE_CHECKLIST.md for release cycles.

## When to attach canonical docs (minimum attachments)

- API work → `#file:chat_docs/instructions/API_DOCUMENTATION_WORKFLOW.md`
- UI work → `#file:chat_docs/instructions/DESIGN_SYSTEM.md`
- Documentation flow → `#file:chat_docs/instructions/DOCUMENTATION_STRATEGY.md`
- Troubleshooting / ops → `#file:chat_docs/instructions/TROUBLESHOOTING_GUIDE.md`
- Prompt engineering / token optimization → `#file:chat_docs/instructions/EFFICIENT_PROMPTING_GUIDE.md`
- **Preparing release / version bump** → `#file:chat_docs/instructions/VERSION_UPDATE_CHECKLIST.md`

## Quick Decision Tree (attach then act)

- "Implement/modify API" → attach API doc, confirm constraints, then implement.
- "Create/modify UI" → attach DESIGN_SYSTEM.md, provide component references, then implement.
- "Documenting/Planning" → attach DOCUMENTATION_STRATEGY.md and relevant planning doc.

## Agent Safety & Behavior (short)

- If a required canonical file is not attached for specialized work, the AI MUST request it before proceeding:
  - Example: "Please attach `#file:chat_docs/instructions/DESIGN_SYSTEM.md` so I can follow canonical UI rules."
- **Dev server commands** (Django backend, Vite frontend) run in external PowerShell — user must run these:
  - `python manage.py migrate`, `python manage.py makemigrations`, `npm run dev`, server restarts
- **All other commands** (git, docker, npm install, etc.) can be run by AI with user permission via run_in_terminal tool.
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
