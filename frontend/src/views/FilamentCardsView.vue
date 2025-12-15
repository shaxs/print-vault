<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import APIService from '../services/APIService'
import MainHeader from '../components/MainHeader.vue'

const spools = ref([])
const searchText = ref('')
const statusFilter = ref('')
const isLoading = ref(false)

const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'new', label: 'New (Unopened)' },
  { value: 'opened', label: 'Opened' },
  { value: 'in_use', label: 'In Use' },
  { value: 'low', label: 'Low' },
  { value: 'empty', label: 'Empty' },
  { value: 'archived', label: 'Archived' },
]

const getStatusClass = (status) => {
  const statusMap = {
    new: 'status-new',
    opened: 'status-opened',
    in_use: 'status-in-use',
    low: 'status-low',
    empty: 'status-empty',
    archived: 'status-archived',
  }
  return statusMap[status] || ''
}

const getStatusLabel = (status) => {
  const option = statusOptions.find((opt) => opt.value === status)
  return option ? option.label.replace(' (Unopened)', '') : status
}

const loadSpools = async () => {
  isLoading.value = true
  try {
    const params = {}
    if (searchText.value) params.search = searchText.value
    if (statusFilter.value) params.status = statusFilter.value

    const response = await APIService.getFilamentSpools(params)
    spools.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to load filament spools:', error)
  } finally {
    isLoading.value = false
  }
}

const filteredSpools = computed(() => {
  let filtered = spools.value

  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    filtered = filtered.filter(
      (spool) =>
        spool.filament_type?.color_name?.toLowerCase().includes(search) ||
        spool.filament_type?.name.toLowerCase().includes(search) ||
        spool.filament_type?.brand?.name.toLowerCase().includes(search),
    )
  }

  if (statusFilter.value) {
    filtered = filtered.filter((spool) => spool.status === statusFilter.value)
  }

  return filtered
})

watch([searchText, statusFilter], () => {
  loadSpools()
})

onMounted(() => {
  loadSpools()
})
</script>

<template>
  <main>
    <MainHeader
      title="Filament Spools"
      createUrl="/filaments/create"
      v-model="searchText"
      :showFilterButton="false"
      :showColumnButton="false"
    />

    <div class="controls-bar">
      <div class="status-filter">
        <label for="status-filter">Status:</label>
        <select id="status-filter" v-model="statusFilter">
          <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </div>
      <RouterLink to="/filaments/materials" class="btn-secondary">
        Manage Material Library
      </RouterLink>
    </div>

    <div v-if="isLoading" class="loading-message">Loading spools...</div>

    <div v-else-if="filteredSpools.length === 0" class="empty-state">
      <p>No filament spools found.</p>
      <RouterLink to="/filaments/create" class="btn-primary">Add Your First Spool</RouterLink>
    </div>

    <div v-else class="spools-grid">
      <RouterLink
        v-for="spool in filteredSpools"
        :key="spool.id"
        :to="`/filaments/${spool.id}`"
        class="spool-card"
      >
        <div class="spool-header">
          <div class="color-swatches">
            <div
              v-for="(colorHex, idx) in spool.filament_type?.colors || []"
              :key="idx"
              class="color-swatch"
              :style="{ backgroundColor: colorHex || '#cccccc' }"
              :title="spool.filament_type?.name"
            ></div>
            <div
              v-if="!spool.filament_type?.colors || spool.filament_type.colors.length === 0"
              class="color-swatch"
              style="background-color: #cccccc"
            ></div>
          </div>
          <div class="spool-title">
            <h3>{{ spool.filament_type?.name || 'Unknown Color' }}</h3>
            <p class="material-name">
              {{ spool.filament_type?.brand?.name }}
              {{ spool.filament_type?.base_material_type?.name }}
            </p>
          </div>
        </div>

        <div class="spool-details">
          <div v-if="spool.is_opened" class="detail-row">
            <span class="label">Weight:</span>
            <span class="value">
              {{ spool.current_weight }}g / {{ spool.initial_weight }}g
              <span class="percentage">({{ spool.weight_remaining_percent?.toFixed(0) }}%)</span>
            </span>
          </div>
          <div v-else class="detail-row">
            <span class="label">Quantity:</span>
            <span class="value">{{ spool.quantity }} unopened spool(s)</span>
          </div>

          <div v-if="spool.location" class="detail-row">
            <span class="label">Location:</span>
            <span class="value">{{ spool.location.name }}</span>
          </div>

          <div v-if="spool.assigned_printer" class="detail-row">
            <span class="label">Printer:</span>
            <span class="value">{{ spool.assigned_printer.name }}</span>
          </div>

          <div class="detail-row">
            <span :class="['status-badge', getStatusClass(spool.status)]">
              {{ getStatusLabel(spool.status) }}
            </span>
          </div>
        </div>
      </RouterLink>
    </div>
  </main>
</template>

<style scoped>
.controls-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.status-filter {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-filter label {
  font-weight: 600;
  color: var(--color-text);
}

.status-filter select {
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  font-size: 1rem;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  background: none;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  color: var(--color-text);
  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  border-color: var(--color-border-hover);
  background-color: var(--color-background-mute);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  padding: 0.75rem 1.5rem;
  background-color: var(--color-blue);
  color: white;
  text-decoration: none;
  border-radius: 5px;
  font-weight: 600;
  transition: background-color 0.2s ease;
}

.btn-primary:hover {
  background-color: #0b5ed7;
}

.loading-message {
  text-align: center;
  padding: 2rem;
  color: var(--color-text-muted);
  font-style: italic;
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--color-text-muted);
}

.empty-state p {
  margin-bottom: 1.5rem;
  font-size: 1.1rem;
}

.spools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.spool-card {
  display: block;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.25rem;
  text-decoration: none;
  color: var(--color-text);
  transition: all 0.2s ease;
}

.spool-card:hover {
  border-color: var(--color-border-hover);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.spool-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.color-swatches {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.color-swatch {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  border: 2px solid var(--color-border);
  flex-shrink: 0;
}

.spool-title h3 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--color-heading);
}

.material-name {
  margin: 0.25rem 0 0 0;
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

.spool-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9rem;
}

.detail-row .label {
  font-weight: 600;
  color: var(--color-text-muted);
}

.detail-row .value {
  color: var(--color-text);
  text-align: right;
}

.percentage {
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-new {
  background-color: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.status-opened {
  background-color: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.status-in-use {
  background-color: rgba(168, 85, 247, 0.1);
  color: #a855f7;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

.status-low {
  background-color: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.status-empty {
  background-color: rgba(107, 114, 128, 0.1);
  color: #6b7280;
  border: 1px solid rgba(107, 114, 128, 0.3);
}

.status-archived {
  background-color: rgba(107, 114, 128, 0.1);
  color: #6b7280;
  border: 1px solid rgba(107, 114, 128, 0.3);
  text-decoration: line-through;
}

@media (max-width: 768px) {
  .spools-grid {
    grid-template-columns: 1fr;
  }

  .controls-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .status-filter {
    justify-content: space-between;
  }
}
</style>
