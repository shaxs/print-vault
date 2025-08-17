<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import APIService from '@/services/APIService.js'
import Multiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'

const props = defineProps({
  initialData: { type: Object, default: null },
})

const router = useRouter()
const item = ref({})
const isEditMode = ref(false)
const photoFile = ref(null)
const photoPreview = ref(null)

const allProjects = ref([])
const partTypes = ref([])
const brands = ref([])
const locations = ref([])

watch(
  () => props.initialData,
  (newData) => {
    if (newData) {
      item.value = {
        ...newData,
        is_consumable: newData.is_consumable || false,
        low_stock_threshold:
          newData.low_stock_threshold === null ? null : newData.low_stock_threshold,
      }
      item.value.project_ids = newData.associated_projects?.map((p) => p.id) || []
      isEditMode.value = true
    } else {
      item.value = {
        title: '',
        brand: null,
        part_type: null,
        location: null,
        quantity: 1,
        cost: null,
        notes: '',
        project_ids: [],
        is_consumable: false,
        low_stock_threshold: null,
      }
      isEditMode.value = false
    }
  },
  { immediate: true, deep: true },
)

watch(
  () => item.value.is_consumable,
  (isConsumable) => {
    if (!isConsumable) {
      item.value.low_stock_threshold = null
    } else if (item.value.low_stock_threshold === null) {
      item.value.low_stock_threshold = 0
    }
  },
)

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    photoFile.value = file
    photoPreview.value = URL.createObjectURL(file)
  }
}

const saveItem = async () => {
  const formData = new FormData()
  formData.append('title', item.value.title || '')
  formData.append('quantity', item.value.quantity || 0)
  if (item.value.cost) formData.append('cost', item.value.cost)
  if (item.value.notes) formData.append('notes', item.value.notes)
  formData.append('is_consumable', item.value.is_consumable)
  if (item.value.is_consumable && item.value.low_stock_threshold !== null) {
    formData.append('low_stock_threshold', item.value.low_stock_threshold)
  }

  const brandName = item.value.brand?.name || item.value.brand
  if (brandName) formData.append('brand', JSON.stringify({ name: brandName }))

  const partTypeName = item.value.part_type?.name || item.value.part_type
  if (partTypeName) formData.append('part_type', JSON.stringify({ name: partTypeName }))

  const locationName = item.value.location?.name || item.value.location
  if (locationName) formData.append('location', JSON.stringify({ name: locationName }))

  if (item.value.project_ids) {
    item.value.project_ids.forEach((id) => formData.append('project_ids', id))
  }

  if (photoFile.value) {
    formData.append('photo', photoFile.value)
  }

  try {
    let savedItem
    if (isEditMode.value) {
      savedItem = await APIService.updateInventoryItem(item.value.id, formData)
    } else {
      savedItem = await APIService.createInventoryItem(formData)
    }
    router.push(`/item/${savedItem.data.id}`)
  } catch (error) {
    console.error('There was an error saving the item:', error)
  }
}

const addBrand = (newBrand) => {
  const brand = { name: newBrand }
  brands.value.push(brand)
  item.value.brand = brand
}
const addPartType = (newPartType) => {
  const partType = { name: newPartType }
  partTypes.value.push(partType)
  item.value.part_type = partType
}
const addLocation = (newLocation) => {
  const location = { name: newLocation }
  locations.value.push(location)
  item.value.location = location
}
const addProject = async (newProjectName) => {
  try {
    const newProjectData = { project_name: newProjectName, status: 'Planning' }
    const response = await APIService.createProject(newProjectData)
    const newProject = response.data
    allProjects.value.push(newProject)
    item.value.project_ids.push(newProject.id)
  } catch (error) {
    console.error('Error creating new project:', error)
  }
}

onMounted(async () => {
  try {
    const [partTypesRes, brandsRes, locationsRes, projectsRes] = await Promise.all([
      APIService.getPartTypes(),
      APIService.getBrands(),
      APIService.getLocations(),
      APIService.getProjects(),
    ])
    partTypes.value = partTypesRes.data
    brands.value = brandsRes.data
    locations.value = locationsRes.data
    allProjects.value = projectsRes.data
  } catch (error) {
    console.error('Error loading form options:', error)
  }
})
</script>

