<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  mod: {
    type: Object,
    default: () => ({ name: '', link: '', status: 'Planned', files: [] }),
  },
})

const emit = defineEmits(['save', 'cancel'])

const formData = ref({})
const newFiles = ref([])
const filesToDelete = ref(new Set())

const getFileName = (filePath) => {
  if (!filePath) return ''
  return filePath.split('/').pop()
}

watch(
  () => props.mod,
  (newMod) => {
    // Correctly clone the mod data, ensuring the files array is also cloned
    formData.value = { ...newMod, files: [...(newMod.files || [])] }
  },
  { immediate: true, deep: true },
)

const triggerFileInput = (inputId) => {
  document.getElementById(inputId).click()
}

const handleFileUpload = (event) => {
  // Append new files to the existing list instead of replacing
  newFiles.value.push(...Array.from(event.target.files))
}

const removeNewFile = (index) => {
  newFiles.value.splice(index, 1)
}

const markFileForDeletion = (fileId) => {
  if (filesToDelete.value.has(fileId)) {
    filesToDelete.value.delete(fileId)
  } else {
    filesToDelete.value.add(fileId)
  }
}

const save = () => {
  emit('save', {
    modData: formData.value,
    files: newFiles.value,
    filesToDelete: filesToDelete.value,
  })
}

const cancel = () => {
  emit('cancel')
}
</script>

<template>
  <form @submit.prevent="save" class="item-form">
    <div class="form-group">
      <label for="modName">Mod Name</label>
      <input type="text" id="modName" v-model="formData.name" class="form-control" required />
    </div>
    <div class="form-group">
      <label for="modLink">Link</label>
      <input
        type="url"
        id="modLink"
        v-model="formData.link"
        class="form-control"
        placeholder="https://..."
      />
    </div>
    <div class="form-group">
      <label for="modStatus">Status</label>
      <select id="modStatus" v-model="formData.status" class="form-control">
        <option>Planned</option>
        <option>In Progress</option>
        <option>Completed</option>
        <option>On Hold</option>
      </select>
    </div>

    <div class="form-group" v-if="formData.files && formData.files.length > 0">
      <label>Existing Files</label>
      <ul class="file-list">
        <li
          v-for="file in formData.files"
          :key="file.id"
          :class="{ 'marked-for-deletion': filesToDelete.has(file.id) }"
        >
          <a :href="file.file" target="_blank" class="file-link">{{ getFileName(file.file) }}</a>
          <button type="button" @click="markFileForDeletion(file.id)" class="btn-delete-file">
            &times;
          </button>
        </li>
      </ul>
    </div>

    <div class="form-group">
      <label>Attach New Files</label>
      <button
        type="button"
        @click="triggerFileInput('newModFileInput')"
        class="btn btn-sm btn-secondary"
      >
        Choose Files
      </button>
      <input
        type="file"
        id="newModFileInput"
        multiple
        @change="handleFileUpload"
        class="file-input"
      />
      <ul v-if="newFiles.length > 0" class="file-list">
        <li v-for="(file, index) in newFiles" :key="index">
          <span>{{ file.name }}</span>
          <button type="button" @click="removeNewFile(index)" class="btn-delete-file">
            &times;
          </button>
        </li>
      </ul>
    </div>

    <div class="form-actions">
      <button type="submit" class="btn btn-sm btn-primary">Save Mod</button>
      <button type="button" @click="cancel" class="btn btn-sm btn-secondary">Cancel</button>
    </div>
  </form>
</template>

<style scoped>
.item-form {
  max-width: 600px;
  margin: 0 auto;
}
.form-group {
  margin-bottom: 1.5rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
}
.file-input {
  display: none;
}
.file-list {
  list-style-type: none;
  padding: 0;
  margin-top: 1rem;
}
.file-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}
.file-list li.marked-for-deletion .file-link {
  text-decoration: line-through;
  opacity: 0.6;
}
.file-list li .file-link {
  color: var(--color-text);
  text-decoration: none;
}
.file-list li .file-link:hover {
  text-decoration: underline;
  color: var(--color-blue);
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
  border-top: 1px solid var(--color-border);
  padding-top: 1.5rem;
}
.form-control:-webkit-autofill,
.form-control:-webkit-autofill:hover,
.form-control:-webkit-autofill:focus,
.form-control:-webkit-autofill:active {
  -webkit-box-shadow: 0 0 0 30px var(--color-background) inset !important;
  -webkit-text-fill-color: var(--color-text) !important;
}
</style>
