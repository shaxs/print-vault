<script setup>
import { ref, computed } from 'vue'

// --- Mock Data ---
const trackerData = ref({
  name: 'Voron V0.2',
  associatedProject: 'My Voron Build',
  progress: 45,
  stats: {
    total: 10,
    printed: 4,
    pending: 6,
  },
  categories: [
    {
      name: 'Skirts',
      isOpen: true,
      files: [
        {
          name: '[a]_front_skirt_v0.2_x2.stl',
          color: 'Primary',
          printed: 1,
          required: 2,
          completed: false,
        },
        {
          name: '[a]_rear_skirt_v0.2_x2.stl',
          color: 'Accent',
          printed: 0,
          required: 2,
          completed: false,
        },
      ],
    },
    {
      name: 'Frame',
      isOpen: true,
      files: [
        {
          name: 'corner_post_x4.stl',
          color: 'Multicolor',
          printed: 4,
          required: 4,
          completed: true,
        },
      ],
    },
    {
      name: 'Gantry',
      isOpen: true,
      files: [
        {
          name: 'x_carriage_frame_left.stl',
          color: 'Clear',
          printed: 0,
          required: 1,
          completed: false,
        },
        {
          name: 'x_carriage_frame_right.stl',
          color: 'Other',
          printed: 0,
          required: 1,
          completed: false,
        },
      ],
    },
    {
      name: 'Panels',
      isOpen: true,
      files: [
        { name: 'bottom_panel.stl', color: 'Primary', printed: 1, required: 1, completed: true },
        { name: 'rear_panel.stl', color: 'Primary', printed: 1, required: 1, completed: true },
        { name: 'side_panel_a.stl', color: 'Clear', printed: 0, required: 1, completed: false },
        { name: 'side_panel_b.stl', color: 'Clear', printed: 0, required: 1, completed: false },
      ],
    },
  ],
})

const searchQuery = ref('')

function toggleCategory(category) {
  category.isOpen = !category.isOpen
}

const filteredCategories = computed(() => {
  // This will be expanded later to include search and advanced filters
  let categories = trackerData.value.categories

  return categories
})
</script>

<template>
  <div class="page-container">
    <div class="content-container">
      <div class="list-header">
        <h1 class="page-title">Print Tracker</h1>
        <button class="btn btn-primary">Add Tracker</button>
      </div>
      <div class="list-controls">
        <input
          type="text"
          v-model="searchQuery"
          class="form-control"
          placeholder="Search files..."
        />
        <button class="btn btn-secondary">Filter</button>
      </div>

      <div class="card mb-6">
        <div class="card-body">
          <h2 class="font-bold text-xl mb-2">{{ trackerData.name }}</h2>
          <p class="subtitle">
            Associated Project: <a href="#">{{ trackerData.associatedProject }}</a>
          </p>
          <div class="mt-4">
            <div class="flex justify-between mb-1">
              <span class="progress-label">Overall Progress</span>
              <span class="progress-percentage">{{ trackerData.progress }}%</span>
            </div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fg" :style="{ width: trackerData.progress + '%' }"></div>
            </div>
            <div class="stats-container">
              <div>
                <p class="stat-number">{{ trackerData.stats.total }}</p>
                <p class="stat-label">Total STLs</p>
              </div>
              <div>
                <p class="stat-number stat-printed">{{ trackerData.stats.printed }}</p>
                <p class="stat-label">Printed</p>
              </div>
              <div>
                <p class="stat-number stat-pending">{{ trackerData.stats.pending }}</p>
                <p class="stat-label">Pending</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-body">
          <div class="space-y-2">
            <div v-for="category in filteredCategories" :key="category.name" class="category-group">
              <div
                class="category-header"
                @click="toggleCategory(category)"
                :class="{ 'is-collapsed': !category.isOpen }"
              >
                <h2 class="category-title">{{ category.name }}</h2>
                <span class="arrow">&#9660;</span>
              </div>
              <div v-if="category.isOpen" class="category-content">
                <div
                  v-for="file in category.files"
                  :key="file.name"
                  class="file-row"
                  :class="{ 'completed-row': file.completed }"
                >
                  <div class="file-name">
                    <span :class="{ 'line-through': file.completed }">{{ file.name }}</span>
                    <span class="color-tag" :class="`bg-${file.color.toLowerCase()}`">{{
                      file.color
                    }}</span>
                  </div>
                  <div class="file-actions">
                    <label class="printed-label">Printed:</label>
                    <input
                      type="number"
                      :value="file.printed"
                      class="form-control printed-input"
                      :disabled="file.completed"
                    />
                    <span class="required-amount">/ {{ file.required }}</span>
                    <div class="progress-bar-bg small">
                      <div
                        class="progress-bar-fg"
                        :class="file.completed ? 'bg-green' : 'bg-blue'"
                        :style="{ width: (file.printed / file.required) * 100 + '%' }"
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Scoped styles from other list views for consistency */
.page-container {
  padding: 2rem;
}
.content-container {
  max-width: 1200px;
  margin: 0 auto;
}
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.page-title {
  font-size: 2rem;
  font-weight: bold;
  color: var(--color-heading);
}
.list-controls {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.form-control {
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background-color: var(--color-background);
  color: var(--color-text);
  flex-grow: 1; /* Make search bar take available space */
}

/* Card Styles */
.card {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  margin-bottom: 1.5rem;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
}
.card-header h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-heading);
}
.card-body {
  padding: 1rem 1.5rem;
}

