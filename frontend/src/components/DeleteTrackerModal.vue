<script setup>
import { ref, computed } from 'vue'
import BaseModal from './BaseModal.vue'

const props = defineProps({
  isVisible: {
    type: Boolean,
    required: true,
  },
  trackerName: {
    type: String,
    required: true,
  },
  storageType: {
    type: String,
    required: true, // 'link' or 'local'
  },
  fileCount: {
    type: Number,
    default: 0,
  },
  totalStorageUsed: {
    type: Number,
    default: 0, // in bytes
  },
  filesDownloaded: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'delete', 'downloadAndDelete'])

const deleting = ref(false)
const downloading = ref(false)

const hasLocalFiles = computed(() => {
  return props.storageType === 'local' && props.filesDownloaded && props.fileCount > 0
})

const formattedSize = computed(() => {
  const bytes = props.totalStorageUsed
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
})

const handleClose = () => {
  if (!deleting.value && !downloading.value) {
    emit('close')
  }
}

const handleDeleteOnly = () => {
  deleting.value = true
  emit('delete')
}

const handleDownloadAndDelete = () => {
  downloading.value = true
  emit('downloadAndDelete')
}
</script>

<template>
  <BaseModal :show="isVisible" title="Delete Tracker" @close="handleClose">
    <!-- Modal Body -->
    <div class="delete-modal-content">
      <!-- Warning -->
      <div class="warning-box">
        <span class="warning-icon">⚠️</span>
        <div>
          <p class="warning-title">Are you sure you want to delete this tracker?</p>
          <p class="warning-subtitle">This action cannot be undone.</p>
        </div>
      </div>

      <!-- Tracker Info -->
      <div class="info-box">
        <div class="info-row">
          <span class="info-label">Tracker Name:</span>
          <span class="info-value">{{ trackerName }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Files:</span>
          <span class="info-value">{{ fileCount }} file{{ fileCount !== 1 ? 's' : '' }}</span>
        </div>
        <div v-if="hasLocalFiles" class="info-row">
          <span class="info-label">Storage Used:</span>
          <span class="info-value">{{ formattedSize }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Storage Type:</span>
          <span class="info-value">{{
            storageType === 'local' ? 'Local Files' : 'GitHub Links'
          }}</span>
        </div>
      </div>

      <!-- Local Files Warning -->
      <div v-if="hasLocalFiles" class="local-files-box">
        <p>
          <strong>⚠️ Important:</strong> This tracker has {{ fileCount }} file{{
            fileCount !== 1 ? 's' : ''
          }}
          stored locally ({{ formattedSize }}).
        </p>
        <p>
          You can download all files as a ZIP archive before deleting, or delete without
          downloading.
        </p>
      </div>

      <!-- No Local Files Message -->
      <div v-if="!hasLocalFiles && storageType === 'link'" class="info-message">
        <p>This tracker uses GitHub links only. No local files will be deleted.</p>
      </div>

      <!-- Status Messages -->
      <div v-if="downloading" class="status-box">
        <div class="spinner"></div>
        <p>Preparing ZIP download...</p>
      </div>

      <div v-if="deleting" class="status-box">
        <div class="spinner"></div>
        <p>Deleting tracker...</p>
      </div>
    </div>

    <!-- Modal Footer -->
    <template #footer>
      <div v-if="!deleting && !downloading" class="button-group">
        <button @click="handleClose" class="btn btn-secondary">Cancel</button>
        <button @click="handleDeleteOnly" class="btn btn-danger">
          Delete{{ hasLocalFiles ? ' Without Download' : '' }}
        </button>
        <button v-if="hasLocalFiles" @click="handleDownloadAndDelete" class="btn btn-primary">
          Download ZIP & Delete
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<style scoped>
.delete-modal-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.warning-box {
  display: flex;
  gap: 12px;
  padding: 12px;
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 6px;
}

.warning-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.warning-title {
  margin: 0 0 4px 0;
  font-weight: 600;
  color: var(--color-heading);
  font-size: 15px;
}

.warning-subtitle {
  margin: 0;
  color: var(--color-text);
  font-size: 14px;
}

.info-box {
  background-color: var(--color-background-mute);
  border-radius: 6px;
  padding: 12px;
  border: 1px solid var(--color-border);
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-weight: 600;
  color: var(--color-text);
}

.info-value {
  font-weight: 500;
  color: var(--color-heading);
}

.local-files-box {
  padding: 12px;
  background-color: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 6px;
}

.local-files-box p {
  margin: 0 0 8px 0;
  color: var(--color-text);
  font-size: 14px;
  line-height: 1.5;
}

.local-files-box p:last-child {
  margin-bottom: 0;
}

.info-message {
  padding: 12px;
  background-color: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
}

.info-message p {
  margin: 0;
  color: var(--color-text);
  font-size: 14px;
}

.status-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background-color: var(--color-background-mute);
  border-radius: 6px;
}

.status-box p {
  margin: 0;
  color: var(--color-text);
  font-weight: 500;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--vt-c-indigo);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.button-group {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: var(--vt-c-indigo);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--vt-c-indigo-dark);
}

.btn-secondary {
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.btn-secondary:hover:not(:disabled) {
  background-color: var(--color-background-soft);
}

.btn-danger {
  background-color: #dc2626;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background-color: #b91c1c;
}
</style>
