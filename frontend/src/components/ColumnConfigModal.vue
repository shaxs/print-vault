<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  allColumns: { type: Array, required: true },
  visibleColumns: { type: Array, required: true },
})

const emit = defineEmits(['save', 'close'])

// Local state for the modal, initialized from props
const localVisible = ref([...props.visibleColumns])

const visibleColumnsFull = computed(() =>
  props.allColumns
    .filter((c) => localVisible.value.includes(c.value))
    .sort((a, b) => localVisible.value.indexOf(a.value) - localVisible.value.indexOf(b.value)),
)

const hiddenColumnsFull = computed(() =>
  props.allColumns.filter((c) => !localVisible.value.includes(c.value)),
)

const moveToVisible = (columnValue) => {
  localVisible.value.push(columnValue)
}

const moveToHidden = (columnValue) => {
  localVisible.value = localVisible.value.filter((v) => v !== columnValue)
}

// Functions to move items up/down in the visible list
const moveUp = (index) => {
  if (index > 0) {
    const item = localVisible.value.splice(index, 1)[0]
    localVisible.value.splice(index - 1, 0, item)
  }
}
const moveDown = (index) => {
  if (index < localVisible.value.length - 1) {
    const item = localVisible.value.splice(index, 1)[0]
    localVisible.value.splice(index + 1, 0, item)
  }
}

const save = () => {
  emit('save', localVisible.value)
  emit('close')
}
</script>

<template>
  <div class="modal-overlay" @click="emit('close')">
    <div class="modal-form" @click.stop>
      <h3>Configure Columns</h3>
      <div class="column-config-container">
        <div class="column-list">
          <h4>Visible Columns</h4>
          <div v-for="(col, index) in visibleColumnsFull" :key="col.value" class="column-item">
            <span>{{ col.text }}</span>
            <div class="column-item-actions">
              <button @click="moveUp(index)" :disabled="index === 0" class="move-button">
                &#8593;
              </button>
              <button
                @click="moveDown(index)"
                :disabled="index === visibleColumnsFull.length - 1"
                class="move-button"
              >
                &#8595;
              </button>
              <button @click="moveToHidden(col.value)" class="move-button">&gt;</button>
            </div>
          </div>
        </div>
        <div class="column-list">
          <h4>Hidden Columns</h4>
          <div v-for="col in hiddenColumnsFull" :key="col.value" class="column-item">
            <button @click="moveToVisible(col.value)" class="move-button">&lt;</button>
            <span>{{ col.text }}</span>
          </div>
        </div>
      </div>
      <div class="form-actions">
        <button @click="save" class="save-button">Save</button>
        <button @click="emit('close')" type="button" class="cancel-button">Cancel</button>
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
.modal-form {
  background-color: var(--color-background-soft);
  padding: 20px;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
}
.modal-form h3 {
  color: var(--color-heading);
  margin-bottom: 20px;
}
.column-config-container {
  display: flex;
  gap: 20px;
}
.column-list {
  flex: 1;
  background-color: var(--color-background);
  padding: 10px;
  border-radius: 5px;
  min-height: 300px;
  max-height: 50vh;
  overflow-y: auto;
}
.column-list h4 {
  margin-top: 0;
  margin-bottom: 10px;
  color: var(--color-heading);
}
.column-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  margin-bottom: 5px;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 4px;
}
.column-item-actions {
  display: flex;
  gap: 5px;
}
.move-button {
  background: var(--color-background-mute);
  border: 1px solid var(--color-border);
  color: var(--color-heading);
  border-radius: 5px;
  width: 28px;
  height: 28px;
  cursor: pointer;
  font-weight: bold;
}
.move-button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
.save-button,
.cancel-button {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  text-decoration: none;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
}
.save-button {
  background-color: var(--color-blue);
  color: white;
}
.cancel-button {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
  border: 1px solid var(--color-border);
}
</style>
