<script setup>
/*
 * Neutral, themed tag chip. Colors were deliberately dropped from v1 (auto-
 * assigned colors carry no meaning); a user-chosen color option can be added
 * later without touching callers.
 */
defineProps({
  tag: { type: Object, required: true }, // { id, name, slug }
  removable: { type: Boolean, default: false },
})
const emit = defineEmits(['remove'])
</script>

<template>
  <span class="tag-badge" :title="tag.name">
    {{ tag.name }}
    <button
      v-if="removable"
      type="button"
      class="tag-remove"
      :aria-label="`Remove tag: ${tag.name}`"
      @click.stop="emit('remove', tag)"
    >
      &times;
    </button>
  </span>
</template>

<style scoped>
.tag-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  font-size: 0.8rem;
  line-height: 1.4;
  white-space: nowrap;
}

.tag-remove {
  background: none;
  border: none;
  padding: 0;
  color: var(--color-text);
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0.6;
}

.tag-remove:hover {
  opacity: 1;
}
</style>
