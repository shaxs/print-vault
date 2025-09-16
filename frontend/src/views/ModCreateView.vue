<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '../services/APIService'
import ModForm from '../components/ModForm.vue'

const route = useRoute()
const router = useRouter()
const printer = ref(null)
const isLoading = ref(true)

onMounted(async () => {
  try {
    const response = await APIService.getPrinter(route.params.printerId)
    printer.value = response.data
  } catch (error) {
    console.error('Failed to fetch printer for mod creation:', error)
  } finally {
    isLoading.value = false
  }
})

const handleSave = async ({ modData, files }) => {
  const formData = new FormData()

  // Ensure all required fields are present
  formData.append('printer', printer.value.id)
  formData.append('name', modData.name)
  formData.append('status', modData.status)

  // Only append link if it's not null/undefined, otherwise send an empty string
  formData.append('link', modData.link || '')

  // --- DEBUGGING STEP ---
  // This will print the exact data being sent to the server in your browser's console.
  console.log('Data being sent to server:', Object.fromEntries(formData.entries()))

  try {
    const response = await APIService.createMod(formData)
    const modId = response.data.id

    if (files.length > 0) {
      // Create a new FormData for files to avoid conflicts
      for (const file of files) {
        const fileFormData = new FormData()
        fileFormData.append('mod', modId)
        fileFormData.append('file', file)
        await APIService.createModFile(fileFormData)
      }
    }
    router.push({ name: 'printer-detail', params: { id: printer.value.id } })
  } catch (error) {
    // This will now log more detailed error info from the server if available
    console.error('Failed to create mod:', error)
    if (error.response) {
      console.error('Server response:', error.response.data)
    }
  }
}

const handleCancel = () => {
  router.back()
}
</script>

<template>
  <div class="form-page-container">
    <div v-if="isLoading">Loading...</div>
    <div v-else-if="printer">
      <h1>Add Mod to {{ printer.title }}</h1>
      <ModForm @save="handleSave" @cancel="handleCancel" />
    </div>
  </div>
</template>

<style scoped>
.form-page-container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 2rem;
}

h1 {
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 1rem;
}
</style>
