**Last Updated**: 2025-10-28
**Version**: 2.4.1
**User**: shaxs

# Print Vault - Quick Reference

> 📚 **Full guidelines**: `AGENTS.md` | **UI patterns**: `chat_docs/instructions/DESIGN_SYSTEM.md`

---

## ⚠️ Important: Attach Instruction Files Before Proceeding

**Before starting specialized work, always ask the user to attach the relevant instruction file:**

- **API work** → Ask for `chat_docs/instructions/API_DOCUMENTATION_WORKFLOW.md`
- **UI work** → Ask for `chat_docs/instructions/DESIGN_SYSTEM.md`
- **Documentation** → Ask for `chat_docs/instructions/DOCUMENTATION_STRATEGY.md`
- **Troubleshooting** → Ask for `chat_docs/instructions/TROUBLESHOOTING_GUIDE.md`

**If the file is not attached, respond:**

> "To proceed with [API/UI/Documentation] work, please attach `[filename]`. This file contains the required workflow and standards."

**See `AGENTS.md` "AI Agent Behavior" section for complete guidelines.**

---

## 💎 Token Optimization (Get More Value)

**For Humans:**

- **Batch related questions** - Ask about multiple related items in one message
- **Attach files strategically** - Only attach docs you'll actually reference
  - Use `#file:chat_docs/PROJECT_HANDOFF.md` for project context
  - Use `#file:chat_docs/planning/[FEATURE]_IMPLEMENTATION.md` for specific features
- **Start new chats for new topics** - Keep contexts focused and relevant
- **Use specific file references** - `#file:path/to/file.py` instead of "that file we worked on"
- **Reference line numbers** - "Lines 45-60 in UserView.vue" vs "the middle part"

**For AI Assistants - Efficiency Rules:**

1. **Be concise but complete** - Don't waste tokens on fluff
2. **Balance code + explanation** - Provide code examples WITH brief explanations of what changed and why
3. **Reference existing patterns** - Point to similar code instead of recreating
4. **Use diffs for changes** - Show only what changed, not entire files
5. **Consolidate similar changes** - Group related modifications together
6. **Ask clarifying questions early** - Don't generate wrong code that wastes tokens
7. **Reuse code blocks** - Reference previous messages instead of rewriting

**Code Presentation Preference:**

- ✅ Provide code examples WITH short explanations (2-3 sentences)
- ✅ Explain what the code does and why you chose this approach
- ❌ Don't just dump code without context
- ❌ Don't write long essays - keep explanations brief and focused

**Example of preferred format:**

```javascript
// Added email validation using regex pattern
const validateEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

// This ensures emails are properly formatted before submission.
// Pattern matches the validation used in LoginView.vue for consistency.
```

**Examples of Efficient Prompts:**

❌ **Inefficient:**

```
Can you help me with the user profile page? I'm not sure how to start.
I think I need a form. What should I do?
```

_Issues: Vague, multi-turn clarification needed, no context_

✅ **Efficient:**

```
#file:frontend/src/views/UserProfileView.vue
Add email validation to the profile form (lines 45-60).
Should match the pattern in #file:frontend/src/views/LoginView.vue (lines 23-30).
```

_Benefits: Specific location, clear requirement, reference pattern_

---

❌ **Inefficient:**

```
I need to create an API for notifications. Can you walk me through it?
```

_Issues: Too broad, will generate lots of exploratory content_

✅ **Efficient:**

```
Create notification API endpoint:
- GET /api/notifications/ (list with pagination)
- PATCH /api/notifications/{id}/ (mark as read)
- Model: user, message, read_status, timestamp
Follow pattern in #file:backend/reminders/views.py
Document in chat_docs/api/API_REFERENCE_NOTIFICATIONS.md after implementation.
```

_Benefits: Specific requirements, reference pattern, clear scope_

---

❌ **Inefficient:**

```
The modal doesn't look right. Can you fix it?
```

