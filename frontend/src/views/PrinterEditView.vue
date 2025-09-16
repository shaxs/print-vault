<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import APIService from '@/services/APIService.js'
import MainHeader from '@/components/MainHeader.vue'
import PrinterForm from '@/components/PrinterForm.vue'

const route = useRoute()
const printerToEdit = ref(null)

onMounted(async () => {
  try {
    const printerId = route.params.id
    const response = await APIService.getPrinter(printerId)
    printerToEdit.value = response.data
  } catch (error) {
    console.error('Error loading printer to edit:', error)
  }
})
</script>

<template>
  <div>
    <MainHeader
      title="Edit Printer"
      :showSearch="false"
      :showAddButton="false"
      :showFilterButton="false"
      :showColumnButton="false"
    />
    <PrinterForm v-if="printerToEdit" :initial-data="printerToEdit" />
    <p v-else>Loading printer...</p>
  </div>
</template>
