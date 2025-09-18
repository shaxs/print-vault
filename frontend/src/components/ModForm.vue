<template>
  <form @submit.prevent="submitForm" class="item-form">
    <div class="form-group">
      <label for="modName">Mod Name</label>
      <input type="text" id="modName" v-model="editableMod.name" required />
    </div>
    <div class="form-group">
      <label for="modLink">Link</label>
      <input type="url" id="modLink" v-model="editableMod.link" />
    </div>
    <div class="form-group">
      <label for="modStatus">Status</label>
      <select id="modStatus" v-model="editableMod.status">
        <option>Planned</option>
        <option>In Progress</option>
        <option>Completed</option>
      </select>
    </div>

    <div class="form-group" v-if="existingFiles.length > 0">
      <label>Existing Files</label>
      <ul class="file-list">
        <li
          v-for="file in existingFiles"
          :key="file.id"
          class="file-list-item"
          :class="{ 'marked-for-deletion': filesToDelete.has(file.id) }"
        >
          <a :href="file.file" target="_blank" class="file-link">{{ getFileName(file.file) }}</a>
          <button
            type="button"
            @click.stop="toggleFileForDeletion(file.id)"
            class="btn-delete-file"
          >
            &times;
          </button>
        </li>
      </ul>
    </div>

    <div class="form-group">
      <label>Attach New Files</label>
      <p>Drag and drop files below, or click to select.</p>
      <div
        class="drop-zone"
        @dragover.prevent
        @dragenter.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleFileDrop"
        :class="{ 'drag-over': isDragging }"
        @click="triggerFileInput"
      >
        <input
          type="file"
          multiple
          @change="handleFileSelect"
          class="file-input"
          ref="fileInputRef"
        />
        <div v-if="!newFiles.length" class="text-center">
          <p>Click here or drop files to upload</p>
        </div>
        <ul v-else class="file-list">
          <li v-for="(file, index) in newFiles" :key="index" class="file-list-item">
            <span>{{ file.name }}</span>
            <button type="button" @click.stop="removeNewFile(index)" class="btn-delete-file">
              &times;
            </button>
          </li>
        </ul>
      </div>
    </div>

    <div class="form-actions">
      <button type="submit" class="btn btn-primary">Save Changes</button>
      <button type="button" @click="$emit('cancel')" class="btn btn-secondary">Cancel</button>
    </div>
  </form>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  mod: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['save', 'cancel'])

const editableMod = ref({})
const existingFiles = ref([])
const newFiles = ref([])
const filesToDelete = ref(new Set())
const isDragging = ref(false)
const fileInputRef = ref(null)

watch(
  () => props.mod,
  (newMod) => {
    if (newMod) {
      editableMod.value = { ...newMod }
      existingFiles.value = [...(newMod.files || [])]
    }
  },
  { immediate: true, deep: true },
)

const getFileName = (filePath) => {
  return filePath ? filePath.split('/').pop() : ''
}

const triggerFileInput = () => {
  fileInputRef.value.click()
}

const handleFileSelect = (event) => {
  addFiles(event.target.files)
}

const handleFileDrop = (event) => {
  isDragging.value = false
  addFiles(event.dataTransfer.files)
}

const addFiles = (fileList) => {
  newFiles.value.push(...Array.from(fileList))
}

const removeNewFile = (index) => {
  newFiles.value.splice(index, 1)
}

const toggleFileForDeletion = (fileId) => {
  if (filesToDelete.value.has(fileId)) {
    filesToDelete.value.delete(fileId)
  } else {
    filesToDelete.value.add(fileId)
  }
}

const submitForm = () => {
  emit('save', {
    modData: editableMod.value,
    files: newFiles.value,
    filesToDelete: Array.from(filesToDelete.value),
  })
}
</script>

<style scoped>
.item-form {
  background-color: var(--color-background-soft);
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
}

.form-group p {
  font-size: 0.9rem;
  color: var(--color-text-mute);
  margin-bottom: 0.75rem;
}

input[type='text'],
input[type='url'],
select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
}

.file-input {
  display: none;
}

.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: 0.5rem;
  padding: 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drop-zone.drag-over {
  background-color: var(--color-background-mute);
}

.file-list {
  list-style-type: none;
  padding: 0;
  margin-top: 1rem;
}

.file-list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  transition: opacity 0.2s;
}

.file-list-item.marked-for-deletion {
  opacity: 0.6;
}

.file-list-item.marked-for-deletion .file-link {
  text-decoration: line-through;
}

.file-link {
  color: var(--color-heading);
  text-decoration: none;
  font-weight: 500;
}
.file-link:hover {
  text-decoration: underline;
}

.btn-delete-file {
  background: none;
  border: none;
  color: #ef4444;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0 0.5rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
  border-top: 1px solid var(--color-border);
  padding-top: 1.5rem;
}
</style>
