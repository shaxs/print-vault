<template>
  <div class="preferences-tab-container">
    <div class="content-header">
      <h3>Theme Preferences</h3>
    </div>
    <div class="preference-item">
      <div class="preference-description">
        <h4>Appearance</h4>
        <p>Switch between light and dark mode for the application.</p>
      </div>
      <button @click="toggleTheme" class="theme-toggle">
        <span v-if="currentTheme === 'dark'">🌙 Dark Mode</span>
        <span v-else>☀️ Light Mode</span>
      </button>
    </div>
  </div>
</template>

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

<style scoped>
.preferences-tab-container {
  display: flex;
  flex-direction: column;
}

.content-header h3 {
  color: var(--color-heading);
  margin-bottom: 1.5rem;
}

.preference-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
}

.preference-description h4 {
  color: var(--color-heading);
  margin-top: 0;
  margin-bottom: 0.5rem;
}

.preference-description p {
  margin: 0;
  font-size: 0.9rem;
}
/* Removed custom button styles; use global .btn classes */
/* Removed leftover invalid CSS from previous custom button styles */
</style>
