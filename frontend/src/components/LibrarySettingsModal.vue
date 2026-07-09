<script setup>
/*
 * Library settings — two-level, single BaseModal:
 *
 *  - LIST screen (default when ≥1 root exists): one row per root (name, path,
 *    last-scan status) with per-row Edit / Remove, an "Add Path" button, and
 *    the global "Purge Deleted Records" maintenance action.
 *  - FORM screen (create or edit): name / path / rescan interval / thumbnail
 *    color, plus (edit mode) the Rescan Now / Regenerate Thumbnails actions.
 *
 * Async jobs are only started here and handed up to LibraryView (via
 * 'job-started') which owns the progress banner — the modal never traps the
 * user. When no root exists yet the modal opens straight on the create form.
 */
import { computed, ref, watch } from 'vue'
import APIService from '@/services/APIService'
import BaseModal from '@/components/BaseModal.vue'

const props = defineProps({
  show: { type: Boolean, required: true },
  roots: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'saved', 'created', 'deleted', 'rescanned', 'job-started'])

const HEX_PATTERN = /^#[0-9a-fA-F]{6}$/
const BLANK_FORM = { name: '', path: '', rescan_interval_hours: null, thumbnail_color: '#94a3b8' }

const screen = ref('list') // 'list' | 'form'
const editingRoot = ref(null) // null on the form screen = create mode
const form = ref({ ...BLANK_FORM })
const saving = ref(false)
const statusMessage = ref('')
const errorMessage = ref('')

const isCreateMode = computed(() => editingRoot.value === null)
const colorValid = computed(() => HEX_PATTERN.test(form.value.thumbnail_color))
const formValid = computed(
  () => form.value.name.trim() && form.value.path.trim() && colorValid.value,
)
const modalTitle = computed(() => {
  if (screen.value === 'list') return 'Library Settings'
  return isCreateMode.value ? 'Add Library Root' : 'Edit Library Root'
})

watch(
  () => props.show,
  (show) => {
    if (!show) return
    statusMessage.value = ''
    errorMessage.value = ''
    if (props.roots.length) {
      screen.value = 'list'
    } else {
      openForm(null) // no roots yet → straight to create
    }
  },
)

function openForm(root) {
  editingRoot.value = root
  statusMessage.value = ''
  errorMessage.value = ''
  form.value = root
    ? {
        name: root.name,
        path: root.path,
        rescan_interval_hours: root.rescan_interval_hours,
        thumbnail_color: root.thumbnail_color || '#94a3b8',
      }
    : { ...BLANK_FORM }
  screen.value = 'form'
}

function backToList() {
  statusMessage.value = ''
  errorMessage.value = ''
  screen.value = 'list'
}

function payload() {
  return {
    name: form.value.name.trim(),
    path: form.value.path.trim(),
    rescan_interval_hours: form.value.rescan_interval_hours || null,
    thumbnail_color: form.value.thumbnail_color,
  }
}

function readApiError(err, fallback) {
  const data = err.response?.data
  if (data && typeof data === 'object') {
    const first = Object.values(data)[0]
    if (Array.isArray(first)) return first[0]
    if (typeof first === 'string') return first
  }
  return fallback
}

function scanStatusLabel(root) {
  return { idle: 'Never scanned', running: 'Scanning…', success: 'Scanned', error: 'Scan failed' }[
    root.last_scan_status
  ] || root.last_scan_status
}

// "Next scan in ~5 h" from the periodic schedule's next-run time. Empty when
// the root has no rescan interval (manual-only) — nothing to show.
function nextScanLabel(root) {
  if (!root.next_scan_at) return ''
  const diffMs = new Date(root.next_scan_at).getTime() - Date.now()
  if (diffMs <= 0) return 'Next scan due now'
  const hours = diffMs / 3_600_000
  if (hours < 1) {
    const mins = Math.max(1, Math.round(diffMs / 60_000))
    return `Next scan in ${mins} min`
  }
  if (hours < 24) return `Next scan in ${Math.round(hours)} h`
  const days = Math.round(hours / 24)
  return `Next scan in ${days} day${days === 1 ? '' : 's'}`
}

// "Last scan: 12 new · 3 updated · 1 removed" from the most recent directory
// scan's result counts. Empty before the first scan.
function lastScanLabel(root) {
  const s = root.last_scan
  if (!s) return ''
  if (s.status === 'error') return 'Last scan failed'
  return `Last scan: ${s.files_new} new · ${s.files_updated} updated · ${s.files_deleted} removed`
}

