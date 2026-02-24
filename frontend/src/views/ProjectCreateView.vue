<script setup>
import MainHeader from '../components/MainHeader.vue'
import ProjectForm from '../components/ProjectForm.vue'
</script>

<template>
  <div>
    <MainHeader title="Add New Project" :showSearch="false" :showAddButton="false" :showFilterButton="false" :showColumnButton="false" />
    <ProjectForm />
  </div>
</template>
