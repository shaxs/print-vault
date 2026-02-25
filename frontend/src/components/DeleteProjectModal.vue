<script setup>
import { ref, computed } from 'vue'
import BaseModal from './BaseModal.vue'

const props = defineProps({
  show: {
    type: Boolean,
    required: true,
  },
  projectName: {
    type: String,
    required: true,
  },
  projectStatus: {
    type: String,
    required: true,
  },
  linkedBOMCount: {
    type: Number,
    default: 0,
  },
})

const emit = defineEmits(['close', 'confirm'])

const BOM_ACTIVE_STATUSES = ['Planning', 'In Progress', 'On Hold']
const returnInventory = ref(true)

// Show the inventory option only when there are linked items and project isn't cancelled
// (cancelled projects already had inventory restored)
const showInventoryOption = computed(() => {
  return props.linkedBOMCount > 0 && props.projectStatus !== 'Canceled'
})

const isCompleted = computed(() => props.projectStatus === 'Completed')
const isActive = computed(() => BOM_ACTIVE_STATUSES.includes(props.projectStatus))

const itemWord = computed(() =>
  props.linkedBOMCount === 1 ? 'item' : 'items',
)

const handleConfirm = () => {
  emit('confirm', showInventoryOption.value ? returnInventory.value : false)
}
</script>

<template>
  <BaseModal :show="show" title="Delete Project" @close="emit('close')">
    <div class="delete-modal-content">
      <!-- Warning -->
      <div class="warning-box">
        <span class="warning-icon">⚠️</span>
        <div>
          <p class="warning-title">Delete "{{ projectName }}"?</p>
          <p class="warning-subtitle">This action cannot be undone.</p>
        </div>
      </div>

      <!-- Inventory return option (omitted for Cancelled projects) -->
      <div v-if="showInventoryOption" class="inventory-option-box">
        <label class="checkbox-label">
          <input
            v-model="returnInventory"
            type="checkbox"
            class="checkbox-input"
          />
          <span class="checkbox-text">
            Return {{ linkedBOMCount }} inventory-linked BOM {{ itemWord }} to stock
          </span>
        </label>
        <p v-if="isCompleted" class="inventory-hint">
          This project is <strong>Completed</strong> — these items were likely consumed.
          Only check this if the inventory was not actually used.
        </p>
        <p v-else-if="isActive" class="inventory-hint">
          These items were reserved for this project but not yet consumed.
        </p>
      </div>

      <!-- Info for cancelled projects (already restored) -->
      <div v-else-if="linkedBOMCount > 0 && !showInventoryOption" class="info-message">
        This project was already cancelled — inventory reservations were returned at that time.
      </div>
    </div>

    <template #footer>
      <button @click="emit('close')" class="btn btn-secondary">Cancel</button>
      <button @click="handleConfirm" class="btn btn-danger">Delete Project</button>
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

.inventory-option-box {
  padding: 12px;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.checkbox-input {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  cursor: pointer;
  accent-color: var(--color-primary, #3b82f6);
}

.checkbox-text {
  font-size: 14px;
  color: var(--color-text);
  font-weight: 500;
}

.inventory-hint {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted, var(--color-text));
  opacity: 0.8;
  line-height: 1.4;
}

.info-message {
  padding: 10px 12px;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 14px;
  color: var(--color-text);
}
</style>
