<script setup>
import { useRouter } from 'vue-router'
import DataTable from './DataTable.vue'

defineProps({
  items: { type: Array, required: true },
  visibleColumns: { type: Array, required: true },
})

const router = useRouter()
const headers = [
  { text: 'Title', value: 'title' },
  { text: 'Photo', value: 'photo' },
  { text: 'Manufacturer', value: 'manufacturer' },
  { text: 'Status', value: 'status' },
  { text: 'Serial Number', value: 'serial_number' },
  { text: 'Purchase Date', value: 'purchase_date' },
]

const viewPrinter = (printer) => {
  router.push({ name: 'printer-detail', params: { id: printer.id } })
}
</script>

<template>
  <DataTable
    :headers="headers"
    :items="items"
    :visible-columns="visibleColumns"
    @row-click="viewPrinter"
  >
    <template #cell-title="{ item }">
      {{ item.title }}
    </template>
    <template #cell-manufacturer="{ item }">
      {{ item.manufacturer ? item.manufacturer.name : 'N/A' }}
    </template>
    <template #cell-status="{ item }">
      {{ item.status }}
    </template>
    <template #cell-serial_number="{ item }">
      {{ item.serial_number }}
    </template>
    <template #cell-purchase_date="{ item }">
      {{ item.purchase_date }}
    </template>
  </DataTable>
</template>