_Issues: No context, requires back-and-forth, AI will guess_

✅ **Efficient:**

```
#file:frontend/src/components/UserSettingsModal.vue
Not using BaseModal.vue. Refactor to use BaseModal pattern from
#file:frontend/src/components/ImportURLsModal.vue (lines 1-50).
Keep existing functionality, just change the modal wrapper.
```

_Benefits: Specific problem, clear solution, reference implementation_

**Token Saving Tips for Complex Features:**

1. **Break into phases:**
   ```
   Phase 1: Just the data model
   Phase 2: API endpoints
   Phase 3: Frontend integration
   ```
2. **Use previous context:**

   ```
   "Using the notification model we just created, now add the API views"
   ```

3. **Reference decisions:**

   ```
   "Same validation pattern as the user profile form"
   ```

4. **Ask for structure first:**
   ```
   "Outline the files I need to change for this feature"
   ```
   Then: "Good, now implement the backend models"

---

## ⚡ Critical Rules (NON-NEGOTIABLE)

1. **APIs**: Update `chat_docs/api/API_REFERENCE_*.md` AFTER testing, BEFORE committing
2. **Modals**: Use `BaseModal.vue` - never create custom modals
3. **Colors**: Use CSS variables ONLY - never hardcode colors
4. **Docker**: Use `docker compose` (space) not `docker-compose` (hyphen)
5. **Dark Mode**: Test in BOTH light and dark modes
6. **Button Order**: Cancel/Secondary left, Primary/Action right
7. **Icons in Buttons**: NEVER use icons in buttons (text only)

## 🏗️ Tech Stack

- **Backend**: Django + Django REST Framework + PostgreSQL (production) / SQLite (dev)
- **Frontend**: Vue.js 3 (Composition API) + Tailwind CSS
- **Database**: PostgreSQL (production), SQLite (development)
- **Deployment**: Docker Compose on Linux server (production only)
- **Development**: Native Python + Node.js (runs in external PowerShell terminals)

## 🖥️ Development Environment

**Dev servers run in PowerShell (OUTSIDE VS Code):**

- Backend: `python manage.py runserver 0.0.0.0:8000`
- Frontend: `npm run dev`

**⚠️ Important for AI:**

- **NEVER** try to execute server commands
- **ALWAYS** ask user to restart/reload servers manually
- Servers run externally so VS Code can be closed while testing

## 📁 File Locations

**Documentation (Root chat_docs/):**

- Project overview: `chat_docs/PROJECT_HANDOFF.md` (START HERE for new chats)
- Print Tracker summary: `chat_docs/COMPLETE_PRINT_TRACKER_DEVELOPMENT_SUMMARY.md`
- Roadmap: `chat_docs/FUTURE_ENHANCEMENTS_TODO.md`
- Testing guide: `chat_docs/TESTING_STRATEGY.md`
- Caching reference: `chat_docs/CACHING_EXPLANATION.md`

**API Documentation (chat_docs/api/):**

- All API references: `chat_docs/api/API_REFERENCE_*.md`
- Inventory API: `chat_docs/api/API_REFERENCE_INVENTORY.md`
- Printers API: `chat_docs/api/API_REFERENCE_PRINTERS.md`
- Projects API: `chat_docs/api/API_REFERENCE_PROJECTS.md`
- Tracker API: `chat_docs/api/API_REFERENCE_TRACKER.md`
- Lookups API: `chat_docs/api/API_REFERENCE_LOOKUPS.md`
- Mods API: `chat_docs/api/API_REFERENCE_MODS.md`
- Reminders API: `chat_docs/api/API_REFERENCE_REMINDERS.md`
- Data Management API: `chat_docs/api/API_REFERENCE_DATA_MANAGEMENT.md`

**Planning Documents (chat_docs/planning/):**

- Feature planning: `chat_docs/planning/*.md`
- Future features: Check `chat_docs/planning/` for proposals

