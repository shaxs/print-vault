<script setup>
import { watch } from 'vue'

const props = defineProps({
  show: { type: Boolean, required: true },
  title: { type: String, required: true },
})

const emit = defineEmits(['close'])

// Handle overlay click to close modal
// Use mousedown instead of click to detect when drag starts outside modal
function handleOverlayClick(event) {
  // Only close if the click started and ended on the overlay (not dragging from inside modal)
  if (event.target.classList.contains('modal-overlay')) {
    emit('close')
  }
}

watch(
  () => props.show,
  (newValue) => {
    const handleKeydown = (event) => {
      if (event.key === 'Escape') {
        emit('close')
      }
    }

    if (newValue) {
      window.addEventListener('keydown', handleKeydown)
    } else {
      window.removeEventListener('keydown', handleKeydown)
    }
  },
)
</script>

<template>
  <div v-if="show" class="modal-overlay" @mousedown="handleOverlayClick">
    <div class="modal-container" @click.stop @mousedown.stop>
      <div class="modal-header">
        <h3>{{ title }}</h3>
        <button @click="emit('close')" class="close-button">&times;</button>
      </div>
      <div class="modal-body">
        <slot></slot>
      </div>
      <div class="modal-footer">
        <slot name="footer"></slot>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-container {
  background-color: var(--color-background-soft);
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  border: 1px solid var(--color-border); /* Added border for better contrast */
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid var(--color-border);
}
.modal-header h3 {
  color: var(--color-heading);
  margin: 0;
  font-size: 1.25rem;
}
.close-button {
  background: none;
  border: none;
  font-size: 2rem;
  color: var(--color-text);
  cursor: pointer;
}
.modal-body {
  padding: 20px;
  overflow-y: auto;
}
.modal-footer {
  padding: 15px 20px;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
