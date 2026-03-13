<script setup>
/**
 * InfoTooltip.vue
 * A small ? badge that reveals a floating tooltip panel on hover/focus.
 * Uses Vue Teleport so the panel is attached to <body>, escaping any
 * overflow:hidden ancestors (cards, modals, etc.) that would clip it.
 * Uses a slot so callers can supply rich HTML content.
 *
 * Usage:
 *   <InfoTooltip>
 *     <strong>Term A</strong> — explanation...<br /><br />
 *     <strong>Term B</strong> — explanation...
 *   </InfoTooltip>
 */
import { ref } from 'vue'

const triggerRef = ref(null)
const isVisible = ref(false)
const panelStyle = ref({})

const showTooltip = () => {
  if (!triggerRef.value) return
  const rect = triggerRef.value.getBoundingClientRect()
  panelStyle.value = {
    left: `${rect.left + rect.width / 2}px`,
    bottom: `${window.innerHeight - rect.top + 8}px`,
  }
  isVisible.value = true
}

const hideTooltip = () => {
  isVisible.value = false
}
</script>

<template>
  <span class="info-tooltip">
    <button
      ref="triggerRef"
      type="button"
      class="info-tooltip__trigger"
      aria-label="More information"
      @mouseenter="showTooltip"
      @mouseleave="hideTooltip"
      @focus="showTooltip"
      @blur="hideTooltip"
    ></button>

    <!-- Teleport to body so overflow:hidden cards don't clip the panel -->
    <Teleport to="body">
      <span
        v-if="isVisible"
        class="info-tooltip__panel"
        role="tooltip"
        :style="panelStyle"
      >
        <slot />
        <span class="info-tooltip__arrow"></span>
      </span>
    </Teleport>
  </span>
</template>

<style scoped>
.info-tooltip {
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
}

/* The circular ? badge — ? rendered via ::after for precise centering */
.info-tooltip__trigger {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background-color: var(--color-heading);
  border: none;
  cursor: default;
  user-select: none;
  margin-left: 0.375rem;
  flex-shrink: 0;
  opacity: 0.45;
  transition: background-color 0.15s, opacity 0.15s;
  padding: 0;
  overflow: hidden;
}

.info-tooltip__trigger::after {
  content: '?';
  font-size: 9px;
  font-weight: 700;
  font-family: sans-serif;
  line-height: 1;
  letter-spacing: 0;
  color: var(--color-background);
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -52%); /* -52% corrects ? glyph descender offset */
}

.info-tooltip__trigger:hover,
.info-tooltip__trigger:focus {
  background-color: var(--color-blue);
  opacity: 1;
  outline: none;
}
</style>

<!-- Global styles for teleported panel (not scoped so Teleport can reach it) -->
<style>
.info-tooltip__panel {
  position: fixed;
  transform: translateX(-50%);
  background-color: var(--color-background-soft);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 0.625rem 0.75rem;
  font-size: 0.8125rem;
  line-height: 1.55;
  width: 290px;
  z-index: 9999;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
  text-align: left;
  font-weight: 400;
  pointer-events: none;
}

.info-tooltip__arrow {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid var(--color-border);
}

.info-tooltip__arrow::after {
  content: '';
  position: absolute;
  top: -7px;
  left: -5px;
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 5px solid var(--color-background-soft);
}
</style>
