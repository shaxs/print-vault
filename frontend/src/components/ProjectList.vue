<script setup>
import { useRouter } from 'vue-router'
import DataTable from './DataTable.vue'

defineProps({
  items: { type: Array, required: true },
  visibleColumns: { type: Array, required: true },
})

const router = useRouter()
const headers = [
  { text: 'Project Name', value: 'projectName' },
  { text: 'Status', value: 'status' },
  { text: 'Description', value: 'description' },
]

const viewProject = (project) => {
  router.push({ name: 'project-detail', params: { id: project.id } })
}
</script>

<template>
  <DataTable
    :headers="headers"
    :items="items"
    :visible-columns="visibleColumns"
    @row-click="viewProject"
  >
    <template #cell-projectName="{ item }">
      {{ item.project_name }}
    </template>
    <template #cell-status="{ item }">
      {{ item.status }}
    </template>
    <template #cell-description="{ item }">
      {{ item.description }}
    </template>
  </DataTable>
</template>
