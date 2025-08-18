<script setup>
import { RouterLink } from 'vue-router'
import { ref, onMounted } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  createUrl: { type: String, default: '' },
  showSearch: { type: Boolean, default: true },
  showAddButton: { type: Boolean, default: true },
  showFilterButton: { type: Boolean, default: true },
  showColumnButton: { type: Boolean, default: true },
  modelValue: { type: String },
})

const emit = defineEmits(['update:modelValue', 'open-filter', 'open-columns'])

const clearSearch = () => {
  emit('update:modelValue', '')
}

// Theme toggle logic
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
  <div class="main-header">
    <h1 class="header-title">{{ title }}</h1>
    <div class="header-actions">
      <button v-if="showFilterButton" @click="emit('open-filter')" class="header-button">
        Filter
      </button>
      <button v-if="showColumnButton" @click="emit('open-columns')" class="header-button">
        Columns
      </button>
      <div v-if="showSearch" class="search-container">
        <input
          type="search"
          placeholder="Search..."
          class="search-bar"
          :value="modelValue"
          @input="emit('update:modelValue', $event.target.value)"
        />
        <button v-if="modelValue" @click="clearSearch" class="search-clear-button">&times;</button>
      </div>
      <RouterLink v-if="showAddButton" :to="createUrl" class="add-button">+ Add</RouterLink>
      <!-- Theme Toggle Button -->
      <button @click="toggleTheme" class="theme-toggle">
        <span v-if="currentTheme === 'dark'">🌙 Dark Mode</span>
        <span v-else>☀️ Light Mode</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.main-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 1rem;
  flex-wrap: wrap;
}
.header-title {
  margin: 0;
  color: var(--color-heading);
  user-select: none;
  cursor: default;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}
.search-container {
  position: relative;
}
.search-bar {
  padding: 8px 30px 8px 12px; /* Add padding to the right for the button */
  border: 1px solid var(--color-border);
  border-radius: 5px;
  min-width: 250px;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  font-size: 1rem;
  height: 41px;
}
.search-clear-button {
  position: absolute;
  right: 5px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--color-text);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0 5px;
}
.add-button,
.header-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 15px;
  text-decoration: none;
  border-radius: 5px;
  font-weight: bold;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  font-size: 1rem;
  height: 41px;
  user-select: none;
}
.add-button {
  background-color: var(--color-blue);
  color: white;
}
.header-button {
  background: none;
  border: 1px solid var(--color-border);
  color: var(--color-text);
}
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

@media (max-width: 768px) {
  .main-header {
    flex-direction: column;
    align-items: stretch;
  }
  .header-actions {
    justify-content: flex-end;
  }
  .search-bar {
    min-width: 0;
    flex-grow: 1;
  }
}
</style>
