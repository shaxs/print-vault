<script setup>
import { ref, onMounted, computed } from 'vue'
import APIService from '../services/APIService'
import MainHeader from '../components/MainHeader.vue'

const props = defineProps({
  embedded: { type: Boolean, default: false },
})

const materials = ref([])
const searchText = ref('')
const typeFilter = ref('blueprint')
const favoritesOnly = ref(false)
const isLoading = ref(false)

const loadMaterials = async () => {
  isLoading.value = true
  try {
    const params = { type: typeFilter.value }
    if (searchText.value) params.search = searchText.value
    if (favoritesOnly.value) params.favorites = true

    const response = await APIService.getMaterials(params)
    materials.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to load materials:', error)
  } finally {
    isLoading.value = false
  }
}

const toggleFavorite = async (material) => {
  try {
    // Need to add this method to APIService or use axios directly with relative URL
    const apiClient = (await import('axios')).default
    const response = await apiClient.post(`/api/materials/${material.id}/toggle-favorite/`)
    // Update local state
    material.is_favorite = response.data.is_favorite
    material.favorite_order = response.data.favorite_order
    // Reload to get correct ordering
    await loadMaterials()
  } catch (error) {
    console.error('Failed to toggle favorite:', error)
    if (error.response?.data?.error) {
      alert(error.response.data.error)
    }
  }
}

const filteredMaterials = computed(() => {
  return materials.value
})

onMounted(() => {
  loadMaterials()
})
</script>

<template>
  <main :class="{ embedded: embedded }">
    <MainHeader
      v-if="!embedded"
      title="Material Library"
      createUrl="/filaments/materials/create"
      v-model="searchText"
      :showFilterButton="false"
      :showColumnButton="false"
      @update:modelValue="loadMaterials"
    />

    <div class="controls-bar">
      <div class="type-filter">
        <label for="type-filter">Type:</label>
        <select id="type-filter" v-model="typeFilter" @change="loadMaterials">
          <option value="blueprint">Blueprints (Brand-Specific)</option>
          <option value="generic">Generic Materials</option>
        </select>
      </div>
      <div class="favorites-toggle">
        <label>
          <input type="checkbox" v-model="favoritesOnly" @change="loadMaterials" />
          Show Favorites Only
        </label>
      </div>
      <RouterLink to="/filaments" class="btn-secondary">View Spools</RouterLink>
    </div>

    <div v-if="isLoading" class="loading-message">Loading materials...</div>

    <div v-else-if="filteredMaterials.length === 0" class="empty-state">
      <p>No materials found.</p>
      <RouterLink to="/filaments/materials/create" class="btn-primary">
        Add Your First Material
      </RouterLink>
    </div>

    <div v-else class="materials-grid">
      <div v-for="material in filteredMaterials" :key="material.id" class="material-card">
        <div class="card-header">
          <div class="title-row">
            <h3>{{ material.name }}</h3>
            <button
              v-if="material.is_generic === false"
              @click.prevent="toggleFavorite(material)"
              class="favorite-btn"
              :class="{ active: material.is_favorite }"
            >
              {{ material.is_favorite ? '★' : '☆' }}
            </button>
          </div>
          <p v-if="material.brand" class="brand-name">{{ material.brand.name }}</p>
          <div v-if="material.colors && material.colors.length > 0" class="color-info">
            <div class="color-swatches">
              <div
                v-for="(colorHex, idx) in material.colors"
                :key="idx"
                class="color-swatch"
                :style="{ backgroundColor: colorHex || '#cccccc' }"
              ></div>
            </div>
            <span v-if="material.colors.length > 1" class="multi-color-label">
              Multi-Color ({{ material.colors.length }} colors)
            </span>
          </div>
        </div>

        <div v-if="material.photo" class="material-photo">
          <img :src="material.photo" :alt="material.name" />
        </div>

        <div class="material-details">
          <div v-if="material.base_material" class="detail-row">
            <span class="label">Base Material:</span>
            <span class="value">{{ material.base_material.name }}</span>
          </div>

          <div v-if="material.diameter" class="detail-row">
            <span class="label">Diameter:</span>
            <span class="value">{{ material.diameter }}mm</span>
          </div>

          <div v-if="material.spool_weight" class="detail-row">
            <span class="label">Spool Weight:</span>
            <span class="value">{{ material.spool_weight }}g</span>
          </div>

          <div v-if="material.price_per_spool" class="detail-row">
            <span class="label">Price:</span>
            <span class="value">${{ material.price_per_spool }}</span>
          </div>

          <div class="detail-row">
            <span class="label">Total Spools:</span>
            <span class="value">{{ material.total_spool_count || 0 }}</span>
          </div>

          <div class="detail-row">
            <span class="label">Available Weight:</span>
            <span class="value">{{ material.total_available_grams || 0 }}g</span>
          </div>

          <div v-if="material.total_inventory_value" class="detail-row">
            <span class="label">Total Value:</span>
            <span class="value">${{ material.total_inventory_value }}</span>
          </div>

          <div v-if="material.is_low_stock" class="low-stock-warning">⚠️ Low Stock</div>
        </div>

        <div class="card-actions">
          <RouterLink :to="`/filaments/materials/${material.id}/edit`" class="btn-edit">
            Edit
          </RouterLink>
          <button
            v-if="material.is_generic === false"
            @click="$router.push(`/filaments/create?materialId=${material.id}`)"
            class="btn-add-spool"
          >
            Add Spool
          </button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
