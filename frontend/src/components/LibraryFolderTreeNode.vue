<script setup>
/*
 * One node of the library's left-nav folder tree. Recursive (refers to
 * itself by filename). The whole tree renders from a single skeleton
 * payload fetched once by LibraryView — expanding/collapsing a node is
 * purely client-side, no further requests.
 *
 * Tree-wide state (selection, expansion, children lookup) is provided by
 * LibraryView via inject, which avoids re-emitting events through every
 * level of recursion.
 */
import { computed, inject } from 'vue'

const props = defineProps({
  folder: { type: Object, required: true }, // { id, name, parent_id }
})

const tree = inject('libraryTree')

const children = computed(() => tree.childrenOf(props.folder.id))
const hasChildren = computed(() => children.value.length > 0)
const isExpanded = computed(() => tree.isExpanded(props.folder.id))
const isSelected = computed(() => tree.selectedId === props.folder.id)
</script>

<template>
  <li class="tree-node">
    <div
      class="tree-row"
      :class="{ 'tree-row-selected': isSelected }"
      @click="tree.select(folder.id)"
    >
      <span
        v-if="hasChildren"
        class="tree-caret"
        :class="{ 'tree-caret-open': isExpanded }"
        @click.stop="tree.toggle(folder.id)"
      ></span>
      <span v-else class="tree-caret-spacer"></span>
      <span class="tree-label" :title="folder.name">{{ folder.name }}</span>
    </div>
    <ul v-if="hasChildren && isExpanded" class="tree-children">
      <LibraryFolderTreeNode v-for="child in children" :key="child.id" :folder="child" />
    </ul>
  </li>
</template>

<style scoped>
.tree-node {
  list-style: none;
}

.tree-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--color-text);
  user-select: none;
  white-space: nowrap;
}

.tree-row:hover {
  background-color: var(--color-background-mute);
}

.tree-row-selected {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
  font-weight: 600;
}

/* CSS caret triangle — rotates when expanded */
.tree-caret {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.12s ease;
}

.tree-caret::before {
  content: '';
  border-left: 5px solid var(--color-text-muted, var(--color-text));
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
}

.tree-caret-open {
  transform: rotate(90deg);
}

.tree-caret-spacer {
  width: 16px;
  flex-shrink: 0;
}

.tree-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.tree-children {
  margin: 0;
  padding-left: 16px;
}
</style>
