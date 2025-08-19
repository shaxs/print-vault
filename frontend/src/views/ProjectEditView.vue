<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import APIService from '@/services/APIService.js'
import MainHeader from '@/components/MainHeader.vue'
import ProjectForm from '@/components/ProjectForm.vue'

const route = useRoute()
const projectToEdit = ref(null)

onMounted(async () => {
  try {
    const projectId = route.params.id
    const response = await APIService.getProject(projectId)
    projectToEdit.value = response.data
  } catch (error) {
    console.error('Error loading project to edit:', error)
  }
})
</script>

<template>
  <div>
    <MainHeader
      title="Edit Project"
      :showSearch="false"
      :showAddButton="false"
      :show-filter-button="false"
      :show-column-button="false"
    />
    <ProjectForm v-if="projectToEdit" :initial-data="projectToEdit" />
    <p v-else>Loading project...</p>
  </div>
</template>
