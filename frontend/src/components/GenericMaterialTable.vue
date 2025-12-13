<script setup>
import { computed } from 'vue'
import DataTable from './DataTable.vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  visibleColumns: {
    type: Array,
    default: () => ['name'],
  },
})

const headers = computed(() => {
  const allHeaders = [{ value: 'name', text: 'Name' }]
  return allHeaders.filter((header) => props.visibleColumns.includes(header.value))
})

const tableItems = computed(() => {
  return props.items.map((item) => ({
    id: item.id,
    name: item.name || 'Unnamed Material',
  }))
})

const viewItem = (item) => {
  router.push({ name: 'material-detail', params: { id: item.id } })
}
</script>

<template>
  <DataTable
    :headers="headers"
    :items="tableItems"
    :visible-columns="visibleColumns"
    @row-click="viewItem"
  >
    <template #cell-name="{ item }">
      {{ item.name }}
    </template>
  </DataTable>
</template>

<style scoped>
/* Generic materials table has minimal styling - only name column */
</style>
