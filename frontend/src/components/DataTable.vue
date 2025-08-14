<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  headers: { type: Array, required: true },
  items: { type: Array, required: true },
  visibleColumns: { type: Array, required: true },
})

const emit = defineEmits(['row-click'])

const isPhotoModalVisible = ref(false)
const photoModalSrc = ref('')

const activeHeaders = computed(() => {
  return props.visibleColumns
    .map((key) => {
      return props.headers.find((h) => h.value === key)
    })
    .filter((h) => h)
})

const openPhotoModal = (src) => {
  photoModalSrc.value = src
  isPhotoModalVisible.value = true
}

watch(isPhotoModalVisible, (newValue) => {
  const handleKeydown = (event) => {
    if (event.key === 'Escape') {
      isPhotoModalVisible.value = false
    }
  }

  if (newValue) {
    window.addEventListener('keydown', handleKeydown)
  } else {
    window.removeEventListener('keydown', handleKeydown)
  }
})
</script>

<template>
  <div class="table-container">
    <table>
      <thead>
        <tr>
          <th v-for="header in activeHeaders" :key="header.value">{{ header.text }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="item in items"
          :key="item.id"
          @click="emit('row-click', item)"
          class="clickable-row"
        >
          <td v-for="header in activeHeaders" :key="header.value" :data-label="header.text">
            <template v-if="header.value === 'photo'">
              <img
                v-if="item.photo"
                :src="item.photo"
                alt="Thumbnail"
                class="table-thumbnail"
                @click.stop="openPhotoModal(item.photo)"
              />
            </template>
            <template v-else>
              <slot :name="`cell-${header.value}`" :item="item">{{ item[header.value] }}</slot>
            </template>
          </td>
        </tr>
        <tr v-if="!items.length">
          <td :colspan="activeHeaders.length > 0 ? activeHeaders.length : 1" class="no-items">
            No items found.
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="isPhotoModalVisible" class="modal-overlay" @click="isPhotoModalVisible = false">
      <div class="modal-content" @click.stop>
        <button @click="isPhotoModalVisible = false" class="close-button">&times;</button>
        <img :src="photoModalSrc" alt="Full size photo" class="modal-image" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.table-container {
  overflow-x: auto;
  width: 100%;
  user-select: none;
  cursor: default;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}
th,
td {
  border: 1px solid var(--color-border);
  text-align: left;
  padding: 12px 15px;
  vertical-align: middle;
  white-space: nowrap; /* Prevent text from wrapping */
}
th {
  background-color: var(--color-background-soft);
  color: var(--color-heading);
  font-weight: bold;
}
tr:nth-child(even) {
  background-color: var(--color-background-soft);
}
.clickable-row {
  cursor: pointer;
}
.clickable-row:hover {
  background-color: var(--color-background-mute);
}
.no-items {
  text-align: center;
  color: var(--color-text);
  padding: 20px;
}
.table-thumbnail {
  max-width: 50px;
  max-height: 50px;
  border-radius: 4px;
  cursor: pointer;
}
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-content {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
}
.modal-image {
  max-width: 100%;
  max-height: 100%;
  display: block;
}
.close-button {
  position: absolute;
  top: -15px;
  right: -15px;
  background: white;
  color: black;
  border: none;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  font-size: 24px;
  line-height: 30px;
  text-align: center;
  cursor: pointer;
  font-weight: bold;
}

/* The old responsive CSS is removed, allowing the table to scroll naturally */
</style>
