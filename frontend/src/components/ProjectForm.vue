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
const project = ref({})
const isEditMode = ref(false)
const photoFile = ref(null)
const photoPreview = ref(null)
const allInventoryItems = ref([])
const allPrinters = ref([])
const allTrackers = ref([])
const materialBlueprints = ref([])
const projectMaterials = ref([])

watch(
  () => props.initialData,
  (newData) => {
    if (newData) {
      project.value = { ...newData }
      project.value.inventory_item_ids = newData.associated_inventory_items.map((item) => item.id)
      project.value.printer_ids = newData.associated_printers.map((printer) => printer.id)
      project.value.tracker_ids = newData.trackers
        ? newData.trackers.map((tracker) => tracker.id)
        : []
      
      // Initialize materials with mode tracking
      projectMaterials.value = (newData.materials_display || newData.materials || []).map(mat => ({
        label: mat.label || '',
        custom_color: mat.custom_color || '',
        blueprint_obj: mat.blueprint || null,
        mode: mat.blueprint || mat.blueprint_id ? 'blueprint' : 'custom'
      }))
      
      isEditMode.value = true
    } else {
      project.value = {
        project_name: '',
        description: '',
        status: 'Planning',
        start_date: null,
        due_date: null,
        notes: '',
        inventory_item_ids: [],
        printer_ids: [],
        tracker_ids: [],
      }
      projectMaterials.value = []
      isEditMode.value = false
    }
  },
  { immediate: true },
)

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    photoFile.value = file
    photoPreview.value = URL.createObjectURL(file)
  }
}

const addMaterial = () => {
  projectMaterials.value.push({
    label: '',
    custom_color: '',
    blueprint_obj: null,
    mode: 'custom'
  })
}

const removeMaterial = (index) => {
  projectMaterials.value.splice(index, 1)
}

const formatMaterialName = (material) => {
  if (!material) return ''
  const brandName = material.brand?.name || ''
  const diameter = material.diameter ? ` (${material.diameter}mm)` : ''
  return `${brandName} ${material.name}${diameter}`.trim()
}

const saveProject = async () => {
  const formData = new FormData()
  for (const key in project.value) {
    if (key === 'inventory_item_ids' || key === 'printer_ids' || key === 'tracker_ids') {
      project.value[key].forEach((id) => {
        formData.append(key, id)
      })
    } else if (key !== 'photo' && project.value[key] !== null && project.value[key] !== undefined) {
      formData.append(key, project.value[key])
    }
  }

  if (photoFile.value) {
    formData.append('photo', photoFile.value)
  }

  // Add materials as JSON
  const materialsData = projectMaterials.value.map(mat => ({
    label: mat.label,
    custom_color: mat.mode === 'custom' ? mat.custom_color : '',
    blueprint_id: mat.mode === 'blueprint' && mat.blueprint_obj ? mat.blueprint_obj.id : null
  }))
  formData.append('materials', JSON.stringify(materialsData))

  try {
    let savedProject
    if (isEditMode.value) {
      savedProject = await APIService.updateProject(project.value.id, formData)
    } else {
      savedProject = await APIService.createProject(formData)
    }
    router.push(`/projects/${savedProject.data.id}`)
  } catch (error) {
    console.error('Error saving project:', error)
  }
}

onMounted(async () => {
  try {
    const [itemsRes, printersRes, trackersRes, materialsRes] = await Promise.all([
      APIService.getInventoryItems(),
      APIService.getPrinters(),
      APIService.getTrackers(),
      APIService.getMaterials({ type: 'blueprint' }),
    ])
    allInventoryItems.value = itemsRes.data
    allPrinters.value = printersRes.data
    allTrackers.value = trackersRes.data
    materialBlueprints.value = materialsRes.data
  } catch (error) {
    console.error('Error loading form options:', error)
  }
})
</script>