<template>
  <form @submit.prevent="saveItem" class="item-form">
    <div class="form-group">
      <label for="title">Title</label>
      <input id="title" v-model="item.title" type="text" required />
    </div>

    <div class="form-group">
      <label for="project_ids">Associated Projects</label>
      <multiselect
        v-model="item.project_ids"
        :options="allProjects.map((p) => p.id)"
        :custom-label="(opt) => allProjects.find((p) => p.id === opt)?.project_name || ''"
        :multiple="true"
        :taggable="true"
        @tag="addProject"
        placeholder="Select or type to add a new project"
      ></multiselect>
    </div>

    <div class="form-group">
      <label for="brand">Brand</label>
      <multiselect
        id="brand"
        v-model="item.brand"
        :options="brands"
        label="name"
        track-by="name"
        placeholder="Select or type to add brand"
        :taggable="true"
        @tag="addBrand"
      ></multiselect>
    </div>

    <div class="form-group">
      <label for="part_type">Part Type</label>
      <multiselect
        id="part_type"
        v-model="item.part_type"
        :options="partTypes"
        label="name"
        track-by="name"
        placeholder="Select or type to add part type"
        :taggable="true"
        @tag="addPartType"
      ></multiselect>
    </div>

    <div class="form-group">
      <label for="location">Location</label>
      <multiselect
        id="location"
        v-model="item.location"
        :options="locations"
        label="name"
        track-by="name"
        placeholder="Select or type to add location"
        :taggable="true"
        @tag="addLocation"
      ></multiselect>
    </div>

    <div class="form-group">
      <label for="quantity">Quantity</label>
      <input id="quantity" v-model.number="item.quantity" type="number" min="0" />
    </div>

    <div class="form-group">
      <label for="cost">Cost</label>
      <input id="cost" v-model.number="item.cost" type="number" step="0.01" />
    </div>

    <div class="form-group">
      <label for="photo">Photo</label>
      <input id="photo" type="file" @change="handleFileUpload" accept="image/*" />
      <div v-if="photoPreview || (isEditMode && item.photo)" class="photo-preview">
        <img :src="photoPreview || item.photo" alt="Item preview" />
      </div>
    </div>

    <div class="form-group">
      <label for="notes">Notes</label>
      <textarea id="notes" v-model="item.notes"></textarea>
    </div>

    <div class="form-group checkbox-group">
      <input id="is_consumable" type="checkbox" v-model="item.is_consumable" />
      <label for="is_consumable">Enable Low Stock Alert</label>
    </div>

    <div v-if="item.is_consumable" class="form-group">
      <label for="low_stock_threshold">Low Stock Warning Level</label>
      <input
        id="low_stock_threshold"
        type="number"
        v-model.number="item.low_stock_threshold"
        min="0"
        placeholder="e.g., 5"
      />
    </div>

    <div class="form-actions">
      <button type="submit" class="save-button">Save</button>
      <RouterLink :to="isEditMode ? `/item/${item.id}` : '/'" class="cancel-button"
        >Cancel</RouterLink
      >
    </div>
  </form>
</template>

<style>
/* Styles are unchanged */
.item-form {
  max-width: 500px;
  margin: 20px auto;
  padding: 20px;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}
.form-group {
  margin-bottom: 1.5rem;
}
label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
  color: var(--color-heading);
}
input[type='text'],
input[type='number'],
input[type='file'],
textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-sizing: border-box;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
}
.photo-preview {
  margin-top: 15px;
}
.photo-preview img {
  max-width: 200px;
  max-height: 200px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
.save-button,
.cancel-button {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  text-decoration: none;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
}
.save-button {
  background-color: var(--color-blue);
  color: white;
}
.cancel-button {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
  border: 1px solid var(--color-border);
}
.multiselect__tags,
.multiselect__input {
  background: var(--color-background);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}
.multiselect__single {
  background: var(--color-background);
  color: var(--color-text);
}
.multiselect__content-wrapper {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
}
.multiselect__option {
  color: var(--color-text);
}
.multiselect__option--highlight {
  background: var(--color-blue);
}
.multiselect__option--selected {
  background: var(--color-background-mute);
}
.multiselect__tag {
  background: var(--color-blue);
}
.checkbox-group {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
}
.checkbox-group input {
  width: auto;
}
.checkbox-group label {
  margin-bottom: 0;
  font-weight: normal;
  user-select: none;
  cursor: pointer;
}
</style>
