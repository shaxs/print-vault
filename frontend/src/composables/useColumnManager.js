// src/composables/useColumnManager.js
import { ref } from 'vue'

export function useColumnManager(storageKey, allColumns) {
  const getDefaultVisible = () => {
    return allColumns.filter((c) => c.defaultVisible).map((c) => c.value)
  }

  const loadInitialColumns = () => {
    const saved = localStorage.getItem(storageKey)
    if (saved) {
      try {
        const savedValues = JSON.parse(saved)
        const allValues = allColumns.map((c) => c.value)
        return savedValues.filter((v) => allValues.includes(v))
      } catch (error) {
        console.error('Error parsing saved columns:', error)
        return getDefaultVisible()
      }
    }
    return getDefaultVisible()
  }

  const visibleColumns = ref(loadInitialColumns())

  const saveColumns = (newColumns) => {
    visibleColumns.value = newColumns
    localStorage.setItem(storageKey, JSON.stringify(newColumns))
  }

  return {
    visibleColumns,
    saveColumns,
  }
}
