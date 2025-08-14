<script setup>
import { ref, watch } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import APIService from '@/services/APIService.js'

const props = defineProps({
  initialData: { type: Object, required: true },
})

const router = useRouter()
const maintenanceData = ref({})

watch(
  () => props.initialData,
  (newData) => {
    if (newData) {
      // Only extract the fields we need for this form
      maintenanceData.value = {
        last_maintained_date: newData.last_maintained_date,
        maintenance_reminder_date: newData.maintenance_reminder_date,
        last_carbon_replacement_date: newData.last_carbon_replacement_date,
        carbon_reminder_date: newData.carbon_reminder_date,
        maintenance_notes: newData.maintenance_notes,
      }
    }
  },
  { immediate: true },
)

const saveMaintenance = async () => {
  try {
    // We use a PATCH request to only update these specific fields
    await APIService.updatePrinter(props.initialData.id, maintenanceData.value)
    router.push(`/printers/${props.initialData.id}`)
  } catch (error) {
    console.error('Error saving maintenance data:', error)
  }
}
</script>

<template>
  <form @submit.prevent="saveMaintenance" class="item-form">
    <h3>Maintenance</h3>
    <div class="form-group">
      <label for="last_maintained_date">Date of Last Maintenance</label>
      <input id="last_maintained_date" v-model="maintenanceData.last_maintained_date" type="date" />
    </div>
    <div class="form-group">
      <label for="maintenance_reminder_date">Maintenance Reminder</label>
      <input
        id="maintenance_reminder_date"
        v-model="maintenanceData.maintenance_reminder_date"
        type="date"
      />
    </div>
    <div class="form-group">
      <label for="last_carbon_replacement_date">Date of Last Carbon Filter Replacement</label>
      <input
        id="last_carbon_replacement_date"
        v-model="maintenanceData.last_carbon_replacement_date"
        type="date"
      />
    </div>
    <div class="form-group">
      <label for="carbon_reminder_date">Carbon Filter Reminder</label>
      <input id="carbon_reminder_date" v-model="maintenanceData.carbon_reminder_date" type="date" />
    </div>
    <div class="form-group">
      <label for="maintenance_notes">Maintenance Notes</label>
      <textarea id="maintenance_notes" v-model="maintenanceData.maintenance_notes"></textarea>
    </div>

    <div class="form-actions">
      <button type="submit" class="save-button">Save Maintenance</button>
      <RouterLink :to="`/printers/${initialData.id}`" class="cancel-button">Cancel</RouterLink>
    </div>
  </form>
</template>

<style scoped>
/* Using a scoped version of the item-form styles */
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
input[type='date'],
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
</style>