async function handleSave() {
  errorMessage.value = ''
  saving.value = true
  try {
    if (isCreateMode.value) {
      const response = await APIService.createLibraryRoot(payload())
      emit('created', response.data)
      editingRoot.value = response.data
    } else {
      const response = await APIService.updateLibraryRoot(editingRoot.value.id, payload())
      emit('saved', response.data)
      editingRoot.value = response.data
    }
    statusMessage.value = 'Saved.'
    screen.value = 'list'
  } catch (err) {
    console.error('Failed to save library settings:', err)
    errorMessage.value = readApiError(err, 'Failed to save settings.')
  } finally {
    saving.value = false
  }
}

async function confirmDelete(root) {
  if (
    !confirm(
      `Remove the library root "${root.name}"? All indexed records for it are deleted ` +
        `(the real files on the share are never touched).`,
    )
  )
    return
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    await APIService.deleteLibraryRoot(root.id)
    emit('deleted', root.id)
    statusMessage.value = `Removed "${root.name}".`
  } catch (err) {
    console.error('Failed to remove root:', err)
    errorMessage.value =
      err.response?.status === 409
        ? 'A scan is in progress for this root — wait for it to finish before removing it.'
        : readApiError(err, 'Failed to remove the root.')
  }
}

// ---- Maintenance actions (edit-mode form screen) ----

async function startJob(kind) {
  errorMessage.value = ''
  statusMessage.value = ''
  // Persist any pending edits first so the job uses the latest settings.
  saving.value = true
  try {
    const response = await APIService.updateLibraryRoot(editingRoot.value.id, payload())
    emit('saved', response.data)
    editingRoot.value = response.data
  } catch (err) {
    saving.value = false
    errorMessage.value = readApiError(err, 'Failed to save settings.')
    return
  }

  try {
    const start =
      kind === 'rescan'
        ? APIService.rescanLibraryRoot(editingRoot.value.id)
        : APIService.regenerateLibraryThumbnails(editingRoot.value.id)
    const response = await start
    emit('job-started', response.data)
    statusMessage.value =
      kind === 'rescan'
        ? 'Scan started — progress shows on the Library screen.'
        : 'Thumbnail regeneration started — progress shows on the Library screen.'
  } catch (err) {
    console.error(`Failed to start ${kind}:`, err)
    errorMessage.value =
      err.response?.status === 409
        ? 'A scan is already in progress — try again when it finishes.'
        : `Failed to start ${kind === 'rescan' ? 'scan' : 'regeneration'}.`
  } finally {
    saving.value = false
  }
}

async function handlePurge() {
  if (
    !confirm(
      'Permanently delete every record currently marked as deleted? ' +
        'This cannot be undone (the real files on the share are never touched).',
    )
  )
    return
  errorMessage.value = ''
  try {
    const response = await APIService.purgeLibraryDeleted()
    const { files_purged, folders_purged } = response.data
    statusMessage.value = `Purged ${files_purged} deleted file record(s) and ${folders_purged} folder record(s).`
    emit('rescanned') // tree + contents need a refresh
  } catch (err) {
    console.error('Purge failed:', err)
    errorMessage.value = 'Failed to purge deleted records.'
  }
}
</script>

