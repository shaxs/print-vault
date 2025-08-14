<script setup>
import MainHeader from '../components/MainHeader.vue'
import InventoryForm from '../components/InventoryForm.vue'
</script>

<template>
  <div>
    <MainHeader title="Add New Item" :showSearch="false" :showAddButton="false" />
    <InventoryForm />
  </div>
</template>
