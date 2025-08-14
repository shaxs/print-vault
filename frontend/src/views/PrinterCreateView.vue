<script setup>
import PrinterForm from '../components/PrinterForm.vue'
import MainHeader from '../components/MainHeader.vue'
</script>

<template>
  <div>
    <MainHeader title="Add New Printer" :showSearch="false" :showAddButton="false" />
    <PrinterForm />
  </div>
</template>

<style scoped>
div {
  padding: 20px;
}
</style>
