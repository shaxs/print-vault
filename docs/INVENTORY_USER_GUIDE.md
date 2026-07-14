# Inventory Guide

**Print Vault** — User Documentation
**Feature**: Inventory / Parts Management
**Last Updated**: 2026-07-10

---

## What Is the Inventory System?

Inventory is where you track everything in your workshop that isn't filament: screws, boards, sensors, brackets, tools, and any other part or supply you buy for your builds. Each item records what it is, how much of it you have, where it lives, what it costs, and — optionally — a photo and notes.

Core capabilities:

- **Inventory Items** — title, optional Brand/Part Type/Location/Vendor, a Model number, Quantity, Cost, Photo, and Notes
- **Free-taggable lookup lists** — Brand, Part Type, Location, and Vendor are all type-ahead fields that create new entries on the fly; the master lists are also managed centrally from **Settings**
- **Two ways to link an item to a project** — an informal **Associated** soft link, or a structured, quantity-tracked **Bill of Materials (BOM)** entry that reserves stock (see [Associated Projects vs. Bill of Materials](#associated-projects-vs-bill-of-materials))
- **BOM Allocation** — an item used in one or more project BOMs shows a live Covered/Running Low/Overallocated/Ordered status right on its own detail page
- **CSV import** — bulk-load an existing parts bin in one pass
- **Low stock alerts** — flag any item with a warning threshold and get notified in the app's global notification bell when it's reached

> **Note**: Inventory is a different feature from **Filament**. Filament is a dedicated system for spool-level weight tracking, print temperatures, and per-spool location/printer assignment — see `docs/FILAMENT_USER_GUIDE.md`. Inventory is for everything else.

---

## Getting Started

Open **Inventory** from the sidebar (route `/inventory`) to land on the **Parts List**. The header toolbar has **Filter**, **Columns**, **Import**, a live **Search** box, and a blue **Add** button.

> 📷 **Screenshot needed** — the Parts List page showing the toolbar and item table

The table has one row per item, with these available columns (toggle visibility from **Columns**):

| Column | Shown by default | What it shows |
|---|---|---|
| Title | ✅ | Item name, links to its detail page |
| Photo | | Thumbnail |
| Brand | ✅ | |
| Part Type | ✅ | |
| Location | ✅ | |
| Physical Stock | ✅ | Actual units you own (see [Quantity: Physical Stock vs. Available](#quantity-physical-stock-vs-available)) |
| Qty Allocated | ✅ | Units currently reserved by active project BOMs |
| Qty Needed | ✅ | Shortfall — only populated when you're short (shown in red) |
| Cost | | Cost per unit |

Your column choices and any active filters are remembered in your browser across visits. Clicking a row opens that item's detail page and remembers the filtered list you came from, so the detail/edit views can offer **Save + Back** / **Save + Next** navigation between items without bouncing back to the list each time (see [Editing an Item](#editing-an-item)).

---

## Creating an Inventory Item

Click **Add** to open **Add New Item**:

- **Title** (required)
- **Associated Projects** — multi-select; type to search existing projects or type a new name to create one on the fly (new projects start in **Planning** status)
- **Brand**, **Part Type**, **Location**, **Vendor** — each a type-ahead field; type a new value and it's created for you the first time you use it
- **Vendor Link** — URL to the product page
- **Model Number**
- **Quantity** — defaults to 1
- **Cost**
- **Photo** — with a preview once selected
- **Notes**
- **Enable Low Stock Alert** checkbox — reveals a **Low Stock Warning Level** number field when checked (see [Low Stock Alerts and Notifications](#low-stock-alerts-and-notifications))

> 📷 **Screenshot needed** — the Add New Item form

Buttons: **Cancel**, **Save + Add Another** (saves the item, clears the form, and keeps you on the page so you can keep entering items — also triggered by `Ctrl+Enter`), and **Save** (saves and takes you to the item's detail page).

---

## The Item Detail View

Click into any item to see its **Item Photo** (click to enlarge), an **Item Details** card (Brand, Part Type, Location, Vendor with a clickable link if a Vendor Link is set, Model, **Qty Available**, Cost, and — if the item is consumable — "Low Stock Alert: Enabled" plus the Warning Threshold), and a Notes section if notes were entered.

An **Associated Projects** card lists any projects this item is soft-linked to, with a **Remove** button per row; clicking a project row navigates to that project.

> 📷 **Screenshot needed** — the item detail page

Header buttons: **← Back to Inventory**, **Edit**, **Delete** (asks for confirmation — deleting cannot be undone).

If the item is used in any project's Bill of Materials, a **BOM Allocation** card also appears — see [BOM Allocation on an Inventory Item](#bom-allocation-on-an-inventory-item).

---

## Editing an Item

Click **Edit** to open the same form pre-filled with the item's current values.

**The Quantity field always shows your physical stock — never a raw, possibly-negative internal number.** If any active project BOM has reserved units of this item, a hint appears below the field:

> *"X unit(s) currently reserved by active project BOMs. Enter your actual physical stock on hand."*

Always type in the real number of units on your shelf. Print Vault converts that into the correct internal reserved value automatically — you never need to do the subtraction yourself.

If you opened this item from a filtered or searched list, the form shows **Save + Back** and **Save + Next** buttons instead of (in addition to) the plain Save button, letting you save the current item and jump straight to the previous/next item in that same filtered set — useful for working through a batch of items (e.g. updating everyone's Location after a shelf reorganization) without returning to the list in between.

> 📷 **Screenshot needed** — the Edit form showing the BOM reservation hint

---

## Quantity: Physical Stock vs. Available

This is the most important nuance in the Inventory system, and it mirrors the reservation model described in `docs/BOM_USER_GUIDE.md`.

- **Physical Stock** (list column) is always the real number of units you own — full stop.
- **Qty Allocated** (list column) is how much of that stock is currently committed to active project Bills of Materials.
- **Qty Needed** (list column, red text) only appears when you're short — it's the number of additional units you need to buy to cover every active commitment.
- **Qty Available** (shown on the item's detail page, *not* the list) is Physical Stock minus Qty Allocated, floored at **0**. It will never show a negative number, even if you're technically over-committed.

> **Note**: "Physical Stock" and "Qty Available" are deliberately different numbers shown in different places. The list's Physical Stock column is what you actually own; the detail page's Qty Available field is what's left over after subtracting everything already promised to project BOMs.

Being overallocated — owning fewer units than your active projects have reserved — is expected during planning, not an error. It's Print Vault's way of telling you what to shop for before you start a build. See the next section for how that shows up on the item itself.

---

## BOM Allocation on an Inventory Item

Once an item is added to the Bill of Materials of one or more projects, its detail page grows a **BOM Allocation** card.

The summary row shows:

- **Committed to Projects** — total quantity reserved across all active project BOMs
- **Status** — a colored badge:

| Status | Color | Meaning |
|---|---|---|
| Covered | 🟢 Green | Enough stock on hand for everything committed |
| Running Low | 🟡 Yellow | Consumable item, alert enabled, and available quantity has dropped to or below your Low Stock threshold |
| Overallocated | 🔴 Red | Committed quantity exceeds what you physically own |
| Ordered | 🟢 Green | Overallocated, but you've flagged a restock order as placed |

When overallocated, two extra cells appear: **Physical Stock** (what you own before any commitments) and **Qty to Buy** (in red). An **Actions** cell shows **Mark as Ordered** while overallocated — click it to flip the badge to green "Ordered" and signal the shortage is being handled — or **Undo Ordered** to revert if the order falls through.

Below the summary, an **Active Projects** table lists every project in Planning, In Progress, or On Hold status that has this item in its BOM, with the quantity allocated to each and a **Remove** button (removing returns that quantity to your stock). A collapsible **Closed Projects** section shows past usage in Completed or Canceled projects — Canceled ones show `↩ X returned` to mark that the stock was given back automatically when the project was canceled.

> 📷 **Screenshot needed** — the BOM Allocation card in its overallocated state

For the full BOM workflow — the BOM Wizard, adding/editing BOM items, project lifecycle effects on stock — see `docs/BOM_USER_GUIDE.md`.

---

## Associated Projects vs. Bill of Materials

An inventory item can connect to a project two different ways, and it's worth knowing which one you're using:

- **Associated (soft link)** — no quantity tracking, just "this item is relevant to this project." Set it from the item's own **Associated Projects** field on create/edit, or from the project's own **Associated Inventory Items** section via its **Add Inventory** button.
- **Bill of Materials item** — structured, quantity-aware, and reserves stock the moment it's added.

An item can be Associated **or** in a project's BOM, never both for the same project. If you've already soft-linked an item and later want to start tracking it formally, go to the project page and click **Move to BOM** on that item's row — it opens the BOM item form pre-linked to this item, and saving it automatically removes the old soft association.

Full comparison table and workflow: `docs/BOM_USER_GUIDE.md#bom-items-vs-associated-inventory-items`.

---

## Importing Items from CSV

Click **Import** from the Parts List toolbar to open **Import Inventory Items**. Click **Download CSV Template** first if you need a starter file with the correct header row and one example row.

| Column | Required | Notes |
|---|---|---|
| `title` | ✅ | Rows with a blank title are counted as errors and skipped |
| `brand` | | Created automatically if it doesn't already exist |
| `part_type` | | Created automatically if it doesn't already exist |
| `location` | | Created automatically if it doesn't already exist |
| `vendor` | | Created automatically if it doesn't already exist |
| `vendor_link` | | |
| `model` | | |
| `quantity` | | Defaults to 1 if left blank |
| `cost` | | |
| `notes` | | |

> 📷 **Screenshot needed** — the Import Inventory Items modal

**Things to know before you upload:**

- **Matching is by exact Title.** If a title already exists in your inventory, that row is skipped, not updated — re-running the same file is safe and won't create duplicates.
- **Brand/Part Type/Location/Vendor are created on the fly** — keep spelling consistent, since "Amazon" and "amazon.com" would create two separate vendors instead of reusing one.
- Save the file as **UTF-8** CSV.

After uploading, a result summary shows how many rows were **Created** and **Skipped**, plus a list of any row-level errors (row number + reason) so you can fix and re-upload just the problem rows.

---

## Filtering, Searching, and Columns

Click **Filter** to narrow the table by **Brand**, **Part Type**, or **Location** (each defaults to "All"). A **"Filters are active"** banner appears above the table whenever a filter or search term is applied, with a **Clear Filters** link to reset.

The **Search** box does a live text search across Title, Notes, Brand name, Part Type name, and Location name. **Columns** lets you choose which of the table columns are visible — Photo and Cost are hidden by default.

---

## Low Stock Alerts and Notifications

Check **Enable Low Stock Alert** on any item (create or edit) and set a **Low Stock Warning Level**. When that item's available quantity drops to or below the threshold, it shows up in the app's global notification bell (top of every page, alongside reminders) with its title and current quantity vs. threshold — clicking it takes you straight to the item.

> 📷 **Screenshot needed** — the notification bell showing a low-stock alert

This is independent of BOM allocation status — an item can trigger a low-stock alert purely on physical count, whether or not it's in any project's Bill of Materials at all. (The **Running Low** status on the BOM Allocation card, by contrast, only applies to items that are also consumable-flagged and used in an active BOM — see [BOM Allocation on an Inventory Item](#bom-allocation-on-an-inventory-item).)

---

## Common Use Cases

### Adding a New Part You Just Bought

1. Click **Add** from the Parts List.
2. Fill in Title, Quantity, and Cost; use the type-ahead fields for Brand, Part Type, and Location.
3. Turn on **Enable Low Stock Alert** if it's something you'll want to reorder before you run out.
4. Click **Save** to land on the new item's detail page.

### Bulk-Loading an Existing Parts Bin

1. Click **Import**, then **Download CSV Template**.
2. Fill it in with your existing stock — one row per item — and save as UTF-8.
3. Upload it and review the result summary. Fix and re-upload just the rows listed under errors; already-imported rows are skipped automatically, so it's safe to re-run.

### An Item Runs Low Mid-Build

1. You get a low-stock notification in the bell, or notice a red **Qty Needed** value on the Parts List.
2. Open the item's detail page. If it's tied to a project BOM, the **BOM Allocation** card shows exactly how many units you're short (**Qty to Buy**).
3. Click **Mark as Ordered** on the Allocation card so the status reads "Ordered" instead of "Overallocated" while you wait on the restock.
4. When the parts arrive, **Edit** the item and enter your new physical count in Quantity — Print Vault recalculates the reservation math and the status resolves back to Covered on its own.

---

## Tips

- Keep Brand/Part Type/Location/Vendor spelling **consistent** — they're all free-taggable, so a typo creates a duplicate entry rather than reusing the existing one.
- Use **Save + Add Another** (or `Ctrl+Enter`) when logging a batch of new items in one sitting.
- Always enter your **real physical count** in the Quantity field, both on create and edit — let Print Vault handle the reservation math against active BOMs rather than trying to pre-subtract it yourself.
- CSV import is idempotent by title — you can safely re-run the same file later to pick up only the rows you haven't imported yet.
- If you soft-linked an item to a project and later need to actually reserve stock for it, use **Move to BOM** on the project page instead of removing and re-adding it.

---

## Related Sections

- **Bill of Materials** — the full BOM workflow, the BOM Wizard, and how project status changes affect reserved stock: `docs/BOM_USER_GUIDE.md`
- **Filament** — spool-level weight/quantity tracking is a separate system from Inventory: `docs/FILAMENT_USER_GUIDE.md`
- **Settings → Brands / Part Types / Locations / Vendors** — manage the master lookup lists used throughout Inventory
- **Projects** — a project's **Associated Inventory Items** section is where soft links are added and where **Move to BOM** lives
