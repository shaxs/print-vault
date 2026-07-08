import { ref } from 'vue'
import APIService from '@/services/APIService.js'

// Module-scoped singleton state (this project has no Pinia/Vuex). The same
// reactive `hiddenModules` is shared by the sidebar (App.vue), the
// Settings > Modules tab, and the Dashboard notice, so a change in one place is
// reflected everywhere without a page reload.
const hiddenModules = ref([])
const loaded = ref(false)
let inflight = null

async function load(force = false) {
  if (loaded.value && !force) return
  if (inflight) return inflight
  inflight = APIService.getAppConfig()
    .then(({ data }) => {
      hiddenModules.value = Array.isArray(data.hidden_modules) ? data.hidden_modules : []
      loaded.value = true
    })
    .catch((error) => {
      // Fail open: on any error default to all-visible so a backend hiccup can
      // never hide the whole app. Leave loaded=false so a later call retries.
      console.error('Failed to load app configuration:', error)
      hiddenModules.value = []
    })
    .finally(() => {
      inflight = null
    })
  return inflight
}

function isHidden(key) {
  return hiddenModules.value.includes(key)
}

// Toggle one module's visibility and persist it. Optimistically returns the
// server's saved state (the backend validates + de-dupes the list).
async function setHidden(key, hidden) {
  const next = hidden
    ? [...new Set([...hiddenModules.value, key])]
    : hiddenModules.value.filter((k) => k !== key)
  const { data } = await APIService.updateAppConfig({ hidden_modules: next })
  hiddenModules.value = Array.isArray(data.hidden_modules) ? data.hidden_modules : []
  return hiddenModules.value
}

export function useAppConfig() {
  return { hiddenModules, loaded, load, isHidden, setHidden }
}