**Code:**

- Base modal: `frontend/src/components/BaseModal.vue`
- Example modal: `frontend/src/components/ImportURLsModal.vue`
- API service: `frontend/src/services/APIService.js`
- Django models: `backend/*/models.py`
- Django views: `backend/*/views.py`

**Configuration:**

- **Production**: `docker-compose.yml` (in root)
- Backend env: `backend/.env`
- Frontend env: `frontend/.env`

**Development:**

- Backend: `python manage.py runserver 0.0.0.0:8000` (PowerShell)
- Frontend: `npm run dev` (PowerShell)
- Database (dev): `data/db.sqlite3`

## 🎯 Quick Decision Tree

**"I need to..."**

- **Understand the project** (new chat)
  → Attach `#file:chat_docs/PROJECT_HANDOFF.md` (this is NOT auto-loaded)

- **Create/modify an API endpoint**
  → Update `chat_docs/api/API_REFERENCE_*.md` AFTER testing, BEFORE committing

- **Create a modal**
  → Use `BaseModal.vue` (see `chat_docs/instructions/DESIGN_SYSTEM.md` examples)

- **Style something**
  → Use CSS variables only (check `chat_docs/instructions/DESIGN_SYSTEM.md`)

- **See what's planned**
  → Check `chat_docs/FUTURE_ENHANCEMENTS_TODO.md`

- **Find a planning document**
  → Look in `chat_docs/planning/`

- **Add a form field**
  → Pre-populate with existing data (see Form Patterns in `chat_docs/instructions/DESIGN_SYSTEM.md`)

- **Run Docker commands**
  → Use `docker compose` (space, not hyphen)

- **Not sure if component exists**
  → Check `frontend/src/components/` before creating new one

## 📚 Documentation Structure

**Root Documentation (`chat_docs/`):**

- `PROJECT_HANDOFF.md` - Comprehensive project overview ⚠️ **Not auto-loaded, attach with #file: in new chats**
- `COMPLETE_PRINT_TRACKER_DEVELOPMENT_SUMMARY.md` - Print Tracker reference
- `FUTURE_ENHANCEMENTS_TODO.md` - Active roadmap and TODOs
- `TESTING_STRATEGY.md` - Testing guidelines
- `CACHING_EXPLANATION.md` - Technical reference for caching

**API Documentation (`chat_docs/api/`):**

- All `API_REFERENCE_*.md` files - Grouped API documentation
- Mandatory to update with API changes

**Planning (`chat_docs/planning/`):**

- Feature proposals and analysis documents
- Detailed implementation docs for complex features

**Other:**

- `AGENTS.md` - Complete development guidelines (attach with `#file:` for detailed work)
- `chat_docs/instructions/DESIGN_SYSTEM.md` - UI/UX patterns (attach with `#file:` for UI work)

## 🤖 For AI Assistants

**Before implementing anything:**

1. **Check if it exists**: Look for similar components/patterns first
2. **API work**: Confirm docs will be updated in `chat_docs/api/` AFTER testing, BEFORE committing
3. **UI work**: Reference `chat_docs/instructions/DESIGN_SYSTEM.md` patterns (ask user to attach with `#file:`)
4. **New to project**: Ask user to attach `chat_docs/PROJECT_HANDOFF.md` with `#file:`
5. **Unsure**: Ask user to attach `AGENTS.md` with `#file:`

**Token Efficiency for AI:**

- Provide code WITH brief explanations (2-3 sentences)
- Use diffs when modifying existing files
- Reference similar implementations instead of writing from scratch
- Ask clarifying questions before generating large code blocks
- Break large features into smaller, focused responses
- Reuse patterns from the codebase

**Server Management (CRITICAL):**

- ❌ **NEVER** try to execute `python manage.py runserver`
- ❌ **NEVER** try to execute `npm run dev`
- ❌ **NEVER** try to restart dev servers
- ✅ **ALWAYS** ask user to manually restart servers in their PowerShell terminals

