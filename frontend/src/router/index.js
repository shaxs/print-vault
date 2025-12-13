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
import DashboardView from '../views/DashboardView.vue'
import ModCreateView from '../views/ModCreateView.vue'
import ModEditView from '../views/ModEditView.vue'
import ProjectManageFilesView from '../views/ProjectManageFilesView.vue'
import ProjectManageLinksView from '../views/ProjectManageLinksView.vue'
import TrackerListView from '../views/TrackerListView.vue'
import CreateTrackerWizard from '../views/CreateTrackerWizard.vue'
import TrackerDetailView from '../views/TrackerDetailView.vue'
import TrackerEditView from '../views/TrackerEditView.vue'
import TrackerAddFilesView from '../views/TrackerAddFilesView.vue'
import PrintTrackerView from '../views/PrintTrackerView.vue' // TEMP: Original template for comparison

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // Dashboard (Home)
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', name: 'dashboard', component: DashboardView },

    // Inventory Routes
    { path: '/inventory', name: 'home', component: HomeView },
    { path: '/create', name: 'create', component: InventoryCreateView },
    { path: '/item/:id', name: 'item-detail', component: InventoryDetailView },
    { path: '/item/:id/edit', name: 'item-edit', component: InventoryEditView },

    // Printer Routes
    { path: '/printers', name: 'printer-list', component: PrinterListView },
    { path: '/printers/create', name: 'printer-create', component: PrinterCreateView },
    { path: '/printers/:id', name: 'printer-detail', component: PrinterDetailView },
    { path: '/printers/:id/edit', name: 'printer-edit', component: PrinterEditView },
    { path: '/printers/:id/maintenance', name: 'maintenance-edit', component: MaintenanceEditView },
    {
      path: '/printers/:printerId/mods/add',
      name: 'mod-create',
      component: ModCreateView,
      props: true,
    },
    // New route for editing a mod
    {
      path: '/printers/:printerId/mods/:modId/edit',
      name: 'mod-edit',
      component: ModEditView,
      props: true,
    },

    // Project Routes
    { path: '/projects', name: 'project-list', component: ProjectListView },
    { path: '/projects/create', name: 'project-create', component: ProjectCreateView },
    { path: '/projects/:id', name: 'project-detail', component: ProjectDetailView },
    { path: '/projects/:id/edit', name: 'project-edit', component: ProjectEditView },
    {
      path: '/projects/:id/manage-files',
      name: 'project-manage-files',
      component: ProjectManageFilesView,
    },
    {
      path: '/projects/:id/manage-links', // Added this route
      name: 'project-manage-links',
      component: ProjectManageLinksView,
      props: true,
    },

    // Print Tracker Routes
    { path: '/trackers', name: 'tracker-list', component: TrackerListView },
    { path: '/trackers/create', name: 'tracker-create', component: CreateTrackerWizard },
    { path: '/trackers/:id', name: 'tracker-detail', component: TrackerDetailView },
    { path: '/trackers/:id/edit', name: 'tracker-edit', component: TrackerEditView },
    { path: '/trackers/:id/files/add', name: 'tracker-add-files', component: TrackerAddFilesView },

    // TEMP: Route to view original template for comparison
    { path: '/trackers/:id/template', name: 'tracker-template', component: PrintTrackerView }, // Legacy route - redirect to new route
    {
      path: '/print-tracker',
      redirect: '/trackers',
    },
    {
      path: '/create-tracker',
      redirect: '/trackers/create',
    },

    // Filament Management Routes
    {
      path: '/filaments',
      name: 'filament-management',
      component: () => import('../views/FilamentManagementView.vue'),
    },
    {
      path: '/filaments/cards',
      name: 'filament-cards',
      component: () => import('../views/FilamentCardsView.vue'),
    },
    {
      path: '/filaments/materials',
      name: 'material-library',
      component: () => import('../views/MaterialLibraryView.vue'),
    },
    {
      path: '/filaments/materials/create',
      name: 'material-create',
      component: () => import('../views/MaterialCreateView.vue'),
    },
    {
      path: '/filaments/materials/:id',
      name: 'material-detail',
      component: () => import('../views/MaterialDetailView.vue'),
    },
    {
      path: '/filaments/materials/:id/edit',
      name: 'material-edit',
      component: () => import('../views/MaterialEditView.vue'),
    },
    {
      path: '/filaments/create',
      name: 'filament-spool-create',
      component: () => import('../views/FilamentSpoolCreateView.vue'),
    },
    {
      path: '/filaments/:id',
      name: 'filament-spool-detail',
      component: () => import('../views/FilamentSpoolDetailView.vue'),
    },
    {
      path: '/filaments/:id/edit',
      name: 'filament-spool-edit',
      component: () => import('../views/FilamentSpoolEditView.vue'),
    },

    // Settings Route
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})

export default router
