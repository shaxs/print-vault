// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import InventoryCreateView from '../views/InventoryCreateView.vue'
import InventoryDetailView from '../views/InventoryDetailView.vue'
import InventoryEditView from '../views/InventoryEditView.vue'
import PrinterListView from '../views/PrinterListView.vue'
import PrinterCreateView from '../views/PrinterCreateView.vue'
import PrinterDetailView from '../views/PrinterDetailView.vue'
import PrinterEditView from '../views/PrinterEditView.vue'
import MaintenanceEditView from '../views/MaintenanceEditView.vue'
import ProjectListView from '../views/ProjectListView.vue'
import ProjectCreateView from '../views/ProjectCreateView.vue'
import ProjectDetailView from '../views/ProjectDetailView.vue'
import ProjectEditView from '../views/ProjectEditView.vue'
import SettingsView from '../views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // Inventory Routes
    { path: '/', name: 'home', component: HomeView },
    { path: '/create', name: 'create', component: InventoryCreateView },
    { path: '/item/:id', name: 'item-detail', component: InventoryDetailView },
    { path: '/item/:id/edit', name: 'item-edit', component: InventoryEditView },

    // Printer Routes
    { path: '/printers', name: 'printer-list', component: PrinterListView },
    { path: '/printers/create', name: 'printer-create', component: PrinterCreateView },
    { path: '/printers/:id', name: 'printer-detail', component: PrinterDetailView },
    { path: '/printers/:id/edit', name: 'printer-edit', component: PrinterEditView },
    { path: '/printers/:id/maintenance', name: 'maintenance-edit', component: MaintenanceEditView },

    // Project Routes
    { path: '/projects', name: 'project-list', component: ProjectListView },
    { path: '/projects/create', name: 'project-create', component: ProjectCreateView },
    { path: '/projects/:id', name: 'project-detail', component: ProjectDetailView },
    { path: '/projects/:id/edit', name: 'project-edit', component: ProjectEditView },

    // Settings Route
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})

export default router
