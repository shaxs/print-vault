<script setup>
import { useRouter } from 'vue-router'
import { ref } from 'vue'
import DataTable from './DataTable.vue'

const props = defineProps({
  items: { type: Array, required: true },
  visibleColumns: { type: Array, required: true },
})

const router = useRouter()

// Color swatch lightbox state
const isColorSwatchModalVisible = ref(false)
const selectedColorHex = ref(null)

const openColorSwatchModal = (colorHex) => {
  selectedColorHex.value = colorHex
  isColorSwatchModalVisible.value = true
}

const headers = [
  { text: 'Photo', value: 'photo' },
  { text: 'Brand', value: 'brand' },
  { text: 'Name', value: 'name' },
  { text: 'Colors', value: 'colors' },
  { text: 'Material', value: 'material' },
  { text: 'Color Family', value: 'colorFamily' },
  { text: 'Diameter', value: 'diameter' },
]

const viewItem = (item) => {
  const filteredItemIds = props.items.map((i) => i.id)
  const currentIndex = filteredItemIds.indexOf(item.id)

  sessionStorage.setItem(
    'materialNavState',
    JSON.stringify({
      filteredItemIds,
      currentIndex,
    }),
  )

  router.push({
    name: 'material-detail',
    params: { id: item.id },
    state: {
      filteredItemIds,
      currentIndex,
    },
  })
}
</script>

<template>
  <DataTable
    :headers="headers"
    :items="items"
    :visible-columns="visibleColumns"
    @row-click="viewItem"
  >
    <template #cell-photo="{ item }">
      <img v-if="item.photo" :src="item.photo" alt="Material" class="table-thumbnail" />
      <span v-else class="no-photo">—</span>
    </template>

    <template #cell-brand="{ item }">
      {{ item.brand?.name || 'N/A' }}
    </template>

    <template #cell-name="{ item }">
      {{ item.name || 'N/A' }}
    </template>

    <template #cell-colors="{ item }">
      <div class="color-swatches">
        <span
          v-for="(color, index) in (item.colors || []).slice(0, 5)"
          :key="index"
          class="color-swatch"
          :style="{ backgroundColor: color }"
          :title="color"
          @click.stop="openColorSwatchModal(color)"
        ></span>
        <span v-if="item.colors && item.colors.length > 5" class="more-colors">
          +{{ item.colors.length - 5 }}
        </span>
      </div>
    </template>

    <template #cell-material="{ item }">
      {{ item.base_material?.name || 'N/A' }}
    </template>

    <template #cell-colorFamily="{ item }">
      <span v-if="item.color_family" class="color-family-text">
        {{ item.color_family }}
      </span>
      <span v-else>—</span>
    </template>

    <template #cell-diameter="{ item }">
      {{ item.diameter ? `${item.diameter}mm` : '—' }}
    </template>
  </DataTable>

  <!-- Color Swatch Lightbox Modal -->
  <div
    v-if="isColorSwatchModalVisible"
    class="modal-overlay"
    @click="isColorSwatchModalVisible = false"
  >
    <div class="color-swatch-modal-content" @click.stop>
      <button @click="isColorSwatchModalVisible = false" class="close-button">&times;</button>
      <div
        class="color-swatch-large"
        :style="{ backgroundColor: selectedColorHex || '#cccccc' }"
      ></div>
      <p class="color-hex-label">{{ selectedColorHex }}</p>
    </div>
  </div>
</template>

<style scoped>
.table-thumbnail {
  width: 50px;
  height: 50px;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
}

.no-photo {
  color: var(--color-text-muted);
}

.color-swatches {
  display: flex;
  align-items: center;
  gap: 4px;
}

.color-swatch {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: 1px solid var(--color-border);
  display: inline-block;
  cursor: pointer;
  transition: transform 0.15s ease;
}

.color-swatch:hover {
  transform: scale(1.15);
}

.more-colors {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-left: 4px;
}

.color-family-text {
  text-transform: capitalize;
}

/* Color Swatch Lightbox Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.color-swatch-modal-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.color-swatch-large {
  width: 250px;
  height: 250px;
  border-radius: 16px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.color-hex-label {
  color: white;
  font-size: 1.25rem;
  font-family: monospace;
  background: rgba(0, 0, 0, 0.5);
  padding: 0.5rem 1rem;
  border-radius: 8px;
}

.close-button {
  position: absolute;
  top: -40px;
  right: 0;
  background: none;
  border: none;
  color: white;
  font-size: 2rem;
  cursor: pointer;
  padding: 0.5rem;
}

.close-button:hover {
  color: var(--color-text-muted);
}
</style>
