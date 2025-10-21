<script setup>
import { useRouter } from 'vue-router'
import DataTable from './DataTable.vue'

defineProps({
  items: { type: Array, required: true },
  visibleColumns: { type: Array, required: true },
})

const router = useRouter()
const headers = [
  { text: 'Tracker Name', value: 'trackerName' },
  { text: 'Project', value: 'projectName' },
  { text: 'Files', value: 'fileCount' },
  { text: 'Progress', value: 'progress' },
  { text: 'GitHub URL', value: 'githubUrl' },
  { text: 'Storage Type', value: 'storageType' },
  { text: 'Created Date', value: 'createdDate' },
]

const viewTracker = (tracker) => {
  router.push({ name: 'tracker-detail', params: { id: tracker.id } })
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

const getProgressColor = (percentage) => {
  if (percentage === 0) return '#64748b' // gray
  if (percentage < 50) return '#ef4444' // red
  if (percentage < 100) return '#f59e0b' // orange
  return '#10b981' // green
}

// Get tracker progress style for consistency with detail views
const getTrackerProgressStyle = (item) => {
  const percentage = item?.progress_percentage || 0
  return {
    width: `${percentage}%`,
    height: '100%',
    backgroundColor: getProgressColor(percentage),
    transition: 'width 0.3s ease',
  }
}
</script>

<template>
  <DataTable
    :headers="headers"
    :items="items"
    :visible-columns="visibleColumns"
    @row-click="viewTracker"
  >
    <template #cell-trackerName="{ item }">
      {{ item.name }}
    </template>
    <template #cell-projectName="{ item }">
      <span v-if="item.project_name">{{ item.project_name }}</span>
      <span v-else style="color: var(--color-text-muted)">No Project</span>
    </template>
    <template #cell-fileCount="{ item }">
      {{ item.total_count }}
    </template>
    <template #cell-progress="{ item }">
      <div style="display: flex; align-items: center; gap: 10px">
        <div
          style="
            flex: 1;
            background: rgba(156, 163, 175, 0.3);
            border-radius: 10px;
            height: 20px;
            overflow: hidden;
          "
        >
          <div :style="getTrackerProgressStyle(item)"></div>
        </div>
        <span style="min-width: 45px; text-align: right; font-weight: 500"
          >{{ item.progress_percentage }}%</span
        >
      </div>
    </template>
    <template #cell-githubUrl="{ item }">
      <a
        v-if="item.github_url"
        :href="item.github_url"
        target="_blank"
        rel="noopener noreferrer"
        @click.stop
        style="color: var(--color-link); text-decoration: none"
      >
        {{ item.github_url.replace('https://github.com/', '') }}
      </a>
      <span v-else style="color: var(--color-text-muted)">—</span>
    </template>
    <template #cell-storageType="{ item }">
      <span
        :style="{
          display: 'inline-block',
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '0.85rem',
          fontWeight: '500',
          backgroundColor: item.storage_type === 'local' ? '#22c55e20' : '#3b82f620',
          color: item.storage_type === 'local' ? '#22c55e' : '#3b82f6',
        }"
      >
        {{ item.storage_type === 'local' ? '💾 Local' : '🔗 Links' }}
      </span>
    </template>
    <template #cell-createdDate="{ item }">
      {{ formatDate(item.created_date) }}
    </template>
  </DataTable>
</template>
