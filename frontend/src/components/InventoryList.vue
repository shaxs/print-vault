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
  { text: 'Brand', value: 'brand' },
  { text: 'Part Type', value: 'partType' },
  { text: 'Location', value: 'location' },
  { text: 'Quantity', value: 'quantity' },
  { text: 'Cost', value: 'cost' },
]

const viewItem = (item) => {
  router.push({ name: 'item-detail', params: { id: item.id } })
}
</script>

<template>
  <DataTable
    :headers="headers"
    :items="items"
    :visible-columns="visibleColumns"
    @row-click="viewItem"
  >
    <template #cell-title="{ item }">
      {{ item.title }}
    </template>
    <template #cell-brand="{ item }">
      {{ item.brand ? item.brand.name : 'N/A' }}
    </template>
    <template #cell-partType="{ item }">
      {{ item.part_type ? item.part_type.name : 'N/A' }}
    </template>
    <template #cell-location="{ item }">
      {{ item.location ? item.location.name : 'N/A' }}
    </template>
    <template #cell-quantity="{ item }">
      {{ item.quantity }}
    </template>
    <template #cell-cost="{ item }"> ${{ item.cost || '0.00' }} </template>
  </DataTable>
</template>
