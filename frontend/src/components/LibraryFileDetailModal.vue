<script setup>
/*
 * Library file detail: metadata panel + embedded 3D viewer streaming the
 * real bytes from the share via /api/library/files/{id}/download/ (nothing
 * is copied into app storage). Viewer background preference is a Library-
 * wide localStorage setting — unlike trackers there is no per-entity
 * filament color context to justify a per-record setting here.
 */
import { ref, watch, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import APIService from '@/services/APIService'
import BaseModal from '@/components/BaseModal.vue'
import ModelViewer from '@/components/ModelViewer.vue'
import TagInput from '@/components/TagInput.vue'

const props = defineProps({
  show: { type: Boolean, required: true },
  fileId: { type: Number, default: null },
  // Root's configured thumbnail_color — keeps the live viewer consistent
  // with the rendered thumbnails.
  renderColor: { type: String, default: '' },
})

const emit = defineEmits(['close', 'deleted', 'favorite-changed', 'tags-changed'])

const VIEWER_BG_KEY = 'library-viewer-background'

const file = ref(null)
const loading = ref(false)
const error = ref(null)
const viewerBackground = ref(localStorage.getItem(VIEWER_BG_KEY) || 'dark')
const viewerFullscreen = ref(false)

// Notes editing — a user-writable field on a library file.
const notesDraft = ref('')
const notesSaving = ref(false)
const notesError = ref(null)
const notesJustSaved = ref(false)
const notesDirty = computed(() => notesDraft.value !== (file.value?.notes || ''))

// Tags — persisted immediately on add/remove (no explicit save, unlike notes).
const fileTags = ref([])
const tagsError = ref(null)

// Favorite — a one-click toggle, persisted immediately.
const isFavorite = ref(false)
const favoriteSaving = ref(false)

// Bumped on every file switch (open/close/change). Each async operation below
// captures the id it was started under and checks it's still current before
// applying its result — otherwise a slow response for a file the user has
// since navigated away from could land AFTER a newer load/save and silently
// overwrite what's now displayed for a different file.
let requestId = 0

watch(
  () => [props.show, props.fileId],
  async ([show, fileId]) => {
    // Leaving fullscreen whenever the modal is (re)opened or closed keeps the
    // fixed overlay from lingering across file switches.
    viewerFullscreen.value = false
    if (!show || !fileId) return
    const myRequestId = ++requestId
    file.value = null
    error.value = null
    notesError.value = null
    notesJustSaved.value = false
    tagsError.value = null
    loading.value = true
    try {
      const response = await APIService.getLibraryFile(fileId)
      if (myRequestId !== requestId) return // superseded by a later file switch
      file.value = response.data
      notesDraft.value = response.data.notes || ''
      fileTags.value = response.data.tags || []
      isFavorite.value = !!response.data.is_favorite
    } catch (err) {
      if (myRequestId !== requestId) return
      console.error('Failed to load library file:', err)
      error.value = 'Failed to load file details.'
    } finally {
      if (myRequestId === requestId) loading.value = false
    }
  },
  { immediate: true },
)

async function saveNotes() {
  if (!file.value || notesSaving.value) return
  const myRequestId = requestId
  notesSaving.value = true
  notesError.value = null
  notesJustSaved.value = false
  try {
    const response = await APIService.updateLibraryFile(file.value.id, { notes: notesDraft.value })
    if (myRequestId !== requestId) return // modal moved to a different file meanwhile
    file.value.notes = response.data.notes
    notesDraft.value = response.data.notes
    notesJustSaved.value = true
  } catch (err) {
    if (myRequestId !== requestId) return
    console.error('Failed to save notes:', err)
    notesError.value = 'Failed to save notes.'
  } finally {
    if (myRequestId === requestId) notesSaving.value = false
  }
}

// Separate from `requestId` (which only changes on a file switch): tracks the
// latest of possibly several rapid-fire saves on the SAME file (e.g. quickly
// adding two tags in a row), whose responses could resolve out of order. Only
// the response matching the most recently STARTED call is applied locally —
// an older response landing after a newer one must not roll the tags back.
let tagsSeq = 0

async function saveTags(newTags) {
  if (!file.value) return
  const myRequestId = requestId
  const mySeq = ++tagsSeq
  const savedFileId = file.value.id
  const previous = fileTags.value
  fileTags.value = newTags // optimistic
  tagsError.value = null
  try {
    const response = await APIService.updateLibraryFile(savedFileId, {
      tag_ids: newTags.map((t) => t.id),
    })
    // Tell the library to refresh the left-pane tag browser regardless of
    // whether the modal has since moved on — the save itself landed on the
    // right file server-side, so the filter list must still pick it up.
    emit('tags-changed', { id: savedFileId, tags: response.data.tags })
    if (myRequestId !== requestId || mySeq !== tagsSeq) return // superseded
    fileTags.value = response.data.tags
    file.value.tags = response.data.tags
  } catch (err) {
    if (myRequestId !== requestId || mySeq !== tagsSeq) return
    console.error('Failed to save tags:', err)
    fileTags.value = previous // roll back
    tagsError.value = 'Failed to update tags.'
  }
}

async function toggleFavorite() {
  if (!file.value || favoriteSaving.value) return
  const myRequestId = requestId
  const savedFileId = file.value.id
  const next = !isFavorite.value
  isFavorite.value = next // optimistic
  favoriteSaving.value = true
  try {
    const response = await APIService.updateLibraryFile(savedFileId, { is_favorite: next })
    // Let the browser sync the row's star without a refetch, regardless of
    // whether the modal has since moved on — the save landed on the right file.
    emit('favorite-changed', { id: savedFileId, is_favorite: response.data.is_favorite })
    if (myRequestId !== requestId) return // modal moved to a different file meanwhile
    isFavorite.value = response.data.is_favorite
    file.value.is_favorite = response.data.is_favorite
  } catch (err) {
    if (myRequestId !== requestId) return
    console.error('Failed to update favorite:', err)
    isFavorite.value = !next // roll back
  } finally {
    if (myRequestId === requestId) favoriteSaving.value = false
  }
}

function toggleFullscreen() {
  viewerFullscreen.value = !viewerFullscreen.value
  // The viewer wrapper resizes via CSS only; nudge the ModelViewer's existing
  // window-resize handler so the WebGL canvas re-fits the new dimensions
  // (avoids a remount + model re-download).
  nextTick(() => window.dispatchEvent(new Event('resize')))
}

// ESC exits fullscreen first (and is swallowed) so it doesn't also close the
// whole modal via BaseModal's own ESC handler.
function handleKeydown(event) {
  if (event.key === 'Escape' && viewerFullscreen.value) {
    event.stopPropagation()
    event.preventDefault()
    toggleFullscreen()
  }
}
onMounted(() => document.addEventListener('keydown', handleKeydown, true))
onBeforeUnmount(() => document.removeEventListener('keydown', handleKeydown, true))

const downloadUrl = computed(() =>
  file.value ? APIService.getLibraryFileDownloadUrl(file.value.id) : '',
)

const boundingBox = computed(() => {
  const f = file.value
  if (!f || f.bounding_box_x == null) return null
  const fmt = (v) => (Math.round(v * 10) / 10).toFixed(1)
  return `${fmt(f.bounding_box_x)} × ${fmt(f.bounding_box_y)} × ${fmt(f.bounding_box_z)} mm`
})

const slicerLabel = computed(() => {
  const meta = file.value?.embedded_metadata || {}
  if (!meta.slicer_name) return null
  return meta.slicer_version ? `${meta.slicer_name} ${meta.slicer_version}` : meta.slicer_name
})

const hasEmbeddedMetadata = computed(
  () => Object.keys(file.value?.embedded_metadata || {}).length > 0,
)

// Explains a missing thumbnail (the grid/list preview image). The live 3D
// viewer above uses a different, browser-side loader, so it may still render
// even when no thumbnail could be generated during scanning.
const PREVIEW_NOTICES = {
  too_large: 'No thumbnail image was generated — this file exceeds the preview-render size limit.',
  unrenderable: 'No thumbnail image was generated — the mesh could not be read for a preview.',
  pending: 'This file has not been processed for a preview yet.',
}
const previewNotice = computed(() => {
  const f = file.value
  // A file that already has a thumbnail needs no explanation — even if its
  // thumbnail_status is a stale 'pending' (e.g. it was scanned before the
  // field existed and hasn't been reclassified by a regeneration yet).
  if (!f || f.thumbnail) return null
  const s = f.thumbnail_status
  return s && s !== 'rendered' ? PREVIEW_NOTICES[s] || null : null
})

function toggleViewerBackground() {
  viewerBackground.value = viewerBackground.value === 'light' ? 'dark' : 'light'
  localStorage.setItem(VIEWER_BG_KEY, viewerBackground.value)
}

function formatSize(bytes) {
  if (bytes == null) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : ''
}

async function handlePermanentDelete() {
  if (!confirm(`Permanently delete the record for "${file.value.filename}"? The real file on the share is never touched.`)) return
  try {
    await APIService.deleteLibraryFile(file.value.id)
    emit('deleted', file.value.id)
  } catch (err) {
    console.error('Failed to delete file record:', err)
    alert(err.response?.data?.error || 'Failed to delete the file record.')
  }
}
</script>

<template>
  <div class="library-file-modal">
    <BaseModal :show="show" :title="file?.filename || 'File Details'" @close="emit('close')">
      <div v-if="loading" class="modal-state">Loading…</div>
      <div v-else-if="error" class="modal-state modal-error">{{ error }}</div>

      <template v-else-if="file">
        <!-- Favorite toggle -->
        <div class="file-actions">
          <button
            type="button"
            class="star-toggle"
            :class="{ active: isFavorite }"
            :disabled="favoriteSaving"
            :title="isFavorite ? 'Remove from favorites' : 'Add to favorites'"
            @click="toggleFavorite"
          >
            <span class="star-glyph">{{ isFavorite ? '★' : '☆' }}</span>
            {{ isFavorite ? 'Favorited' : 'Favorite' }}
          </button>
        </div>

        <!-- 3D viewer -->
        <div class="viewer-header">
          <h4>3D Preview</h4>
          <div class="viewer-actions">
            <button type="button" class="btn btn-sm btn-secondary" @click="toggleViewerBackground">
              {{ viewerBackground === 'light' ? 'Switch to Dark Background' : 'Switch to Light Background' }}
            </button>
            <button type="button" class="btn btn-sm btn-secondary" @click="toggleFullscreen">
              Fullscreen
            </button>
          </div>
        </div>
        <div class="viewer-wrap" :class="{ 'is-fullscreen': viewerFullscreen }">
          <div v-if="viewerFullscreen" class="viewer-fullscreen-bar">
            <button type="button" class="btn btn-sm btn-secondary" @click="toggleViewerBackground">
              {{ viewerBackground === 'light' ? 'Switch to Dark Background' : 'Switch to Light Background' }}
            </button>
            <button type="button" class="btn btn-sm btn-secondary" @click="toggleFullscreen">
              Exit Fullscreen
            </button>
          </div>
          <ModelViewer
            :key="`${file.id}-${viewerBackground}-${renderColor}`"
            :url="downloadUrl"
            :format="file.extension"
            :color="renderColor"
            :background="viewerBackground"
          />
        </div>

        <p v-if="previewNotice" class="preview-notice">{{ previewNotice }}</p>

        <!-- Notes -->
        <div class="notes-header">
          <h4 class="section-title">Notes</h4>
          <span v-if="notesJustSaved && !notesDirty" class="notes-saved">Saved</span>
        </div>
        <textarea
          v-model="notesDraft"
          class="notes-input"
          rows="3"
          placeholder="Add notes about this file… (searchable)"
          spellcheck="true"
        ></textarea>
        <div class="notes-actions">
          <span v-if="notesError" class="notes-error">{{ notesError }}</span>
          <button
            type="button"
            class="btn btn-sm btn-primary"
            :disabled="!notesDirty || notesSaving"
            @click="saveNotes"
          >
            {{ notesSaving ? 'Saving…' : 'Save Notes' }}
          </button>
        </div>

        <!-- Tags (persist immediately on add/remove) -->
        <h4 class="section-title">Tags</h4>
        <TagInput
          :model-value="fileTags"
          placeholder="Add tags… (type to search or create)"
          @update:model-value="saveTags"
        />
        <p v-if="tagsError" class="notes-error">{{ tagsError }}</p>

        <!-- File metadata -->
        <h4 class="section-title">Details</h4>
        <dl class="meta-grid">
          <dt>Path</dt>
          <dd class="meta-path">{{ file.relative_path }}</dd>
          <dt>Size</dt>
          <dd>{{ formatSize(file.size_bytes) }}</dd>
          <dt>Modified</dt>
          <dd>{{ formatDate(file.modified_time) }}</dd>
          <dt v-if="boundingBox">Dimensions</dt>
          <dd v-if="boundingBox">{{ boundingBox }}</dd>
          <dt v-if="file.sha256_hash">SHA-256</dt>
          <dd v-if="file.sha256_hash" class="meta-hash" :title="file.sha256_hash">
            {{ file.sha256_hash.slice(0, 16) }}…
          </dd>
        </dl>

        <!-- Embedded 3MF slicer metadata -->
        <template v-if="hasEmbeddedMetadata">
          <h4 class="section-title">Slicer Metadata</h4>
          <dl class="meta-grid">
            <dt v-if="slicerLabel">Slicer</dt>
            <dd v-if="slicerLabel">{{ slicerLabel }}</dd>
            <dt v-if="file.embedded_metadata.printer_profile">Printer Profile</dt>
            <dd v-if="file.embedded_metadata.printer_profile">
              {{ file.embedded_metadata.printer_profile }}
            </dd>
            <dt v-if="file.embedded_metadata.print_profile">Print Profile</dt>
            <dd v-if="file.embedded_metadata.print_profile">
              {{ file.embedded_metadata.print_profile }}
            </dd>
            <dt v-if="file.embedded_metadata.layer_height">Layer Height</dt>
            <dd v-if="file.embedded_metadata.layer_height">
              {{ file.embedded_metadata.layer_height }} mm
            </dd>
            <dt v-if="file.embedded_metadata.nozzle_diameter">Nozzle</dt>
            <dd v-if="file.embedded_metadata.nozzle_diameter">
              {{ file.embedded_metadata.nozzle_diameter }} mm
            </dd>
            <dt v-if="file.embedded_metadata.filaments?.length">Filaments</dt>
            <dd v-if="file.embedded_metadata.filaments?.length">
              <div
                v-for="(filament, index) in file.embedded_metadata.filaments"
                :key="index"
                class="filament-row"
              >
                <span
                  v-if="filament.color"
                  class="color-swatch"
                  :style="{ backgroundColor: filament.color }"
                ></span>
                <span>{{ [filament.name, filament.type].filter(Boolean).join(' — ') }}</span>
              </div>
            </dd>
            <dt v-if="file.embedded_metadata.designer">Designer</dt>
            <dd v-if="file.embedded_metadata.designer">{{ file.embedded_metadata.designer }}</dd>
          </dl>
        </template>
      </template>

      <template #footer>
        <button @click="emit('close')" class="btn btn-secondary">Close</button>
        <button
          v-if="file && file.status === 'deleted'"
          @click="handlePermanentDelete"
          class="btn btn-danger"
        >
          Delete Permanently
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
/* Widen the standard modal for the 3D viewer without forking BaseModal */
.library-file-modal :deep(.modal-container) {
  max-width: 720px;
}

.modal-state {
  padding: 24px 0;
  text-align: center;
  color: var(--color-text-muted, var(--color-text));
}

.modal-error {
  color: var(--color-text);
}

.file-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}

