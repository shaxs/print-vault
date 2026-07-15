# Projects Guide

**Print Vault** — User Documentation
**Feature**: Projects
**Last Updated**: 2026-07-11

---

## What Is the Project System?

A Project is the hub that ties a build together: its status, timeline, the printers and inventory involved, the filament materials it needs, reference links and files, any Print Trackers for its parts, and — for structured builds — a full Bill of Materials.

Core capabilities:

- **Project record** — name, description, status, start/due dates, a photo/render, and notes
- **Status lifecycle** — Planning, In Progress, Completed, Canceled, On Hold — with confirmation prompts when canceling or re-opening a project that has reserved inventory
- **Associated Printers** and **Associated Inventory Items** — soft links for reference (see `docs/INVENTORY_USER_GUIDE.md` for the Associated-vs-BOM distinction)
- **Bill of Materials** — a structured, quantity-tracked parts list with stock allocation; the full workflow lives in `docs/BOM_USER_GUIDE.md`
- **Materials** — a free-form list of the filament colors/materials this build needs, each either a custom text description or a live link to a Material Blueprint
- **Links and Files** — reference URLs and downloadable attachments (guides, configs, renders), managed on their own pages
- **Print Trackers** — the per-part print-progress trackers tied to this project show up here with a live progress bar
- **Health and alerts** — the Dashboard surfaces overdue, due-soon, and printer-blocked status for your active builds

---

## Getting Started

Open **Projects** from the sidebar (route `/projects`). The header toolbar has **Filter**, **Columns**, a live **Search** box, and a blue **Add** button.

> 📷 **Screenshot needed** — the Projects list page

Table columns: Photo, Project Name, Status, Description. Photo, Project Name, and Status are visible by default; Description is off by default. Your column choices and filters persist across visits.

---

## Creating a Project

Click **Add** to open the project form:

- **Project Name** (required)
- **Status** — Planning / In Progress / Completed / Canceled / On Hold (defaults to Planning)
- **Start Date** and **Due Date** — Due Date drives the Dashboard's overdue/due-soon tracking (see [Project Health and Alerts](#project-health-and-alerts))
- **Description**
- **Associated Inventory Items** — multi-select from your existing inventory (soft link, no quantity tracking)
- **Associated Printers** — multi-select from your existing printers
- **Associated Print Trackers** — multi-select from your existing trackers
- **Materials** — click **+ Add Material** for each color/material this build needs: a free-text **Label** (e.g. "Primary", "Accent", "Support"), then either **Custom Material** (free text, e.g. "Red ASA") or **Material Blueprint** (a live link into your Filament library)
- **Photo / Render**
- **Notes**

> 📷 **Screenshot needed** — the Add Project form, including the Materials section