**When code changes require server restart:**

```
"Changes made to [file]. To see the changes:

Backend changes: Stop Django (Ctrl+C) and restart: python manage.py runserver 0.0.0.0:8000
Frontend changes: Should hot-reload automatically (or restart: npm run dev)
Model changes: Run migrations, then restart Django
"
```

**Response template for API changes:**

> "Before implementing, I need to update `chat_docs/api/API_REFERENCE_[MODULE].md` after the code is stable but before we commit (mandatory requirement). I'll:
>
> 1. Implement and test the endpoint
> 2. Document it with examples
> 3. Commit code + docs together
>
> Shall I proceed?"

## 🚀 Git Workflow

```
1. Create feature branch
2. Implement + test
3. ⛔ Document before committing
4. Commit code + docs together
5. Push feature branch
6. Open PR for review
7. Merge to main after approval
```

## 🔄 Chat History & Knowledge Management

### When to Start a New Chat

**Start new chat when:**

- ✅ Starting a completely different feature
- ✅ Switching between backend and frontend work (different context needed)
- ✅ After 50+ messages (context becomes bloated)
- ✅ When you need to attach different documentation files

**Continue current chat when:**

- ✅ Iterating on the same feature
- ✅ Related bug fixes in the same area
- ✅ Follow-up questions about code just generated

### Managing Feature Continuity (Hybrid Strategy)

**For small features/tactical decisions:**

```
"Add a 'Recent Decisions' section to chat_docs/PROJECT_HANDOFF.md:

## Recent Decisions

### [Feature Name] - [Date]
- Decision 1: [summary]
- Pattern established: [description]
- Key files modified: [list]
- Integration points: [description]
```

**For large/complex features:**

```
"Create chat_docs/planning/[FEATURE]_IMPLEMENTATION.md with:
- Architecture decisions
- Patterns used
- Key files modified
- API endpoints added
- Integration points
- Testing approach
- Future considerations
```

### Starting a New Chat with Context

**For general work:**

```
#file:chat_docs/PROJECT_HANDOFF.md
[Brief description of what you're working on]
```

**For continuing a large feature:**

```
#file:chat_docs/PROJECT_HANDOFF.md
#file:chat_docs/planning/NOTIFICATION_SYSTEM_IMPLEMENTATION.md
Continuing work on notification system - need to add email delivery
```

**For API work:**

```
#file:AGENTS.md
#file:chat_docs/api/API_REFERENCE_NOTIFICATIONS.md
Adding new notification filtering endpoints
```

**For UI work:**

```
#file:chat_docs/instructions/DESIGN_SYSTEM.md
#file:chat_docs/PROJECT_HANDOFF.md
Creating new settings modal
```

### When to Update Documentation

**Update immediately after:**

- ✅ Completing a major milestone
- ✅ Establishing new patterns that others should follow
- ✅ Making architectural decisions
- ✅ Before starting a related feature

**Don't update for:**

- ❌ Every tiny code change (too much overhead)
- ❌ Experimental/temporary code
- ❌ Bug fixes that don't change patterns

### Documentation Update Workflow

**End of feature chat:**

```
"Document our work:

1. Add high-level summary (5 bullets) to chat_docs/PROJECT_HANDOFF.md
   under 'Recent Decisions - [Feature Name]'

2. [If large feature] Create detailed implementation doc at
   chat_docs/planning/[FEATURE]_IMPLEMENTATION.md with:
   - Architecture decisions
   - Code patterns used
   - Integration points
   - Files modified
"
```

**This creates a knowledge base that grows intelligently over time!**

---

## 📖 More Details

See `AGENTS.md` and `chat_docs/instructions/DESIGN_SYSTEM.md` for:

- Complete coding standards
- Token optimization strategies
- Component patterns and examples
- API documentation requirements
- Git workflow details
- Troubleshooting guides
