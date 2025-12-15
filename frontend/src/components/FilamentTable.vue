<script setup>
import { useRouter } from 'vue-router'
import { computed, ref } from 'vue'
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
  { text: 'Colors', value: 'colors' },
  { text: 'Name', value: 'name' },
  { text: 'Material', value: 'material' },
  { text: 'Features', value: 'features' },
  { text: 'Quantity', value: 'quantity' },
  { text: 'Status', value: 'status' },
  { text: 'Location/Printer', value: 'location' },
  { text: 'Filament Used', value: 'filamentUsed' },
]

// Helper functions for Quick Add vs Blueprint data
const getSpoolPhoto = (item) => {
  return item.is_quick_add ? item.standalone_photo : item.filament_type?.photo || null
}

const getSpoolBrand = (item) => {
  return item.is_quick_add
    ? item.standalone_brand?.name || 'N/A'
    : item.filament_type?.brand?.name || 'N/A'
}

const getSpoolColors = (item) => {
  return item.is_quick_add ? item.standalone_colors || [] : item.filament_type?.colors || []
}

const getSpoolName = (item) => {
  return item.is_quick_add
    ? item.standalone_name || 'Quick Add Spool'
    : item.filament_type?.color_name || item.filament_type?.name || 'N/A'
}

const getSpoolMaterial = (item) => {
  return item.is_quick_add
    ? item.standalone_material_type?.name || 'N/A'
    : item.filament_type?.base_material?.name || 'N/A'
}

const getSpoolFeatures = (item) => {
  // Quick Add spools don't have features
  if (item.is_quick_add) return []
  return item.filament_type?.features || []
}

// Transform items to map photo for DataTable
const transformedItems = computed(() => {
  return props.items.map((item) => ({
    ...item,
    photo: getSpoolPhoto(item),
  }))
})

const getStatusLabel = (status) => {
  const statusMap = {
    new: 'New',
    opened: 'Opened',
    in_use: 'In Use',
    low: 'Low',
    empty: 'Empty',
    archived: 'Archived',
  }
  return statusMap[status] || status
}

const getFilamentUsedColor = (usedPercent) => {
  if (usedPercent <= 50) return '#10b981' // Green - 0-50% used (plenty left)
  if (usedPercent <= 75) return '#eab308' // Yellow - 51-75% used (medium)
  if (usedPercent <= 90) return '#f59e0b' // Orange - 76-90% used (getting low)
  return '#ef4444' // Red - 91-100% used (almost empty)
}

const filamentUsedPercent = (item) => {
  if (!item || !item.weight_remaining_percent) return 0
  return 100 - item.weight_remaining_percent
}

const viewItem = (item) => {
  // Create array of filtered item IDs and find current position
  const filteredItemIds = props.items.map((i) => i.id)
  const currentIndex = filteredItemIds.indexOf(item.id)

  // Save to sessionStorage for navigation
  sessionStorage.setItem(
    'filamentNavState',
    JSON.stringify({
      filteredItemIds,
      currentIndex,
    }),
  )

  router.push({
    name: 'filament-spool-detail',
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
    :items="transformedItems"
    :visible-columns="visibleColumns"
    @row-click="viewItem"
  >
    <template #cell-brand="{ item }">
      {{ getSpoolBrand(item) }}
    </template>

    <template #cell-colors="{ item }">
      <div class="color-swatches">
        <span
          v-for="(color, index) in getSpoolColors(item)"
          :key="index"
          class="color-swatch"
          :style="{ backgroundColor: color }"
          :title="color"
          @click.stop="openColorSwatchModal(color)"
        ></span>
        <span
          v-if="getSpoolColors(item).length === 0"
          class="color-swatch"
          style="background-color: #cccccc"
          @click.stop="openColorSwatchModal('#cccccc')"
        ></span>
      </div>
    </template>

    <template #cell-name="{ item }">
      {{ getSpoolName(item) }}
      <span v-if="item.is_quick_add" class="quick-add-tag">QA</span>
    </template>

    <template #cell-material="{ item }">
      {{ getSpoolMaterial(item) }}
    </template>

    <template #cell-features="{ item }">
      <div v-if="getSpoolFeatures(item).length > 0" class="features-cell">
        <span v-for="feature in getSpoolFeatures(item)" :key="feature.id" class="feature-badge">
          {{ feature.name }}
        </span>
      </div>
      <span v-else>-</span>
    </template>

    <template #cell-quantity="{ item }">
      <!-- Show spool count for unopened (status=new), show grams for opened spools -->
      <span v-if="item.status === 'new'"
        >{{ item.quantity }} spool{{ item.quantity !== 1 ? 's' : '' }}</span
      >
      <span v-else>{{ item.current_weight ? `${item.current_weight}g` : 'N/A' }}</span>
    </template>

    <template #cell-status="{ item }">
      {{ getStatusLabel(item.status) }}
    </template>

    <template #cell-location="{ item }">
      <span v-if="item.assigned_printer">{{ item.assigned_printer.title }}</span>
      <span v-else-if="item.location">{{ item.location.name }}</span>
      <span v-else>-</span>
    </template>

    <template #cell-filamentUsed="{ item }">
      <div v-if="item.is_opened" class="progress-mini">
        <div
          class="progress-mini-bar"
          :style="{
            width: filamentUsedPercent(item) + '%',
            backgroundColor: getFilamentUsedColor(filamentUsedPercent(item)),
          }"
        ></div>
        <span class="progress-mini-text">{{ filamentUsedPercent(item).toFixed(0) }}%</span>
      </div>
      <span v-else class="progress-mini-text">-</span>
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
.color-swatches {
  display: flex;
  gap: 4px;
  align-items: center;
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

.quick-add-tag {
  display: inline-block;
  background-color: var(--color-background-mute);
  color: var(--color-text-muted);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-size: 0.65rem;
  font-weight: 600;
  margin-left: 0.5rem;
  vertical-align: middle;
}

.features-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.feature-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.125rem 0.5rem;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-text);
  white-space: nowrap;
}

.progress-mini {
  position: relative;
  width: 100px;
  height: 20px;
  background-color: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  display: inline-block;
}

.progress-mini-bar {
  height: 100%;
  transition:
    width 0.3s ease,
    background-color 0.3s ease;
}

.progress-mini-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.75rem;
  font-weight: 600;
  color: #1f2937;
  z-index: 1;
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
