<script setup>
/*
 * Library file detail: metadata panel + embedded 3D viewer streaming the
 * real bytes from the share via /api/library/files/{id}/download/ (nothing
 * is copied into app storage). Viewer background preference is a Library-
 * wide localStorage setting — unlike trackers there is no per-entity
 * filament color context to justify a per-record setting here.
 */
import { ref, watch, computed } from 'vue'
import APIService from '@/services/APIService'
import BaseModal from '@/components/BaseModal.vue'
import ModelViewer from '@/components/ModelViewer.vue'

const props = defineProps({
  show: { type: Boolean, required: true },
  fileId: { type: Number, default: null },
  // Root's configured thumbnail_color — keeps the live viewer consistent
  // with the rendered thumbnails.
  renderColor: { type: String, default: '' },
})

const emit = defineEmits(['close', 'deleted'])

const VIEWER_BG_KEY = 'library-viewer-background'

const file = ref(null)
const loading = ref(false)
const error = ref(null)
const viewerBackground = ref(localStorage.getItem(VIEWER_BG_KEY) || 'dark')

watch(
  () => [props.show, props.fileId],
  async ([show, fileId]) => {
    if (!show || !fileId) return
    file.value = null
    error.value = null
    loading.value = true
    try {
      const response = await APIService.getLibraryFile(fileId)
      file.value = response.data
    } catch (err) {
      console.error('Failed to load library file:', err)
      error.value = 'Failed to load file details.'
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

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
        <!-- 3D viewer -->
        <div class="viewer-header">
          <h4>3D Preview</h4>
          <button type="button" class="btn btn-sm btn-secondary" @click="toggleViewerBackground">
            {{ viewerBackground === 'light' ? 'Switch to Dark Background' : 'Switch to Light Background' }}
          </button>
        </div>
        <div class="viewer-wrap">
          <ModelViewer
            :key="`${file.id}-${viewerBackground}-${renderColor}`"
            :url="downloadUrl"
            :format="file.extension"
            :color="renderColor"
            :background="viewerBackground"
          />
        </div>

        <p v-if="previewNotice" class="preview-notice">{{ previewNotice }}</p>

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

.viewer-wrap {
  height: 320px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden;
}

.viewer-wrap :deep(> div),
.viewer-wrap :deep(canvas) {
  width: 100%;
  height: 100%;
}

.section-title {
  margin: 20px 0 8px;
  color: var(--color-heading);
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
