<template>
  <div class="modules-tab-container">
    <div class="content-header">
      <h3>Navigation Modules</h3>
    </div>
    <p class="description">
      Show or hide top-level sections in the sidebar. Hiding a section only removes its
      navigation link — its data and pages remain, and you can re-enable it here anytime.
      Dashboard and Settings are always shown.
    </p>

    <div class="module-list">
      <div v-for="module in modules" :key="module.key" class="module-item">
        <div class="module-description">
          <h4>{{ module.label }}</h4>
          <p>{{ isHidden(module.key) ? 'Hidden from the sidebar' : 'Visible in the sidebar' }}</p>
        </div>
        <label class="switch" :title="`Toggle ${module.label}`">
          <input
            type="checkbox"
            :checked="!isHidden(module.key)"
            @change="onToggle(module.key, $event.target.checked)"
          />
          <span class="slider"></span>
        </label>
      </div>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { MODULES } from '@/config/modules.js'
import { useAppConfig } from '@/composables/useAppConfig.js'

const modules = MODULES
const { isHidden, load, setHidden } = useAppConfig()
const error = ref(null)

// Checkbox "checked" means visible, so hidden is the inverse.
const onToggle = async (key, visible) => {
  error.value = null
  try {
    await setHidden(key, !visible)
  } catch (err) {
    console.error('Failed to update module visibility:', err)
    error.value = 'Failed to save. Please try again.'
  }
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.modules-tab-container {
  display: flex;
  flex-direction: column;
}

.content-header h3 {
  color: var(--color-heading);
  margin-bottom: 0.5rem;
}

.description {
  color: var(--color-text-muted, var(--color-text));
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.module-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.module-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 16px 20px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
}

.module-description h4 {
  color: var(--color-heading);
  margin: 0 0 0.25rem 0;
}

.module-description p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--color-text-muted, var(--color-text));
}

/* Toggle switch (theme-aware via CSS variables) */
.switch {
  position: relative;
  display: inline-block;
  width: 46px;
  height: 24px;
  flex-shrink: 0;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  inset: 0;
  cursor: pointer;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 24px;
  transition: background-color 0.2s, border-color 0.2s;
}

.slider::before {
  content: '';
  position: absolute;
  height: 18px;
  width: 18px;
  left: 2px;
  top: 2px;
  background-color: var(--color-text);
  border-radius: 50%;
  transition: transform 0.2s;
}

.switch input:checked + .slider {
  background-color: var(--color-blue);
  border-color: var(--color-blue);
}

.switch input:checked + .slider::before {
  transform: translateX(22px);
  background-color: #fff;
}

.switch input:focus-visible + .slider {
  outline: 2px solid var(--color-blue);
  outline-offset: 2px;
}

.error-text {
  margin-top: 1rem;
  color: var(--color-red);
  font-size: 0.875rem;
}
</style>
