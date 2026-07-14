# Settings Guide

**Print Vault** — User Documentation
**Feature**: Settings / Configuration
**Last Updated**: 2026-07-11

---

## What Is the Settings Section?

Settings is where you manage the shared lookup lists that power the dropdowns and type-ahead fields across Inventory, Printers, and Filament, plus app-wide preferences, backup/restore, and version info.

Open **Settings** from the sidebar (route `/settings`). It's a single page with nine tabs:

- **Brands**, **Part Types**, **Locations**, **Vendors** — simple name lists used by Inventory and Printers
- **Materials** — the generic base material types (PLA, PETG, ABS, etc.) used by Filament
- **Features** — reusable tags for Filament Material Blueprints (Matte, Glitter, High Speed, etc.)
- **Preferences** — light/dark theme
- **Data Management** — export, restore, and permanently delete all data
- **About** — version info, update checks, help links, and license

Each tab manages its own list live — there's no separate page-wide Save button; every add/edit/delete takes effect immediately.

---

## Managing Lookup Lists (Brands, Part Types, Locations, Vendors)

These four tabs are functionally identical: a plain list of names with an **Add New** button and per-row **Edit**/**Delete**.

- **Brands** — used by Inventory items, Printer manufacturers, and Filament Material Blueprints
- **Part Types** — used only by Inventory items (e.g. "Filament", "Nozzle", "Tool")
- **Locations** — used only by Inventory items (e.g. "Shelf A", "Drawer 3")
- **Vendors** — used only by Inventory items

> 📷 **Screenshot needed** — the Brands tab with its Add New / Edit / Delete controls

Click **Add New** to open a modal with a single **Name** field. Click **Edit** on any row to rename it, or **Delete** to remove it (asks for a simple confirmation).

> **Note**: Deleting a Brand, Part Type, Location, or Vendor that's currently in use does **not** delete or block anything that references it — it just clears that field on every Inventory item or Printer that pointed to it, silently. The confirmation dialog doesn't tell you how many records will be affected, so double-check a value isn't in active use before deleting it if you want to avoid orphaned records.

Most of the time you won't visit these tabs directly — every Brand/Part Type/Location/Vendor field elsewhere in the app is type-ahead and creates new entries on the fly the first time you type one. Settings is where you go to clean up typos or rename something after the fact.

---

## Materials (Generic Types)

Settings → **Materials** manages only the **generic base material types** (PLA, PETG, ABS, TPU, etc.) — not brand-specific Material Blueprints, which live in **Filament → Blueprints**. Print Vault ships with 12 built-in types; add, rename, or delete your own the same way as the other lookup tabs.

This is the same master list that populates every **Base Material Type** and **Material Type** dropdown in the Filament section — see `docs/FILAMENT_USER_GUIDE.md`.

---

## Features

Settings → **Features** manages the reusable tags (e.g. "Matte", "High Speed", "Glitter", "Carbon Filled") you can apply to Filament Material Blueprints to keep specialty filaments searchable. Same Add/Edit/Delete pattern as the other lookup tabs — but here, the delete confirmation explicitly warns you that deleting a feature **removes it from every material that currently uses it**.

---

## Preferences

Currently just one setting: **Appearance** — a toggle between Light Mode and Dark Mode. Your choice is saved in your browser and applies immediately across the whole app.

> 📷 **Screenshot needed** — the Preferences tab's theme toggle

---

## Data Management

### Export Data & Files

Click **Export Backup** to download a single ZIP archive containing your data and every uploaded photo/file. Use this before any risky operation, and periodically as a general backup.

### Restore from Backup

Upload a previously exported ZIP and click **Restore from Backup**. The file is validated first — if any records fail validation, a warning modal breaks down the errors by type (with sample IDs and messages) and lets you either cancel or **Proceed with Partial Import** (valid records are imported, invalid ones are skipped). Either way, a final confirmation step requires typing **RESTORE** exactly and checking an acknowledgment box before anything happens.

> **Restoring wipes all current data and files first.** There is no merge — it's a full replace.

> **Backups aren't backward-compatible across major upgrades.** If you're restoring a backup made by a much older version of Print Vault, uploading it may be rejected with a message telling you it needs that older version to restore. If you hit this, either use the Print Vault version that originally created the backup, or start fresh.

> 📷 **Screenshot needed** — the restore validation warning modal

### Danger Zone — Delete All Data

**Delete All Data & Files** permanently removes everything — inventory, printers, projects, and every uploaded file. Like Restore, it requires typing an exact confirmation phrase (**DELETE ALL**) and checking an acknowledgment box before the button becomes clickable. This cannot be undone and has no backup step built in — export first if there's any chance you'll want the data back.

---

## About

- **Version Information** — frontend/backend version numbers, git commit and branch, Python/Django versions, and build time. If the frontend and backend versions don't match, a warning tells you to rebuild your containers or clear your browser cache. **Copy Version Info** copies all of this plus your browser/OS details to the clipboard — handy when asking for support.
- **Update Available** banner — checks GitHub for a newer release and links to the release notes; dismissing it only suppresses that specific version's notice, a genuinely newer release will show again.
- **Help & Support** — links to the GitHub repository, documentation, issue tracker, Discord, and a support email address.
- **License** — Print Vault is AGPL-3.0 licensed; the tab spells out in plain language what that does and doesn't allow, including a note on SaaS hosting obligations.

> 📷 **Screenshot needed** — the About tab's Version Information section

---

## Common Use Cases

### Setting Up Your Lookup Lists Before a Bulk Import

If you're about to CSV-import a large batch of Inventory items, pre-populate **Brands**, **Part Types**, **Locations**, and **Vendors** with consistent names first — the import auto-creates any value it doesn't recognize, so cleaning these up beforehand (or right after, via Settings) avoids ending up with near-duplicate entries from typos.

### Backing Up Before a Risky Change

Before running a Restore or Delete All (or just before a big manual cleanup), click **Export Backup** in Data Management. It's the only way back if something goes wrong.

### Reporting a Bug

Open **About**, click **Copy Version Info**, and paste it into your GitHub issue or Discord message along with a description of the problem — it saves a round-trip of "what version are you on?"

---

## Tips

- Renaming a Brand/Part Type/Location/Vendor here updates it everywhere it's used; deleting one does not — it just clears the field on anything that referenced it, with no count or warning shown first.
- Both **Restore from Backup** and **Delete All Data** require typing an exact confirmation phrase (case-sensitive) — this is deliberate friction, not a bug, given neither action can be undone.
- Theme preference is stored per-browser, not tied to any account — switching browsers or devices means setting it again.
- Settings → Materials only manages generic base types; if you're looking for brand-specific filament specs, that's Filament → Blueprints, not here.

---

## Related Sections

- **Inventory** — where Brand/Part Type/Location/Vendor lookups are used day-to-day: `docs/INVENTORY_USER_GUIDE.md`
- **Printers** — where the Brand lookup is used for Manufacturer: `docs/PRINTERS_USER_GUIDE.md`
- **Filament** — where generic Material types and Features are used: `docs/FILAMENT_USER_GUIDE.md`