main {
  padding: 0;
}

main.embedded {
  padding: 0;
  margin: 0;
}

.controls-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.type-filter,
.favorites-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.type-filter label,
.favorites-toggle label {
  font-weight: 600;
  color: var(--color-text);
  cursor: pointer;
}

.type-filter select {
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  font-size: 1rem;
}

.favorites-toggle input[type='checkbox'] {
  cursor: pointer;
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

.materials-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.material-card {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  transition: all 0.2s ease;
}

.material-card:hover {
  border-color: var(--color-border-hover);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.75rem;
}

.color-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.5rem;
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.color-swatches {
  display: flex;
  gap: 0.25rem;
}

.color-swatch {
  width: 30px;
  height: 30px;
  border-radius: 4px;
  border: 1px solid var(--color-border);
  flex-shrink: 0;
}

.multi-color-label {
  font-size: 0.85rem;
  font-style: italic;
}

.secondary-color {
  font-style: italic;
}

.title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-row h3 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--color-heading);
}

.favorite-btn {
  background: none;
  border: none;
  font-size: 1.75rem;
  cursor: pointer;
  color: var(--color-text-muted);
  transition: all 0.2s ease;
  line-height: 1;
  padding: 0;
}

.favorite-btn.active {
  color: #f59e0b;
}

.favorite-btn:hover {
  transform: scale(1.2);
}

.brand-name {
  margin: 0.25rem 0 0 0;
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

.material-photo {
  width: 100%;
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-background-mute);
  border-radius: 6px;
  overflow: hidden;
}

.material-photo img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.material-details {
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

.low-stock-warning {
  padding: 0.5rem;
  background-color: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 5px;
  color: #f59e0b;
  text-align: center;
  font-weight: 600;
  font-size: 0.875rem;
}

.card-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: auto;
}

.btn-edit,
.btn-add-spool {
  flex: 1;
  padding: 0.5rem;
  border-radius: 5px;
  text-align: center;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s ease;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-edit {
  background: none;
  border: 1px solid var(--color-border);
  color: var(--color-text);
  display: block;
}

.btn-edit:hover {
  border-color: var(--color-border-hover);
  background-color: var(--color-background-mute);
}

.btn-add-spool {
  background-color: var(--color-blue);
  color: white;
  border: 1px solid var(--color-blue);
}

.btn-add-spool:hover {
  background-color: #0b5ed7;
}

@media (max-width: 768px) {
  .materials-grid {
    grid-template-columns: 1fr;
  }

  .controls-bar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
