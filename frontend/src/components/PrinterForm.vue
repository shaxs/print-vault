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
const printer = ref({})
const isEditMode = ref(false)
const photoFile = ref(null)
const photoPreview = ref(null)
const brands = ref([])

watch(
  () => props.initialData,
  (newData) => {
    if (newData) {
      printer.value = { ...newData }
      isEditMode.value = true
    } else {
      printer.value = {
        title: '',
        manufacturer: null,
        serial_number: '',
        purchase_date: null,
        status: 'Active',
        notes: '',
        build_size_x: null,
        build_size_y: null,
        build_size_z: null,
        purchase_price: null,
      }
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

const savePrinter = async () => {
  const formData = new FormData()
  const fieldsToAppend = [
    'title',
    'serial_number',
    'purchase_date',
    'status',
    'notes',
    'build_size_x',
    'build_size_y',
    'build_size_z',
    'purchase_price',
  ]
  fieldsToAppend.forEach((key) => {
    if (
      printer.value[key] !== null &&
      printer.value[key] !== undefined &&
      printer.value[key] !== ''
    ) {
      formData.append(key, printer.value[key])
    }
  })

  const brandValue = printer.value.manufacturer
  if (brandValue) {
    const brandName =
      typeof brandValue === 'object' && brandValue !== null ? brandValue.name : brandValue
    formData.append('manufacturer', JSON.stringify({ name: brandName }))
  } else if (isEditMode.value && brandValue === null) {
    formData.append('manufacturer', JSON.stringify(null))
  }

  if (photoFile.value) {
    formData.append('photo', photoFile.value)
  }

  try {
    let savedPrinter
    if (isEditMode.value) {
      savedPrinter = await APIService.updatePrinter(printer.value.id, formData)
    } else {
      savedPrinter = await APIService.createPrinter(formData)
    }
    router.push(`/printers/${savedPrinter.data.id}`)
  } catch (error) {
    console.error('Error saving printer:', error)
  }
}

const addBrand = (newBrand) => {
  const brand = { name: newBrand }
  brands.value.push(brand)
  printer.value.manufacturer = brand
}

onMounted(async () => {
  try {
    const response = await APIService.getBrands()
    brands.value = response.data
  } catch (error) {
    console.error('Error loading brands:', error)
  }
})
</script>

<template>
  <form @submit.prevent="savePrinter" class="item-form">
    <div class="form-group">
      <label for="title">Title</label>
      <input id="title" v-model="printer.title" type="text" required />
    </div>

    <div class="form-group">
      <label for="manufacturer">Manufacturer (Brand)</label>
      <multiselect
        id="manufacturer"
        v-model="printer.manufacturer"
        :options="brands"
        label="name"
        track-by="name"
        placeholder="Select or type to add brand"
        :taggable="true"
        @tag="addBrand"
      ></multiselect>
    </div>

    <div class="form-group">
      <label for="serial_number">Serial Number</label>
      <input id="serial_number" v-model="printer.serial_number" type="text" />
    </div>

    <div class="form-group">
      <label for="purchase_price">Purchase Price</label>
      <input
        id="purchase_price"
        v-model.number="printer.purchase_price"
        type="number"
        step="0.01"
      />
    </div>

    <div class="form-group">
      <label for="purchase_date">Purchase Date</label>
      <input id="purchase_date" v-model="printer.purchase_date" type="date" />
    </div>

    <div class="form-group">
      <label for="status">Status</label>
      <select id="status" v-model="printer.status">
        <option>Active</option>
        <option>Under Repair</option>
        <option>Sold</option>
        <option>Archived</option>
        <option>Planned</option>
      </select>
    </div>

    <div class="form-group">
      <label>Build Volume (X, Y, Z in mm)</label>
      <div class="multi-input">
        <input v-model.number="printer.build_size_x" type="number" placeholder="X" />
        <input v-model.number="printer.build_size_y" type="number" placeholder="Y" />
        <input v-model.number="printer.build_size_z" type="number" placeholder="Z" />
      </div>
    </div>

    <div class="form-group">
      <label for="photo">Photo</label>
      <input id="photo" type="file" @change="handleFileUpload" accept="image/*" />
      <div v-if="photoPreview || (isEditMode && printer.photo)" class="photo-preview">
        <img :src="photoPreview || printer.photo" alt="Printer preview" />
      </div>
    </div>

    <div class="form-group">
      <label for="notes">Notes</label>
      <textarea id="notes" v-model="printer.notes" rows="6"></textarea>
    </div>

    <div class="form-actions">
      <button type="submit" class="btn btn-primary">Save Printer Details</button>
      <RouterLink
        :to="isEditMode ? `/printers/${printer.id}` : '/printers'"
        class="btn btn-secondary"
      >
        Cancel
      </RouterLink>
    </div>
  </form>
</template>

<style>
/* Reusing styles from InventoryForm, so no need to be scoped */
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
.multi-input {
  display: flex;
  gap: 10px;
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
/* Removed custom button styles; use global .btn classes */
/* Multiselect dark theme override */
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
</style>
