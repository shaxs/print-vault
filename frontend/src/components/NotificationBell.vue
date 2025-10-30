<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import APIService from '@/services/APIService.js'
import BaseModal from '@/components/BaseModal.vue'

const props = defineProps({
  reminders: {
    type: Array,
    required: true,
  },
  lowStockItems: {
    type: Array,
    required: true,
  },
})

const router = useRouter()
const isModalVisible = ref(false)

const allReminders = computed(() => {
  const processed = []
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  props.reminders.forEach((printer) => {
    // Check maintenance reminder
    if (printer.maintenance_reminder_date) {
      // Parse date as local time by adding 'T00:00:00' to force local timezone
      const maintenanceDate = new Date(printer.maintenance_reminder_date + 'T00:00:00')
      const maintenanceDateOnly = new Date(maintenanceDate)
      maintenanceDateOnly.setHours(0, 0, 0, 0)

      // Only add the reminder if the date is today or in the past
      if (maintenanceDateOnly <= today) {
        processed.push({
          id: `${printer.id}-maintenance`,
          printerId: printer.id,
          printerTitle: printer.title,
          type: 'maintenance',
          message: `Maintenance due on ${maintenanceDate.toLocaleDateString()}`,
          date: maintenanceDate,
          isPastDue: maintenanceDateOnly < today,
        })
      }
    }
    // Check carbon filter reminder
    if (printer.carbon_reminder_date) {
      // Parse date as local time by adding 'T00:00:00' to force local timezone
      const carbonDate = new Date(printer.carbon_reminder_date + 'T00:00:00')
      const carbonDateOnly = new Date(carbonDate)
      carbonDateOnly.setHours(0, 0, 0, 0)

      // Only add the reminder if the date is today or in the past
      if (carbonDateOnly <= today) {
        processed.push({
          id: `${printer.id}-carbon`,
          printerId: printer.id,
          printerTitle: printer.title,
          type: 'carbon',
          message: `Carbon filter due on ${carbonDate.toLocaleDateString()}`,
          date: carbonDate,
          isPastDue: carbonDateOnly < today,
        })
      }
    }
  })
  return processed.sort((a, b) => a.date - b.date)
})

const notificationCount = computed(() => {
  return allReminders.value.length + props.lowStockItems.length
})

const navigateToPrinter = (id) => {
  isModalVisible.value = false
  router.push(`/printers/${id}`)
}

const navigateToItem = (id) => {
  isModalVisible.value = false
  router.push(`/item/${id}`)
}

const dismissReminder = async (id, type) => {
  const printerId = id.split('-')[0]
  const updateData = {}

  if (type === 'maintenance') {
    updateData.last_maintained_date = new Date().toISOString().split('T')[0]
    updateData.maintenance_reminder_date = null
  } else if (type === 'carbon') {
    updateData.last_carbon_replacement_date = new Date().toISOString().split('T')[0]
    updateData.carbon_reminder_date = null
  }

  try {
    await APIService.updatePrinter(printerId, updateData)
    isModalVisible.value = false
    window.location.reload()
  } catch (error) {
    console.error('Failed to dismiss reminder:', error)
  }
}
</script>

<template>
  <div class="notification-container">
    <button @click="isModalVisible = true" class="notification-button">
      <svg class="bell-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
        <path
          d="M10 21h4c0 1.1-.9 2-2 2s-2-.9-2-2zm11-2v1H3v-1l2-2v-6c0-3.1 2.03-5.83 5-6.71V4c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5v.29c2.97.88 5 3.61 5 6.71v6l2 2zM12 2c-4.42 0-8 3.58-8 8v6l-2 2v1h20v-1l-2-2v-6c0-4.42-3.58-8-8-8zm-2 11c0 .55.45 1 1 1s1-.45 1-1-.45-1-1-1-1 .45-1 1zm4 0c0 .55.45 1 1 1s1-.45 1-1-.45-1-1-1-1 .45-1 1z"
          fill="currentColor"
        />
      </svg>
      <span v-if="notificationCount > 0" class="notification-badge">{{ notificationCount }}</span>
    </button>
    <BaseModal :show="isModalVisible" title="Notifications" @close="isModalVisible = false">
      <div v-if="notificationCount > 0">
        <div v-if="lowStockItems.length > 0">
          <h4>Low Stock</h4>
          <ul class="notification-list">
            <li v-for="item in lowStockItems" :key="item.id" class="dropdown-item">
              <div @click="navigateToItem(item.id)" class="item-content">
                <strong>{{ item.title }}</strong>
                <p>
                  Quantity is at {{ item.quantity }} (Threshold: {{ item.low_stock_threshold }})
                </p>
              </div>
            </li>
          </ul>
        </div>

        <div v-if="allReminders.length > 0">
          <h4>Maintenance</h4>
          <ul class="notification-list">
            <li v-for="reminder in allReminders" :key="reminder.id" class="dropdown-item">
              <div @click="navigateToPrinter(reminder.printerId)" class="item-content">
                <strong>{{ reminder.printerTitle }}</strong>
                <p :class="{ 'past-due': reminder.isPastDue }">{{ reminder.message }}</p>
              </div>
              <button
                @click="dismissReminder(reminder.id, reminder.type)"
                class="dismiss-button"
                title="Dismiss reminder"
              >
                ✕
              </button>
            </li>
          </ul>
        </div>
      </div>
      <p v-else>You're all caught up!</p>
      <template #footer>
        <button @click="isModalVisible = false" type="button" class="action-button cancel-button">
          Close
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.notification-container {
  position: relative;
}
.notification-button {
  background: none;
  border: none;
  cursor: pointer;
  position: relative;
  color: var(--color-text);
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bell-icon {
  width: 24px;
  height: 24px;
  fill: currentColor;
}
.notification-badge {
  position: absolute;
  top: -4px;
  right: -8px;
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
h4 {
  margin-top: 10px;
  margin-bottom: 5px;
  color: var(--color-heading);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 5px;
}
h4:first-of-type {
  margin-top: 0;
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
  background: transparent;
  border: none;
  color: var(--color-text-soft);
  font-size: 0.9rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s;
  line-height: 1;
  flex-shrink: 0;
}
.dismiss-button:hover {
  background: rgba(0, 0, 0, 0.1);
  color: var(--color-text);
}
.action-button {
  padding: 8px 15px;
  text-decoration: none;
  border-radius: 5px;
  font-weight: bold;
  border: none;
  cursor: pointer;
}
.cancel-button {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
  border: 1px solid var(--color-border);
}
</style>
