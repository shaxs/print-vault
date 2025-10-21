<script setup>
import BaseModal from './BaseModal.vue'

defineProps({
  isVisible: {
    type: Boolean,
    required: true,
  },
  totalFiles: {
    type: Number,
    default: 0,
  },
})

// Modal cannot be closed while downloading
const canClose = false
const modalTitle = 'Downloading Files'
</script>

<template>
  <BaseModal :show="isVisible" :title="modalTitle" :can-close="canClose">
    <div class="download-modal-content">
      <!-- Simple downloading message with single spinner -->
      <div class="downloading-section">
        <div class="spinner"></div>
        <div class="message">
          <p class="main-text">Downloading {{ totalFiles }} files from GitHub...</p>
          <p class="subtext">This may take a moment depending on file sizes. Please be patient.</p>
        </div>
      </div>
    </div>
  </BaseModal>
</template>

<style scoped>
/* Modal Content - Simple and Clean */
.download-modal-content {
  padding: 2rem 0;
}

.downloading-section {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 1.5rem;
  background-color: var(--color-background-soft);
  border-radius: 8px;
}

.message {
  flex: 1;
}

.main-text {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text);
  margin-bottom: 0.5rem;
}

.subtext {
  font-size: 14px;
  color: var(--color-text-muted);
}

/* Spinner Animation */
.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--color-border);
  border-top-color: var(--vt-c-indigo);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
