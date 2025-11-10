<!-- filepath: c:\Users\jason\projects\printvault\frontend\src\components\ProjectFilesForm.vue -->
<script setup>
import { ref } from 'vue'

defineProps({
  projectId: { type: Number, required: true },
})

const emit = defineEmits(['save', 'cancel'])

const fileInput = ref(null)
const newFiles = ref([])

const handleFileUpload = (event) => {
  newFiles.value = Array.from(event.target.files)
}

const removeNewFile = (index) => {
  newFiles.value.splice(index, 1)
}

const save = () => {
  emit('save', { files: newFiles.value })
}

const cancel = () => {
  emit('cancel')
}
</script>

<template>
  <form @submit.prevent="save" class="item-form">
    <div class="form-group">
      <label>Attach New Files</label>
      <button type="button" @click="fileInput.click()" class="btn btn-sm btn-secondary">
        Choose Files
      </button>
      <input
        type="file"
        ref="fileInput"
        multiple
        @change="handleFileUpload"
        class="file-input"
        style="display: none"
      />
      <ul v-if="newFiles.length > 0" class="file-list">
        <li v-for="(file, index) in newFiles" :key="index">
          <span>{{ file.name }}</span>
          <button type="button" @click="removeNewFile(index)" class="btn-icon-delete">
            &times;
          </button>
        </li>
      </ul>
    </div>
    <div class="form-actions">
      <button type="submit" class="btn btn-sm btn-primary">Save Files</button>
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
</style>
