// Single source of truth for the sidebar's hideable modules.
//
// Dashboard and Settings are intentionally NOT listed here: they are
// structurally always-visible. Settings must always be reachable so a user can
// never lock themselves out of the toggle that re-enables modules; Dashboard is
// the root-URL landing target (`/` redirects to `/dashboard`).
//
// Hiding a module only removes its sidebar link — its routes stay registered so
// in-app deep links (e.g. a Project linking to a Printer) keep working.
//
// NOTE: 'library' is intentionally absent on this branch. The STL/3MF Library
// ships on a separate feature branch; when it merges, add it here AND to
// HIDEABLE_MODULE_KEYS in inventory/models.py so the backend allow-list agrees.
export const MODULES = [
  { key: 'inventory', label: 'Inventory', to: '/inventory' },
  { key: 'filaments', label: 'Filament', to: '/filaments' },
  { key: 'printers', label: 'Printers', to: '/printers' },
  { key: 'projects', label: 'Projects', to: '/projects' },
  { key: 'trackers', label: 'Print Trackers', to: '/trackers' },
]

// Keys that may be hidden — mirror of the backend HIDEABLE_MODULE_KEYS.
export const HIDEABLE_KEYS = MODULES.map((m) => m.key)