<template>
  <form @submit.prevent="saveProject" class="item-form">
    <div class="form-group">
      <label for="project_name">Project Name</label>
      <input id="project_name" v-model="project.project_name" type="text" required />
    </div>
    <div class="form-group">
      <label for="status">Status</label>
      <select id="status" v-model="project.status">
        <option>Planning</option>
        <option>In Progress</option>
        <option>Completed</option>
        <option>Canceled</option>
        <option>On Hold</option>
      </select>
    </div>
    <div class="form-group">
      <label for="start_date">Start Date</label>
      <input id="start_date" v-model="project.start_date" type="date" />
    </div>
    <div class="form-group">
      <label for="due_date">Due Date</label>
      <input id="due_date" v-model="project.due_date" type="date" />
      <p class="help-text">Set a deadline for this project to track due dates on the dashboard</p>
    </div>
    <div class="form-group">
      <label for="description">Description</label>
      <textarea id="description" v-model="project.description"></textarea>
    </div>
    <div class="form-group">
      <label for="inventory_item_ids">Associated Inventory Items</label>
      <multiselect
        v-model="project.inventory_item_ids"
        :options="allInventoryItems.map((item) => item.id)"
        :custom-label="(opt) => allInventoryItems.find((item) => item.id === opt)?.title || ''"
        :multiple="true"
        placeholder="Select parts for this project"
      ></multiselect>
    </div>
    <div class="form-group">
      <label for="printer_ids">Associated Printers</label>
      <multiselect
        v-model="project.printer_ids"
        :options="allPrinters.map((p) => p.id)"
        :custom-label="(opt) => allPrinters.find((p) => p.id === opt)?.title || ''"
        :multiple="true"
        placeholder="Select printers for this project"
      ></multiselect>
    </div>
    <div class="form-group">
      <label for="tracker_ids">Associated Print Trackers</label>
      <multiselect
        v-model="project.tracker_ids"
        :options="allTrackers.map((t) => t.id)"
        :custom-label="(opt) => allTrackers.find((t) => t.id === opt)?.name || ''"
        :multiple="true"
        placeholder="Select print trackers for this project"
      ></multiselect>
    </div>

    <!-- Materials Section -->
    <div class="materials-section">
      <h4>Materials</h4>
      <div v-for="(material, index) in projectMaterials" :key="index" class="material-entry">
        <div class="form-group">
          <label>Label</label>
          <input 
            v-model="material.label"
            type="text"
            placeholder="e.g., Primary, Accent, Support"
          />
        </div>

        <div class="form-group">
          <label>Material/Blueprint</label>
          <div class="radio-group">
            <label>
              <input 
                type="radio" 
                :name="`material-mode-${index}`"
                value="custom"
                v-model="material.mode"
              />
              Custom Material
            </label>
            <label>
              <input 
                type="radio" 
                :name="`material-mode-${index}`"
                value="blueprint"
                v-model="material.mode"
              />
              Material Blueprint
            </label>
          </div>
        </div>

        <div v-if="material.mode === 'custom'" class="form-group">
          <label>Custom Material</label>
          <input 
            v-model="material.custom_color"
            type="text"
            placeholder="e.g., Red ASA, Blue ABS, Transparent PETG"
          />
        </div>

        <div v-else class="form-group">
          <label>Select Blueprint</label>
          <multiselect
            v-model="material.blueprint_obj"
            :options="materialBlueprints"
            :custom-label="formatMaterialName"
            track-by="id"
            placeholder="Select material blueprint"
            :show-no-results="false"
          ></multiselect>
        </div>

        <button 
          type="button" 
          class="btn btn-danger btn-small"
          @click="removeMaterial(index)"
        >
          Remove Material
        </button>
      </div>

      <button 
        type="button" 
        class="btn btn-secondary add-material-btn"
        @click="addMaterial"
      >
        + Add Material
      </button>
    </div>

    <div class="form-group">
      <label for="photo">Photo / Render</label>
      <input id="photo" type="file" @change="handleFileUpload" accept="image/*" />
      <div v-if="photoPreview || (isEditMode && project.photo)" class="photo-preview">
        <img :src="photoPreview || project.photo" alt="Project preview" />
      </div>
    </div>
    <div class="form-group">
      <label for="notes">Notes</label>
      <textarea id="notes" v-model="project.notes"></textarea>
    </div>
    <div class="form-actions">
      <button type="submit" class="btn btn-primary">Save Project</button>
      <RouterLink
        :to="isEditMode ? `/projects/${project.id}` : '/projects'"
        class="btn btn-secondary"
      >
        Cancel
      </RouterLink>
    </div>
  </form>
</template>

<style>
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
.help-text {
  font-size: 0.875rem;
  color: var(--color-text-soft);
  margin-top: 6px;
  margin-bottom: 0;
}
input[type='text'],
input[type='number'],
input[type='url'],
input[type='email'],
input[type='password'],
input[type='date'],
input[type='file'],
textarea,
select {
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
/* No placeholder comment; all styles below remain unchanged */
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

/* Materials Section Styling */
.materials-section {
  margin-bottom: 1.5rem;
  padding: 1rem 0;
}

.materials-section h4 {
  color: var(--color-heading);
  margin-bottom: 1rem;
  font-size: 1.1rem;
}

.material-entry {
  padding: 0;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 1.5rem;
}

.material-entry:last-child {
  border-bottom: none;
}

.radio-group {
  display: flex;
  gap: 1.5rem;
  margin-top: 0.5rem;
}

.radio-group label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: normal;
  cursor: pointer;
}

.radio-group input[type="radio"] {
  width: auto;
  cursor: pointer;
}

.btn-small {
  padding: 6px 12px;
  font-size: 0.875rem;
}

.btn-danger {
  background-color: var(--color-error, #dc3545);
  color: white;
  border: none;
}

.btn-danger:hover {
  background-color: var(--color-error-dark, #c82333);
}

.add-material-btn {
  margin-bottom: 2rem;
}
</style>