/* Amber star favorite toggle — matches the app's existing favorite convention
   (Material blueprint favorites use the same #f59e0b star). */
.star-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.9rem;
  cursor: pointer;
}

.star-toggle:hover {
  border-color: var(--color-border-hover, var(--color-border));
}

.star-toggle.active {
  border-color: #f59e0b;
  color: #f59e0b;
}

.star-toggle .star-glyph {
  color: #f59e0b;
  font-size: 1.05rem;
  line-height: 1;
}

.star-toggle:disabled {
  opacity: 0.6;
  cursor: default;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.viewer-header h4 {
  margin: 0;
  color: var(--color-heading);
}

.viewer-actions {
  display: flex;
  gap: 8px;
}

.viewer-wrap {
  position: relative;
  height: 320px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden;
}

/* Fullscreen: lift the viewer out to a fixed, full-viewport overlay. Sits
   above BaseModal (whose overlay is ~1000) so the model fills the screen. */
.viewer-wrap.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 3000;
  height: 100vh;
  width: 100vw;
  border: none;
  border-radius: 0;
  background-color: var(--color-background);
}

.viewer-fullscreen-bar {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 1;
  display: flex;
  gap: 8px;
}

.viewer-wrap :deep(canvas) {
  width: 100%;
  height: 100%;
}

