# Printers Guide

**Print Vault** — User Documentation
**Feature**: Printers / Fleet Management
**Last Updated**: 2026-07-11

---

## What Is the Printer System?

Printers is where you track every 3D printer you own: its specs, purchase info, status, maintenance schedule, mods, and which filament materials it's currently loaded with.

Core capabilities:

- **Printer records** — title, Manufacturer, Serial Number, purchase price/date, build volume, and a photo
- **Status lifecycle** — Active, Under Repair, Sold, Archived, or Planned, which feeds into low-level alerts and a project's "Blocked" health when a printer it depends on goes unavailable
- **Maintenance tracking** — last-serviced dates and reminder dates for general maintenance and carbon filter replacement, edited separately from the printer's main details
- **Mods** — a running list of upgrades/modifications per printer, each with a status, an optional link, and attached files you can download individually or all at once
- **Materials** — Primary/Accent/additional filament assignments, either a free-text custom description or a live link to a Material Blueprint from your Filament library
- **Assigned Spools** — any Filament spool currently assigned to this printer shows up automatically on its detail page

---

## Getting Started

Open **Printers** from the sidebar (route `/printers`). The header toolbar has **Filter**, **Columns**, a live **Search** box, and a blue **Add** button (there's no CSV import for printers).

> 📷 **Screenshot needed** — the Printers list page

Table columns (toggle visibility from **Columns**): Title, Photo, Manufacturer, Status, Serial Number, Purchase Date. Title, Manufacturer, and Status are visible by default. Your column choices and filters are remembered across visits.

---

## Creating a Printer

Click **Add** to open the printer form:

- **Title** (required)
- **Manufacturer (Brand)** — type-ahead, taggable; shares the same Brand list used by Inventory
- **Serial Number**
- **Purchase Price** and **Purchase Date**
- **Status** — Active / Under Repair / Sold / Archived / Planned (defaults to Active)
- **Build Volume** — X, Y, Z in mm
- **Photo**
- **Primary Color/Material** and **Accent Color/Material** — each toggles between **Custom Entry** (free text, e.g. "Red PLA") and **Select from Library** (a live link to one of your Material Blueprints, shown with its color swatch)
- **Additional Materials** — click **+ Add Another Material** to attach any number of extra material slots, each with its own free-text Type label (e.g. "Canopy", "X-Mount") and the same Custom/Library choice
- **Notes**

> 📷 **Screenshot needed** — the Add Printer form, including the Materials section

Click **Save Printer Details** to save and go to the printer's detail page. (There is no "Save + Add Another" here — that shortcut only exists on the Inventory form.)

> **Note**: Maintenance dates aren't on this form at all — they're set separately after the printer exists. See [Maintenance](#maintenance).

---

## The Printer Detail View

The header shows the printer's photo (click to enlarge), title, manufacturer, and serial number, with **← Back to Printers**, **Edit**, and **Delete** buttons (deleting asks for confirmation and cannot be undone).

### Printer Details Card

Shows a colored **Status** badge, Build Volume, Purchase Date, Purchase Price, and Notes. If Primary/Accent/Additional materials are set, a **Materials** section lists each one — a Library-linked material shows a clickable color swatch (opens a lightbox with the hex value) plus a link straight to that Material Blueprint's detail page in the Filament section.

If any Filament spool is currently assigned to this printer, an **Assigned Spools** list appears underneath, each with a color swatch, a link to the spool, and its status badge (New, Opened, In Use, Low, Empty, Archived).

> 📷 **Screenshot needed** — the Printer Details card showing Materials and Assigned Spools

### Maintenance

A separate card shows **Last Maintained**, **Maintenance Reminder**, **Last Carbon Filter Replacement**, **Carbon Filter Reminder**, and **Maintenance Notes**, each with its own **Edit** link — see [Maintenance](#maintenance) below.

### Mods

Lists every mod on this printer with its name (linked out if a URL was provided), a status badge, and any attached files. See [Mods](#mods) below.

---

## Editing a Printer

Click **Edit** from the detail page (or the **Edit** button on the Printer Details card) to reopen the same form pre-filled, including the Materials section. Saving returns you to the detail page.

---

## Maintenance

Maintenance dates live on their own small form, reached via the **Edit** link on the Maintenance card (not the main printer Edit button):

- **Date of Last Maintenance**
- **Maintenance Reminder** — the date you want to be reminded to service the printer again
- **Date of Last Carbon Filter Replacement**
- **Carbon Filter Reminder**
- **Maintenance Notes**

> 📷 **Screenshot needed** — the Maintenance edit form

### How reminders surface

- **Notification bell** (top of every page): once a Maintenance Reminder or Carbon Filter Reminder date is today or in the past, it appears here as "Maintenance due on <date>" or "Carbon filter due on <date>", alongside Inventory's low-stock alerts. Clicking it takes you to the printer.
- **Dashboard notifications**: once a reminder date has actually passed (not just reached), it also raises a dismissible critical alert — "Maintenance Overdue" or "Carbon Filter Overdue" — on the Dashboard. A separate warning-level "Carbon Filter Due Soon" alert appears in the 7 days leading up to the carbon reminder date. Dismissing one of these clears it until something about that printer's dates or status changes again.

---

## Mods

Click **Add Mod** on the printer's detail page to log an upgrade or modification:

- **Mod Name** (required)
- **Link** — optional URL (to a build guide, a listing, etc.)
- **Status** — Planned / In Progress / Completed
- **Files** — drag-and-drop or click to attach any number of files (STLs, configs, instructions, etc.)

> 📷 **Screenshot needed** — the Add/Edit Mod form with the file drop zone

Back on the printer detail page, each mod shows its status badge and attached files. Use **Edit** to change its details, add more files, or remove existing ones (marked files are only actually deleted once you save); **Download All** zips up every file on that mod for one-click download; **Delete** removes the mod and all of its files permanently (asks for confirmation).

---

## Printer Status Reference

| Status | Meaning |
|---|---|
| **Active** | In service and available for builds |
| **Planned** | Not yet owned/built — a placeholder for a printer you're planning to acquire |
| **Under Repair** | Temporarily unavailable — triggers a "Printer Under Repair" Dashboard alert and can mark dependent projects as Blocked/Partially Blocked |
| **Sold** | No longer in your possession |
| **Archived** | Retired from active use, kept for historical record |

**Under Repair**, **Sold**, and **Archived** are all treated as "unavailable" for the purposes of project health: if a project in **In Progress** status has one or more Associated Printers and any of them are unavailable, the project's health shows as **Blocked** (if every associated printer is unavailable) or **Partially Blocked** (if only some are) on the Dashboard, and a dismissible "Project Blocked" alert is raised. See `docs/PROJECTS_USER_GUIDE.md` for the full project-health picture.

---

## Filtering, Searching, and Columns

Click **Filter** to narrow the list by **Manufacturer** or **Status** (both default to "All"). The **Search** box does a live text search. **Columns** lets you choose which table columns are visible; your choices and filters persist across visits.

---

## Common Use Cases

### Setting Up a New Printer

1. Click **Add**, fill in Title, Manufacturer, and Build Volume.
2. Set Status to **Active** (or **Planned** if you don't have it in hand yet).
3. If it has a go-to filament setup, fill in Primary/Accent Materials — pick **Select from Library** if you've already got the Material Blueprint on file, or **Custom Entry** for a quick free-text note.
4. Save, then use **Add Mod** on the detail page to log any upgrades it already has installed.

### Logging Maintenance After a Service

1. Open the printer, and click **Edit** on the Maintenance card.
2. Set **Date of Last Maintenance** to today, and pick a **Maintenance Reminder** date for the next service.
3. Save — this clears any existing overdue-maintenance alert for this printer and won't raise a new one until the new reminder date arrives.

### A Printer Breaks Mid-Build

1. Edit the printer and set **Status** to **Under Repair**.
2. A "Printer Under Repair" alert appears on the Dashboard, and any **In Progress** project that has this printer as an Associated Printer shows a Blocked or Partially Blocked health status.
3. Once it's fixed, set Status back to **Active** — the alert and the project health status clear automatically.

---

## Tips

- Materials assigned here are just informational — they don't reserve filament stock the way a Bill of Materials does. Use them to remember "this printer is currently loaded with X" at a glance.
- Use **Select from Library** for materials whenever you've already got the Material Blueprint on file — it gives you a clickable color swatch and a live link, not just text.
- Maintenance and Mods each live behind their own **Edit** link on the detail page — don't look for maintenance fields on the main printer Edit form, they aren't there.
- Set a printer's Status to **Under Repair** as soon as it goes down; that's what drives the Dashboard alert and the Blocked/Partially Blocked signal on any project depending on it.

---

## Related Sections

- **Filament** — Material Blueprints referenced by a printer's Primary/Accent/Additional materials, and spool-to-printer assignment: `docs/FILAMENT_USER_GUIDE.md`
- **Projects** — Associated Printers, and how printer status drives a project's Blocked/Partially Blocked health: `docs/PROJECTS_USER_GUIDE.md`
- **Inventory** — the shared Brand lookup list used by both Printers and Inventory: `docs/INVENTORY_USER_GUIDE.md`