/* Tracker Specific Styles */
.subtitle {
  color: var(--color-text-soft);
  font-size: 0.9rem;
}
.subtitle a {
  color: var(--color-blue);
  text-decoration: none;
}
.subtitle a:hover {
  text-decoration: underline;
}
.progress-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-heading);
}
.progress-percentage {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-blue);
}
.progress-bar-bg {
  width: 100%;
  background-color: var(--color-background);
  border-radius: 9999px;
  height: 0.75rem;
}
.progress-bar-fg {
  background-color: var(--color-blue);
  height: 0.75rem;
  border-radius: 9999px;
}
.stats-container {
  display: flex;
  justify-content: space-between;
  text-align: center;
  margin-top: 1rem;
  border-top: 1px solid var(--color-border);
  padding-top: 0.75rem;
}
.stat-number {
  font-size: 1.1rem;
  font-weight: bold;
  color: var(--color-heading);
}
.stat-label {
  font-size: 0.75rem;
  color: var(--color-text-soft);
}
.stat-printed {
  color: var(--color-green);
}
.stat-pending {
  color: #f5a623;
}

.category-group {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.75rem;
  margin-bottom: 0.75rem;
}
.category-group:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.category-header {
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
}
.category-header:hover {
  background-color: var(--color-background-mute);
}
.category-title {
  font-size: 1.1rem;
  font-weight: 600;
}
.arrow {
  transition: transform 0.2s ease-in-out;
}
.category-header.is-collapsed .arrow {
  transform: rotate(-90deg);
}
.category-content {
  padding-top: 0.5rem;
}
.file-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.9rem;
}
.completed-row {
  background-color: rgba(40, 167, 69, 0.1);
}
.completed-row .line-through {
  text-decoration: line-through;
  opacity: 0.6;
}
.file-name {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.file-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.printed-label {
  font-size: 0.8rem;
  color: var(--color-text-soft);
}
.printed-input {
  width: 3.5rem;
  text-align: center;
  padding: 0.2rem;
}
.required-amount {
  font-size: 0.9rem;
  color: var(--color-text-soft);
}
.progress-bar-bg.small {
  width: 6rem;
  height: 0.5rem;
}
.progress-bar-fg.bg-blue {
  background-color: var(--color-blue);
}
.progress-bar-fg.bg-green {
  background-color: var(--color-green);
}
.progress-bar-fg {
  height: 0.5rem;
}

.color-tag {
  padding: 1px 7px;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 500;
  color: white;
}
.bg-primary {
  background-color: #4a90e2;
}
.bg-accent {
  background-color: #f5a623;
}
.bg-multicolor {
  background-image: linear-gradient(to right, #f5a623, #4a90e2, #50e3c2);
}
.bg-clear {
  background-color: #e2e8f0;
  color: #4a5568;
  border: 1px solid #cbd5e0;
}
.bg-other {
  background-color: #78716c;
}

/* Utility classes from Tailwind used in mockup - for spacing */
.mb-6 {
  margin-bottom: 1.5rem;
}
.mt-4 {
  margin-top: 1rem;
}
.mb-1 {
  margin-bottom: 0.25rem;
}
.space-y-2 > :not([hidden]) ~ :not([hidden]) {
  margin-top: 0.5rem;
}
.space-y-4 > :not([hidden]) ~ :not([hidden]) {
  margin-top: 1rem;
}
.flex {
  display: flex;
}
.justify-between {
  justify-content: space-between;
}
.items-center {
  align-items: center;
}
.font-bold {
  font-weight: 700;
}
.text-xl {
  font-size: 1.25rem;
}
.text-lg {
  font-size: 1.125rem;
}
.text-sm {
  font-size: 0.875rem;
}
.text-center {
  text-align: center;
}
.pt-2 {
  padding-top: 0.5rem;
}
.w-full {
  width: 100%;
}
.h-4 {
  height: 1rem;
}
.rounded-full {
  border-radius: 9999px;
}
.text-blue-500 {
  color: #3b82f6;
}
.text-blue-700 {
  color: #1d4ed8;
}
.bg-blue-600 {
  background-color: #2563eb;
}
.text-gray-600 {
  color: #4b5563;
}
.bg-gray-200 {
  background-color: #e5e7eb;
}
.dark .dark\:bg-gray-700 {
  background-color: #374151;
}
.text-green-500 {
  color: #22c55e;
}
.text-yellow-500 {
  color: #eab308;
}
</style>