<template>
  <BaseModal :show="show" :title="modalTitle" @close="emit('close')">
    <!-- LIST SCREEN -->
    <template v-if="screen === 'list'">
      <div class="root-list">
        <div v-for="root in roots" :key="root.id" class="root-row">
          <div class="root-info">
            <div class="root-name">{{ root.name }}</div>
            <div class="root-path">{{ root.path }}</div>
            <div class="root-status">
              <span :class="['status-pill', 'status-' + root.last_scan_status]">
                {{ scanStatusLabel(root) }}
              </span>
              <span v-if="!root.enabled" class="status-pill status-disabled">disabled</span>
            </div>
            <div v-if="lastScanLabel(root)" class="root-meta">{{ lastScanLabel(root) }}</div>
            <div v-if="nextScanLabel(root)" class="root-meta">{{ nextScanLabel(root) }}</div>
          </div>
          <div class="root-actions">
            <button class="btn btn-sm btn-secondary" @click="openForm(root)">Edit</button>
            <button class="btn btn-sm btn-danger" @click="confirmDelete(root)">Remove</button>
          </div>
        </div>
        <p v-if="!roots.length" class="field-hint">No library roots yet.</p>
      </div>

      <div class="list-actions">
        <button class="btn btn-sm btn-primary" @click="openForm(null)">Add Path</button>
        <button class="btn btn-sm btn-danger" @click="handlePurge">Purge Deleted Records</button>
      </div>

      <p v-if="statusMessage" class="status-message">{{ statusMessage }}</p>
      <p v-if="errorMessage" class="field-error">{{ errorMessage }}</p>
    </template>

    <!-- FORM SCREEN (create / edit) -->
    <template v-else>
      <a v-if="roots.length" href="#" class="back-link" @click.prevent="backToList">
        ← Back to roots
      </a>

      <div class="form-group">
        <label for="library-root-name">Name</label>
        <input
          id="library-root-name"
          type="text"
          v-model="form.name"
          :disabled="saving"
          placeholder="e.g. NAS"
        />
      </div>

      <div class="form-group">
        <label for="library-root-path">Folder path</label>
        <input
          id="library-root-path"
          type="text"
          v-model="form.path"
          :disabled="saving"
          spellcheck="false"
          placeholder="e.g. /mnt/nas/stls"
        />
        <p class="field-hint">
          Absolute path as this server sees it (the bind-mount point inside the container in
          Docker). Changing it takes effect on the next scan.
        </p>
      </div>

      <div class="form-group">
        <label for="library-rescan-interval">Automatic rescan interval (hours)</label>
        <input
          id="library-rescan-interval"
          type="number"
          min="1"
          v-model.number="form.rescan_interval_hours"
          :disabled="saving"
          placeholder="Leave empty for manual rescans only"
        />
      </div>

      <div class="form-group">
        <label for="library-thumb-color">Thumbnail &amp; viewer color</label>
        <div class="color-row">
          <input
            id="library-thumb-color"
            type="color"
            v-model="form.thumbnail_color"
            :disabled="saving"
            class="color-input"
          />
          <input
            type="text"
            v-model="form.thumbnail_color"
            :disabled="saving"
            maxlength="7"
            spellcheck="false"
            class="hex-input"
          />
        </div>
        <p class="field-hint">Existing thumbnails keep their old color until regenerated (below).</p>
        <p v-if="!colorValid" class="field-error">Enter a hex color like #94a3b8.</p>
      </div>

      <template v-if="!isCreateMode">
        <h4 class="section-title">Maintenance</h4>
        <div class="maintenance-actions">
          <button class="btn btn-sm btn-primary" :disabled="saving" @click="startJob('rescan')">
            Rescan Now
          </button>
          <button
            class="btn btn-sm btn-secondary"
            :disabled="saving || !colorValid"
            @click="startJob('regenerate')"
          >
            Regenerate Thumbnails
          </button>
        </div>
      </template>

      <p v-if="statusMessage" class="status-message">{{ statusMessage }}</p>
      <p v-if="errorMessage" class="field-error">{{ errorMessage }}</p>
    </template>

    <template #footer>
      <button @click="emit('close')" class="btn btn-secondary">Close</button>
      <button
        v-if="screen === 'form'"
        @click="handleSave"
        class="btn btn-primary"
        :disabled="saving || !formValid"
      >
        {{ isCreateMode ? 'Create Library' : 'Save' }}
      </button>
    </template>
  </BaseModal>
</template>

<style scoped>
/* ---- Root list screen ---- */
.root-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.root-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background-color: var(--color-background);
}

.root-name {
  color: var(--color-heading);
  font-weight: 600;
}

.root-path {
  color: var(--color-text);
  opacity: 0.75;
  font-family: monospace;
  font-size: 0.85rem;
  word-break: break-all;
}

.root-status {
  margin-top: 4px;
  display: flex;
  gap: 6px;
}

.root-meta {
  margin-top: 4px;
  color: var(--color-text);
  opacity: 0.75;
  font-size: 0.8rem;
}

.status-pill {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 0.7rem;
  text-transform: uppercase;
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.status-success {
  background-color: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.3);
}

.status-running {
  background-color: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
}

.status-error {
  background-color: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
}

.status-disabled {
  opacity: 0.7;
}

.root-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.list-actions {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.back-link {
  display: inline-block;
  margin-bottom: 12px;
  color: var(--color-text);
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

/* ---- Form screen ---- */
.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  color: var(--color-heading);
  font-weight: 600;
}

.form-group input[type='text'],
.form-group input[type='number'] {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-sizing: border-box;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-blue);
  box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.15);
}

.color-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.color-input {
  width: 48px;
  height: 36px;
  padding: 2px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  cursor: pointer;
}

.hex-input {
  width: 110px;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-family: monospace;
}

.hex-input:focus {
  outline: none;
  border-color: var(--color-blue);
  box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.15);
}

.section-title {
  margin: 20px 0 10px;
  color: var(--color-heading);
}

.maintenance-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.field-hint {
  margin: 8px 0 0;
  color: var(--color-text);
  opacity: 0.75;
  font-size: 0.85rem;
}

.field-error {
  margin: 8px 0 0;
  color: var(--color-red);
  font-size: 0.85rem;
}

.status-message {
  margin: 12px 0 0;
  padding: 8px 12px;
  background-color: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 4px;
  color: var(--color-text);
}
</style>
