<script setup>
import { ref, onMounted } from 'vue'

const currentTheme = ref(localStorage.getItem('theme') || 'dark')

const toggleTheme = () => {
  currentTheme.value = currentTheme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.setAttribute('data-theme', currentTheme.value)
  localStorage.setItem('theme', currentTheme.value)
}

onMounted(() => {
  document.documentElement.setAttribute('data-theme', currentTheme.value)
})
</script>

<template>
  <button @click="toggleTheme" class="theme-toggle">
    <span v-if="currentTheme === 'dark'">🌙 Dark Mode</span>
    <span v-else>☀️ Light Mode</span>
  </button>
</template>

<style scoped>
.theme-toggle {
  background: none;
  border: 1px solid var(--color-border);
  color: var(--color-text);
  padding: 8px 15px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 5px;
}
.theme-toggle:hover {
  border-color: var(--color-border-hover);
}
</style>
