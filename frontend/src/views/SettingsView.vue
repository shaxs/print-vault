<script setup>
import { ref } from 'vue'
import MainHeader from '@/components/MainHeader.vue'
import BrandsTab from '@/components/BrandsTab.vue'
import PartTypesTab from '@/components/PartTypesTab.vue'
import LocationsTab from '@/components/LocationsTab.vue'
import MaterialsTab from '@/components/MaterialsTab.vue'
import VendorsTab from '@/components/VendorsTab.vue'
import PreferencesTab from '@/components/PreferencesTab.vue'
import DataManagementTab from '@/components/DataManagementTab.vue'

const activeTab = ref('brands')
</script>

<template>
  <div>
    <MainHeader title="Settings" :showSearch="false" :showAddButton="false" />
    <div class="settings-container">
      <div class="tabs">
        <button @click="activeTab = 'brands'" :class="{ active: activeTab === 'brands' }">
          Brands
        </button>
        <button @click="activeTab = 'part-types'" :class="{ active: activeTab === 'part-types' }">
          Part Types
        </button>
        <button @click="activeTab = 'locations'" :class="{ active: activeTab === 'locations' }">
          Locations
        </button>
        <button @click="activeTab = 'materials'" :class="{ active: activeTab === 'materials' }">
          Materials
        </button>
        <button @click="activeTab = 'vendors'" :class="{ active: activeTab === 'vendors' }">
          Vendors
        </button>
        <button @click="activeTab = 'preferences'" :class="{ active: activeTab === 'preferences' }">
          Preferences
        </button>
        <button @click="activeTab = 'data'" :class="{ active: activeTab === 'data' }">
          Data Management
        </button>
      </div>
      <div class="tab-content">
        <BrandsTab v-if="activeTab === 'brands'" />
        <PartTypesTab v-if="activeTab === 'part-types'" />
        <LocationsTab v-if="activeTab === 'locations'" />
        <MaterialsTab v-if="activeTab === 'materials'" />
        <VendorsTab v-if="activeTab === 'vendors'" />
        <PreferencesTab v-if="activeTab === 'preferences'" />
        <DataManagementTab v-if="activeTab === 'data'" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-container {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  margin: 0 20px 20px 20px;
}
.tabs {
  display: flex;
  background-color: var(--color-background-mute);
  flex-wrap: wrap;
}
.tabs button {
  padding: 15px 20px;
  cursor: pointer;
  background-color: transparent;
  border: none;
  color: var(--color-text);
  font-size: 1rem;
  border-bottom: 3px solid transparent;
}
.tabs button.active {
  color: var(--color-heading);
  border-bottom-color: var(--color-blue);
}
.tab-content {
  padding: 20px;
}
</style>
