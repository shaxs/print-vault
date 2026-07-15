<script setup>
/*
 * Left-pane "Browse by Tags" control. A distinct button pinned above the folder
 * tree (so it never gets lost in a long tree) that expands an inline panel: a
 * quick tag-filter box plus the tag list as toggle chips. Selecting tags drives
 * a cross-folder results view in the parent (LibraryView).
 *
 * v-model is an array of selected tag objects ({ id, name, slug }).
 */
import { ref, computed, onMounted } from 'vue'
import APIService from '@/services/APIService'

const props = defineProps({
  modelValue: { type: Array, default: () => [] }, // selected tag objects
  matchMode: { type: String, default: 'all' }, // 'all' (AND) | 'any' (OR)
})
const emit = defineEmits(['update:modelValue', 'update:matchMode'])

const allTags = ref([])
const expanded = ref(false)
const filterText = ref('')

onMounted(loadTags)

async function loadTags() {
  try {
    // in_use=true hides orphaned tags (created then removed from every file) —
    // you can't browse to files of a tag nothing carries. Ordered most-used
    // first by the backend.
    const response = await APIService.getTags({ in_use: 'true' })
    allTags.value = response.data
  } catch (err) {
    console.error('Failed to load tags:', err)
  }
}

const selectedSlugs = computed(() => new Set(props.modelValue.map((t) => t.slug)))

const filteredTags = computed(() => {
  const q = filterText.value.trim().toLowerCase()
  if (!q) return allTags.value
  return allTags.value.filter((t) => t.name.toLowerCase().includes(q))
})

function isSelected(tag) {
  return selectedSlugs.value.has(tag.slug)
}

function toggle(tag) {
  if (isSelected(tag)) {
    emit(
      'update:modelValue',
      props.modelValue.filter((t) => t.slug !== tag.slug),
    )
  } else {
    emit('update:modelValue', [...props.modelValue, tag])
  }
}

function clearAll() {
  emit('update:modelValue', [])
}

function setMode(mode) {
  if (mode !== props.matchMode) emit('update:matchMode', mode)
}

// Let the parent re-pull the tag list after a file's tags change in the detail
// modal, so a just-added tag shows up (or a just-orphaned one disappears) in the
// filter without a page reload.
defineExpose({ reload: loadTags })
</script>

<template>
  <div class="tag-browser">
    <button
      type="button"
      class="tag-browse-toggle"
      :class="{ active: modelValue.length }"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <span class="chevron" :class="{ open: expanded }">▸</span>
      Browse by Tags
      <span v-if="modelValue.length" class="count-badge">{{ modelValue.length }}</span>
    </button>

    <div v-if="expanded" class="tag-panel">
      <input
        v-model="filterText"
        type="text"
        class="tag-filter-input"
        placeholder="Filter tags…"
        aria-label="Filter tags"
        spellcheck="false"
      />
      <!-- Multi-tag semantics: only meaningful with 2+ tags selected. -->
      <div v-if="modelValue.length >= 2" class="match-mode">
        <span class="match-label">Match</span>
        <div class="match-toggle">
          <button
            type="button"
            :class="{ active: matchMode === 'all' }"
            :aria-pressed="matchMode === 'all'"
            @click="setMode('all')"
          >
            All
          </button>
          <button
            type="button"
            :class="{ active: matchMode === 'any' }"
            :aria-pressed="matchMode === 'any'"
            @click="setMode('any')"
          >
            Any
          </button>
        </div>
      </div>
      <div v-if="modelValue.length" class="tag-panel-actions">
        <button type="button" class="link-button" @click="clearAll">Clear selection</button>
      </div>
      <ul v-if="filteredTags.length" class="tag-list">
        <li v-for="tag in filteredTags" :key="tag.id">
          <button
            type="button"
            class="tag-chip"
            :class="{ selected: isSelected(tag) }"
            :aria-pressed="isSelected(tag)"
            @click="toggle(tag)"
          >
            {{ tag.name }}
            <span v-if="tag.usage_count != null" class="tag-count">{{ tag.usage_count }}</span>
          </button>
        </li>
      </ul>
      <p v-else class="tag-empty">
        {{ allTags.length ? 'No matching tags.' : 'No tags yet — add tags from a file’s details.' }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.tag-browser {
  position: sticky;
  top: 0;
  z-index: 1;
  /* Match the left pane (.library-layout is --color-background-soft) so the
     sticky cover doesn't read as a darker box behind the button. */
  background-color: var(--color-background-soft);
  padding-bottom: 8px;
  margin-bottom: 4px;
}

/* Button-like, deliberately distinct from the tree rows below it. */
.tag-browse-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background-color: var(--color-background-mute);
  color: var(--color-heading);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
}

.tag-browse-toggle:hover {
  border-color: var(--color-border-hover);
}

.tag-browse-toggle.active {
  border-color: var(--color-blue);
}

.chevron {
  display: inline-block;
  transition: transform 0.15s ease;
  opacity: 0.7;
}

.chevron.open {
  transform: rotate(90deg);
}

.count-badge {
  margin-left: auto;
  min-width: 18px;
  padding: 0 6px;
  border-radius: 9px;
  background-color: var(--color-blue);
  color: #fff;
  font-size: 0.75rem;
  text-align: center;
}

.tag-panel {
  margin-top: 6px;
  padding: 8px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background-color: var(--color-background-soft);
}

.tag-filter-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-sizing: border-box;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.85rem;
}

/* Search/filter input — gray, no-shadow focus (design system) */
.tag-filter-input:focus {
  border-color: var(--color-border);
  box-shadow: none;
  outline: none;
}

.match-mode {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.match-label {
  color: var(--color-text-muted, var(--color-text));
  font-size: 0.8rem;
}

.match-toggle {
  display: inline-flex;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  overflow: hidden;
}

.match-toggle button {
  padding: 2px 10px;
  border: none;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.8rem;
  cursor: pointer;
}

.match-toggle button.active {
  background-color: var(--color-blue);
  color: #fff;
}

.tag-panel-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.link-button {
  background: none;
  border: none;
  padding: 0;
  color: var(--color-text);
  font-size: 0.8rem;
  cursor: pointer;
  text-decoration: underline;
}

.tag-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 220px;
  overflow-y: auto;
}

.tag-chip {
  padding: 3px 10px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background-color: var(--color-background-mute);
  color: var(--color-text);
  font-size: 0.8rem;
  cursor: pointer;
}

.tag-chip:hover {
  border-color: var(--color-border-hover);
}

.tag-chip.selected {
  background-color: var(--color-blue);
  border-color: var(--color-blue);
  color: #fff;
}

/* Usage count pill inside a chip. */
.tag-count {
  margin-left: 6px;
  padding: 0 5px;
  border-radius: 8px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.7rem;
  opacity: 0.85;
}

.tag-chip.selected .tag-count {
  background-color: rgba(255, 255, 255, 0.25);
  color: #fff;
  opacity: 1;
}

.tag-empty {
  margin: 8px 0 0;
  color: var(--color-text-muted, var(--color-text));
  font-size: 0.8rem;
}
</style>
