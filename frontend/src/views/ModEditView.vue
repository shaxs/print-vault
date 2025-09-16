<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '../services/APIService'
import ModForm from '../components/ModForm.vue'

const route = useRoute()
const router = useRouter()
const mod = ref(null)
const isLoading = ref(true)

onMounted(async () => {
  try {
    const response = await APIService.getMod(route.params.modId)
    mod.value = response.data
  } catch (error) {
    console.error('Failed to fetch mod for editing:', error)
  } finally {
    isLoading.value = false
  }
})

const handleSave = async ({ modData, files, filesToDelete }) => {
  const modId = mod.value.id
  // 1. Update the core mod details (name, link, status)
  // We only send these fields, not the whole object
  const coreModData = {
    name: modData.name,
    link: modData.link,
    status: modData.status,
  }
  try {
    await APIService.updateMod(modId, coreModData)

    // 2. Delete any files that were marked for deletion
    for (const fileId of filesToDelete) {
      await APIService.deleteModFile(fileId)
    }

    // 3. Upload any new files
    if (files.length > 0) {
      for (const file of files) {
        const fileFormData = new FormData()
        fileFormData.append('mod', modId)
        fileFormData.append('file', file)
        await APIService.createModFile(fileFormData)
      }
    }

    // 4. Navigate back to the printer detail page
    router.push({ name: 'printer-detail', params: { id: route.params.printerId } })
  } catch (error) {
    console.error('Failed to update mod:', error)
  }
}

const handleCancel = () => {
  router.back()
}
</script>

<template>
  <div class="form-page-container">
    <div v-if="isLoading">Loading...</div>
    <div v-else-if="mod">
      <h1>Edit Mod: {{ mod.name }}</h1>
      <ModForm :mod="mod" @save="handleSave" @cancel="handleCancel" />
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