.viewer-wrap :deep(.model-viewer-wrapper) {
  width: 100%;
  height: 100%;
}

.section-title {
  margin: 20px 0 8px;
  color: var(--color-heading);
}

.notes-header {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.notes-saved {
  color: var(--color-text-muted, var(--color-text));
  font-size: 0.85rem;
}

.notes-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-sizing: border-box;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
}

.notes-input:focus {
  outline: none;
  border-color: var(--color-blue);
  box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.15);
}

.notes-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.notes-error {
  color: var(--color-text);
  font-size: 0.85rem;
}

.preview-notice {
  margin: 12px 0 0;
  padding: 8px 12px;
  background-color: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 4px;
  color: var(--color-text);
  font-size: 0.9rem;
}

.meta-grid {
  display: grid;
  grid-template-columns: 140px 1fr;
  row-gap: 6px;
  column-gap: 12px;
  margin: 0;
}

.meta-grid dt {
  color: var(--color-text-muted, var(--color-text));
  font-weight: 600;
}

.meta-grid dd {
  margin: 0;
  color: var(--color-text);
  word-break: break-word;
}

.meta-hash {
  font-family: monospace;
}

.meta-path {
  font-family: monospace;
  font-size: 0.9em;
}

.filament-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.color-swatch {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  border: 1px solid var(--color-border);
  flex-shrink: 0;
}
</style>
