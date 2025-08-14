<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import APIService from '@/services/APIService.js'
import BaseModal from '@/components/BaseModal.vue'

const router = useRouter()
const reminders = ref([])
const isModalVisible = ref(false)

const reminderCount = computed(() => reminders.value.length)

const fetchReminders = async () => {
  try {
    const response = await APIService.getReminders()
    const printersWithReminders = response.data

    // Process the printers into a flat list of individual reminders
    const processedReminders = []
    const today = new Date().setHours(0, 0, 0, 0)

    printersWithReminders.forEach((printer) => {
      const maintenanceDate = printer.maintenance_reminder_date
        ? new Date(printer.maintenance_reminder_date).setHours(0, 0, 0, 0)
        : null
      const carbonDate = printer.carbon_reminder_date
        ? new Date(printer.carbon_reminder_date).setHours(0, 0, 0, 0)
        : null

      if (printer.maintenance_reminder_date) {
        processedReminders.push({
          id: `${printer.id}-maintenance`,
          printerId: printer.id,
          printerTitle: printer.title,
          type: 'maintenance',
          message: `Maintenance due on ${printer.maintenance_reminder_date}`,
          isPastDue: maintenanceDate <= today,
        })
      }

      if (printer.carbon_reminder_date) {
        processedReminders.push({
          id: `${printer.id}-carbon`,
          printerId: printer.id,
          printerTitle: printer.title,
          type: 'carbon',
          message: `Carbon filter change due on ${printer.carbon_reminder_date}`,
          isPastDue: carbonDate <= today,
        })
      }
    })

    reminders.value = processedReminders
  } catch (error) {
    console.error('Failed to fetch reminders:', error)
  }
}

const dismiss = async (printerId, type) => {
  try {
    await APIService.dismissReminder(printerId, type)
    fetchReminders()
  } catch (error) {
    console.error('Failed to dismiss reminder:', error)
  }
}

const navigateToPrinter = (printerId) => {
  isModalVisible.value = false
  router.push({ name: 'printer-detail', params: { id: printerId } })
}

onMounted(() => {
  fetchReminders()
  setInterval(fetchReminders, 300000)
})
</script>

<template>
  <div class="notification-container">
    <button @click="isModalVisible = true" class="bell-button">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" class="bell-svg">
        <path
          d="M224 512c35.32 0 63.97-28.65 63.97-64H160.03c0 35.35 28.65 64 63.97 64zm215.39-149.71c-19.32-20.76-55.47-51.99-55.47-154.29 0-77.7-54.48-139.9-127.94-155.16V32c0-17.67-14.32-32-31.98-32s-31.98 14.33-31.98 32v20.84C118.56 68.1 64.08 130.3 64.08 208c0 102.3-36.15 133.53-55.47 154.29-6 6.45-8.66 14.16-8.61 21.71.11 16.4 12.98 32 32.1 32h383.8c19.12 0 32-15.6 32.1-32 .05-7.55-2.61-15.27-8.61-21.71z"
        />
      </svg>
      <span v-if="reminderCount > 0" class="badge">{{ reminderCount }}</span>
    </button>

    <BaseModal :show="isModalVisible" title="Notifications" @close="isModalVisible = false">
      <ul v-if="reminders.length > 0" class="notification-list">
        <li v-for="reminder in reminders" :key="reminder.id" class="dropdown-item">
          <div @click="navigateToPrinter(reminder.printerId)" class="item-content">
            <strong>{{ reminder.printerTitle }}</strong>
            <p :class="{ 'past-due': reminder.isPastDue }">{{ reminder.message }}</p>
          </div>
          <button @click.stop="dismiss(reminder.printerId, reminder.type)" class="dismiss-button">
            Dismiss
          </button>
        </li>
      </ul>
      <div v-else class="no-reminders">No new notifications.</div>
      <template #footer>
        <button @click="isModalVisible = false" class="action-button save-button">Close</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.notification-container {
  position: relative;
}
.bell-button {
  background: none;
  border: none;
  color: var(--color-text);
  cursor: pointer;
  position: relative;
  padding: 0;
  width: 41px;
  height: 41px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bell-svg {
  width: 24px;
  height: 24px;
  fill: currentColor;
}
.bell-button:hover {
  color: var(--color-heading);
}
.badge {
  position: absolute;
  top: 5px;
  right: 5px;
  background-color: var(--color-red);
  color: white;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  font-size: 0.7rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}
.notification-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.dropdown-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border);
}
.dropdown-item:last-child {
  border-bottom: none;
}
.item-content {
  cursor: pointer;
  flex-grow: 1;
}
.item-content strong {
  color: var(--color-heading);
}
.item-content p {
  margin: 0;
  font-size: 0.9rem;
}
.item-content p.past-due {
  color: var(--color-red);
  font-weight: bold;
}
.dismiss-button {
  background: none;
  border: none;
  color: var(--color-text);
  text-decoration: underline;
  cursor: pointer;
  font-size: 0.9rem;
  padding: 5px;
}
.dismiss-button:hover {
  color: var(--color-heading);
}
.no-reminders {
  padding: 20px;
  text-align: center;
}
.action-button {
  padding: 8px 15px;
  text-decoration: none;
  border-radius: 5px;
  font-weight: bold;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  font-size: 0.9rem;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.save-button {
  background-color: var(--color-blue);
  color: white;
}
</style>