Buttons: **Cancel**, **Save & Create BOM** (create mode only — saves the project and jumps straight into the BOM Wizard so you can start entering parts immediately), and **Save Project** (saves and goes to the project's detail page).

---

## The Project Detail View

The header shows the project's photo (click to enlarge), name, and **← Back to Projects**, **Edit**, and **Delete** buttons.

### Project Details Card

Shows a colored **Status** badge, **Description**, **Notes**, an **Associated Printers** list (each linking to that printer), a **Materials** section when set (color swatch + link to the Material Blueprint, or plain custom text), and an **Assigned Spools** list — any Filament spool whose Location & Assignment points at this project shows up here automatically with its status badge (see `docs/FILAMENT_USER_GUIDE.md`).

> 📷 **Screenshot needed** — the Project Details card

### Resources Card

- **Links** — a plain list of reference URLs (assembly guides, product pages, etc.), managed from a **Manage Links** page
- **Files** — downloadable attachments, with a **Download All** button (zips everything) and a **Manage Files** page for uploading/removing individual files
- **Print Trackers** — every tracker tied to this project, each with a progress bar and printed/total part counts; **New Tracker** creates one pre-linked to this project

> 📷 **Screenshot needed** — the Resources card showing Links, Files, and Print Trackers

### Bill of Materials Card

Shows once you start using the BOM system on this project — status filter chips, the BOM Wizard, CSV import, and per-item allocation badges. This is covered in full in `docs/BOM_USER_GUIDE.md`.

### Associated Inventory Items Card

Lists items soft-linked to this project (added via **Add Inventory**), each with **Move to BOM** (converts the soft link into a tracked BOM entry) and **Remove**. See `docs/INVENTORY_USER_GUIDE.md#associated-projects-vs-bill-of-materials` for the full comparison.

---

## Editing a Project

Click **Edit** to reopen the same form pre-filled, including Materials and all associations.

**Changing Status to Canceled**: if the project has any inventory-linked BOM items, a confirmation modal appears first, telling you how many units will be returned to stock, before the save goes through.

**Changing Status back to Planning / In Progress / On Hold from Canceled**: a confirmation modal warns that previously-linked BOM items will be **re-reserved**, reducing your available inventory again.

Both flows are described in full, including exactly how the underlying stock math works, in `docs/BOM_USER_GUIDE.md#project-lifecycle-and-inventory-impact`.

---

## Managing Links

From the project detail page, click **Manage Links** to open a dedicated page: fill in **Link Name** and **URL** and click **Add Link**. Existing links are listed below with **✎ Edit** and **✕ Delete** controls; editing loads the link back into the form with the button relabeled **Update Link**.

> 📷 **Screenshot needed** — the Manage Links page

---

## Managing Files

Click **Manage Files** to open a dedicated page. Existing files are listed with an **✕** to mark them for deletion (they're only actually removed once you save). Drag-and-drop files onto the drop zone, or click it to pick files, then save to upload. From the project detail page itself, **Download All** zips every attached file into one download.

> 📷 **Screenshot needed** — the Manage Files page with the drop zone

---

## Project Status Reference

| Status | Meaning |
|---|---|
| **Planning** | Early stage — BOM/parts being worked out, nothing purchased or committed yet |
| **In Progress** | Actively being built — the only status that shows up in the Dashboard's Active Projects/health view |
| **On Hold** | Paused, but still counted as "active" for inventory reservation purposes |
| **Completed** | Finished — BOM-reserved inventory is treated as consumed, no stock is returned automatically |
| **Canceled** | Abandoned — any inventory reserved by its BOM items is returned to stock immediately |

Planning, In Progress, and On Hold are all treated as **active** for BOM stock-reservation purposes; Completed and Canceled are **closed**. Full detail on what each status transition does to your inventory numbers: `docs/BOM_USER_GUIDE.md`.

---

## Deleting a Project

Click **Delete** on the project detail page. If the project has inventory-linked BOM items and isn't already Canceled, the confirmation modal offers a checkbox to **return those units to stock** — check it if the parts are still in your possession, leave it unchecked if they were already used. Already-Canceled projects skip this choice, since their inventory was returned when they were canceled. Deletion is permanent.

---

## Project Health and Alerts

Two separate places surface a project's timeline/printer status:

### Dashboard Active Projects (health badges)

Only shown for projects currently in **In Progress** status. Each gets a health badge, worst-case first:

| Health | Meaning |
|---|---|
| **Overdue** | Due Date has passed |
| **Blocked** | Every Associated Printer is Under Repair, Sold, or Archived |
| **Partially Blocked** | Some (not all) Associated Printers are unavailable |
| **At Risk** | Due Date is within the next 7 days |
| **Healthy** | None of the above |

> 📷 **Screenshot needed** — the Dashboard's Active Projects section with health badges

### Dashboard Notifications (dismissible alerts)

- **Project Overdue** (critical) — any project not marked Completed with a Due Date in the past
- **Project Due Soon** (warning) — Due Date within the next 7 days
- **Project Blocked** (critical) — an **In Progress** project with one or more unavailable Associated Printers

Dismissing one of these clears it from the notification list until the underlying condition changes again (a new due date, a printer coming back online, etc.) — see `docs/PRINTERS_USER_GUIDE.md#printer-status-reference` for how printer status feeds this.

---

## Filtering, Searching, and Columns

Click **Filter** to narrow the list by **Status** (defaults to "All"). The **Search** box does a live text search. **Columns** lets you choose which table columns are visible; your choices and filters persist across visits.

---

## Common Use Cases

### Starting a New Build from a Creator's Published BOM

1. Click **Add**, fill in Project Name and Status (**Planning** is the natural starting point).
2. Click **Save & Create BOM** instead of the plain Save button — this drops you straight into the BOM Wizard so you can start entering the creator's parts list right away.
3. Once your BOM is entered, use the Associated Printers field (via Edit) to link the printer(s) you'll build it on.

### Setting Up Materials and Printers for a Build

1. Open the project and click **Edit**.
2. Add one Materials entry per color/role in the build (Primary, Accent, Support, etc.), linking each to a Material Blueprint where you have one on file.
3. Add the printer(s) this build will run on to Associated Printers — this is what lets the Dashboard tell you if the build is Blocked when one of them goes down for repair.

### Wrapping Up or Abandoning a Project

- **Finished the build?** Edit the project and set Status to **Completed** — nothing changes about your inventory; the parts are treated as used.
- **Abandoning it?** Edit the project and set Status to **Canceled** — confirm the modal, and any inventory reserved by its BOM is returned to stock automatically.

---

## Tips

- Use **Save & Create BOM** when you have a creator's parts list in front of you — it saves a trip back to the project page to find the BOM Wizard button.
- Materials on a project are informational, like a printer's assigned materials — they don't reserve stock. Use the BOM system for anything you actually need to track against inventory.
- Set a Due Date even on loose builds — it's what powers the Dashboard's overdue/at-risk signals, and it's easy to forget since it isn't shown anywhere on the project detail page itself, only in the Edit form and on the Dashboard.
- Keep Associated Printers accurate — it's the only thing driving a project's Blocked/Partially Blocked health, so an unused or outdated printer link can produce a false alert.

---

## Related Sections

- **Bill of Materials** — the full BOM workflow, allocation statuses, and exactly how project status changes affect reserved stock: `docs/BOM_USER_GUIDE.md`
- **Inventory** — Associated vs. BOM items, and the items a project can pull from: `docs/INVENTORY_USER_GUIDE.md`
- **Printers** — Associated Printers, maintenance, and the status values that drive a project's Blocked health: `docs/PRINTERS_USER_GUIDE.md`
- **Filament** — Material Blueprints used by a project's Materials list, and per-spool project assignment: `docs/FILAMENT_USER_GUIDE.md`
