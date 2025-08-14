<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import APIService from '@/services/APIService.js'
import MainHeader from '@/components/MainHeader.vue'
import InventoryForm from '@/components/InventoryForm.vue'

const route = useRoute()
const itemToEdit = ref(null)

onMounted(async () => {
  try {
    const itemId = route.params.id
    const response = await APIService.getInventoryItem(itemId)
    itemToEdit.value = response.data
  } catch (error) {
    console.error('Error loading item to edit:', error)
  }
})
</script>

<template>
  <div>
    <MainHeader title="Edit Item" :showSearch="false" :showAddButton="false" />
    <InventoryForm v-if="itemToEdit" :initial-data="itemToEdit" />
    <p v-else>Loading item...</p>
  </div>
</template>
