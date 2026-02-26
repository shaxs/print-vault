# Bill of Materials (BOM) Guide

**Print Vault** — User Documentation  
**Feature**: Bill of Materials  
**Last Updated**: 2026-02-25

---

## What Is the BOM System?

When you're building a complex 3D printer project — a Voron, a Box Turtle MMU, a toolchanger — the creator publishes a Bill of Materials: every bolt, board, sensor, bracket, and cable that goes into the build, with exact quantities.

Print Vault's **BOM system** lets you:

- Enter that parts list directly against your project
- Link each part to your existing inventory
- See instantly whether you have enough stock on hand — across **all** your active projects at the same time
- Know exactly what you still need to buy

The key idea: once you link a BOM item to an inventory item, Print Vault **immediately reserves** that quantity in your stock. If you're building two projects that both need an EBB36 CAN board, the system will warn you that you're over-reserved before you even start ordering.

> 📸 *[Screenshot: Project detail page showing the BOM section alongside the Associated Inventory Items section]*

---

## BOM Items vs. Associated Inventory Items

Print Vault has **two ways** to connect inventory to a project, and it's worth understanding the difference:

|                           | Associated Inventory Items                                              | Bill of Materials Items                                              |
| ------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Purpose**               | Informal "I bought this for this project" link                          | Formal structured parts list from the creator's BOM                  |
| **Quantity tracking**     | No — just a loose association                                           | Yes — specific quantity needed per item                              |
| **Inventory reservation** | No — does not affect your stock count                                   | Yes — immediately decrements your available quantity                 |
| **When to use**           | You purchased a part earmarked for a project before you have a full BOM | You're following a creator's published BOM and want precise tracking |

**Short version**: Associated Inventory Items are a quick, informal tag. BOM Items are structured, quantity-aware, and affect your inventory counts. For serious build tracking, use the BOM system.

---

## Getting Started

### Step 1: Create Your Project

Before adding a BOM, you need a project. Go to **Projects → Add Project** and fill in the project name.

For the **Status** field: any active status works — **Planning** is the natural starting point for a new build, but you can also use **In Progress** or **On Hold** if the project is already underway. All three statuses will track inventory reservations.

When saving, you have two options:

- **Save** — saves the project and takes you to the project detail page
- **Save and Create BOM** — saves the project and immediately opens the BOM Wizard so you can start entering parts right away (recommended if you have the creator's BOM in front of you)

> 📸 *[Screenshot: New project form showing the Status dropdown and the "Save and Create BOM" button]*

### Step 2: Open the Project and Go to the BOM Section

From your project's detail page, scroll down to the **Bill of Materials** section. If no items have been added yet, you'll see an empty table with an **"Add Item"** button and a **"BOM Wizard"** button in the header.

> 📸 *[Screenshot: Project detail page with the empty BOM section visible, highlighting the Add Item and BOM Wizard buttons]*

---

## Entering Your BOM

### Option A — BOM Wizard (Recommended for Initial Entry)

The **BOM Wizard** (`/projects/:id/bom/edit`) is designed for fast, bulk data entry. Use it when you're working through a creator's BOM for the first time.

1. Click **"BOM Wizard"** from the project detail page header
2. For each part, fill in:
   - **Description** — copy it from the creator's BOM as-is (e.g., `M3×8 SHCS`, `EBB36 CAN Toolhead Board`)
   - **Quantity** — the number you need for your specific build variant (e.g., 300mm, not 250mm)
   - **Inventory Link** — type to search your inventory and link the part. **Leave this blank if you don't have this item in your inventory yet** — you can always link it later once you've added the item to your inventory
   - **Needs Purchase toggle** — check this if you know you need to buy this item and don't intend to track it against existing inventory
3. Click **"Add"** to queue the item — it appears in the table below
4. Continue adding items until your full BOM is entered
5. Click **"Save All"** (or the equivalent submit action) to commit everything

> 📸 *[Screenshot: BOM Wizard showing the entry form at the top and a partially filled parts list below]*

**While in the Wizard:**

- You can **edit** any row using the blue Edit button (this works for both newly queued rows and already-saved existing rows)
- You can **remove** any row using the red Remove button — if the item was linked to inventory and the project is active, you'll be asked whether to return the reserved stock

### Option B — Add Individually

After the initial wizard session, you can continue adding items one at a time directly from the Project Detail page:

1. Click **"Add Item"** in the BOM section header
2. Fill in description, quantity, and optionally link to inventory — **leave the inventory link blank if the item isn't in your inventory yet**
3. Click **"Add Item"** to save

> 📸 *[Screenshot: Add BOM Item modal showing the description, quantity, inventory typeahead, and Needs Purchase toggle]*

---

## BOM Item Statuses

Every BOM item has two status indicators:

### Item Link Status

| Status             | Meaning                                                                                        |
| ------------------ | ---------------------------------------------------------------------------------------------- |
| **Linked**         | The BOM item is connected to a specific inventory record                                       |
| **Unlinked**       | Not yet connected to any inventory item                                                        |
| **Needs Purchase** | You've explicitly flagged this item as something you need to buy (no inventory match expected) |

### Allocation Status (Inventory Health)

This tells you whether your linked inventory item has enough stock:

| Status             | Color     | Meaning                                                                                                               |
| ------------------ | --------- | --------------------------------------------------------------------------------------------------------------------- |
| **Covered**        | 🟢 Green  | You have enough on hand for this BOM item                                                                             |
| **Low**            | 🟡 Yellow | You have some stock, but it's at or below your low-stock threshold                                                    |
| **Overallocated**  | 🔴 Red    | Your linked inventory item has been over-reserved — the quantity on hand has gone negative across all active projects |
| **Ordered**        | 🟢 Green  | You are overallocated but have placed a restock order — the shortage is being addressed                               |
| **Needs Purchase** | ⚪ Gray    | Not linked to inventory; flagged for purchase                                                                         |
| **Unlinked**       | ⚪ Gray    | Not yet linked to inventory                                                                                           |

> **Tip**: Overallocated doesn't mean something is broken — it means you've committed more of that part than you have. This is expected when planning multiple simultaneous builds. Use it as your shopping signal.

> 📸 *[Screenshot: BOM table on a project page showing all four status badge states—Covered, Low, Overallocated, and Needs Purchase]*

---

## Filtering the BOM Table by Status

Both the **BOM Wizard** and the **Project Detail page** show a row of filter chips above the parts list. Use these to instantly narrow down the view without leaving the page.

### How to Use

Click any chip to show only items matching that status. Click **All** to return to the full list.

| Chip | Shows |
|------|-------|
| **All** | Every item in the list (default) |
| **Covered** | Items with sufficient stock on hand |
| **Running Low** | Items where stock is at or below the low-stock threshold |
| **Overallocated** | Items where the allocated quantity exceeds what's on hand |
| **Needs Purchase** | Items explicitly flagged for purchase (no inventory link) |
| **Not Linked** | Items not yet connected to any inventory record |

Each chip shows a count of matching items. **Chips are only shown when at least one item matches** — if all your items are Covered, you'll only see the **All** and **Covered** chips.

> 📸 *[Screenshot: BOM table filter chips row with "Overallocated" chip selected, showing a filtered list of only the over-reserved items]*

### Tips

- **In the BOM Wizard**: the filter applies to the items queued in the table below the entry form. Items you add during the current session will appear and be filterable immediately.
- **On the Project Detail page**: the filter applies to the full saved BOM list.
- The filter resets to **All** on page reload — it is not persisted.

---

## How Inventory Reservation Works

This is the most important nuance to understand.

**The moment you add a BOM item linked to an inventory item, Print Vault decrements your available stock.**

For example:

- You have **10× M3×8 SHCS** in inventory
- You add a BOM item for your Voron project: `M3×8 SHCS × 4`, linked to that inventory item
- Your inventory immediately shows **6× M3×8 SHCS** available (not 10)
- Those 4 are now "spoken for" — reserved for the Voron project

If you then add a second project (Box Turtle) and add `M3×8 SHCS × 8` to its BOM:

- Your inventory shows **−2× M3×8 SHCS** (overallocated by 2)
- Both project BOM tables show an **🔴 Overallocated** badge for that item

This is by design. You can see the problem immediately and decide whether to order more or reprioritize.

### What affects the reserved quantity

| Action                                | Inventory Effect                            |
| ------------------------------------- | ------------------------------------------- |
| Add a BOM item with inventory link    | − decrements qty                            |
| Remove a BOM item with inventory link | + restores qty                              |
| Edit a BOM item's quantity            | adjusts the delta                           |
| Edit a BOM item's inventory link      | restores old, decrements new                |
| Mark a BOM item as Needs Purchase     | + restores qty (no longer a reservation)    |
| Cancel a project                      | + restores qty for all BOM items            |
| Re-open a cancelled project           | − re-decrements qty for all BOM items       |
| Complete a project                    | no change (items were physically consumed)  |
| Delete a project                      | see [Project Deletion](#deleting-a-project) |

---

## Editing and Removing BOM Items

### Editing

Click the **Edit** button on any BOM item row. A modal opens pre-populated with all the item's current values:

- Change the description
- Change the quantity (inventory reservation adjusts automatically)
- Change or remove the inventory link
- Add or edit notes

Click **"Save Changes"** to apply.

### Removing a BOM Item

Click the **Remove** button on any row. A confirmation dialog appears. If the item was linked to inventory, it will show how many units will be returned to stock when confirmed.

> Projects that are cancelled or completed will note that quantity was "returned to inventory" or was "previously consumed" depending on the project's state at removal time.

---

## Viewing Allocation from Inventory

When you view an inventory item's detail page, scroll down to the **"BOM Allocation"** panel. It shows:

- **Committed to Projects** — total quantity currently reserved across all active projects
- **Status** — whether the item is covered, low, or overallocated

### Active Projects Table

Lists every active project (Planning / In Progress / On Hold) that has this inventory item in its BOM, along with how many units are allocated to each project.

### Closed Projects Table

Shows projects that are **Completed** or **Cancelled** that previously had this item in their BOM:

- **Completed** projects show the quantity that was consumed
- **Cancelled** projects show `↩ X returned` — indicating that quantity was returned to stock when the project was cancelled

This gives you a full history of where the part has been used.

> 📸 *[Screenshot: Inventory item detail page showing the BOM Allocation panel with Active Projects and Closed Projects tables, with a cancelled project row showing "↩ 2 returned"]*

### Marking an Item as Ordered

When the **BOM Allocation** summary shows an **Overallocated** status, an **Actions** column appears next to the status badge with a **"Mark as Ordered"** button.

Click **"Mark as Ordered"** to record that you've placed a restock order. The status badge changes from 🔴 **Overallocated** to 🟢 **Ordered** — signalling that the shortage is being addressed.

This flag is stored on the inventory item itself (not per-project), so marking one item as ordered clears the alert for **all projects** that share it. The same "Mark ordered" / "Undo" controls also appear on the **Dashboard shopping list** for overallocated items.

Click **"Undo Ordered"** to revert the status if the order was cancelled or you want to reset the flag.

---

## Project Lifecycle and Inventory Impact

### Cancelling a Project

When you set a project's status to **Canceled**:

1. A confirmation modal appears explaining how many inventory-linked BOM items will be returned to stock
2. Click **"Yes, Cancel Project"** to proceed, or **"Go Back"** to abort
3. All reserved inventory quantities are immediately restored

> 📸 *[Screenshot: Cancel Project confirmation modal showing the project name and the inventory items that will be returned to stock]*

The cancelled project's BOM items will appear in the **Closed Projects** section of each linked inventory item's allocation panel, marked as `↩ returned`.

### Re-opening a Cancelled Project

When you change a Cancelled project back to Planning, In Progress, or On Hold:

1. A confirmation modal warns you that inventory items will be **re-reserved**
2. Click **"Yes, Re-open Project"** to proceed
3. All previously linked BOM items immediately re-allocate their quantities from inventory

> 📸 *[Screenshot: Re-open Project confirmation modal showing the number of items that will be re-reserved]*

> This may trigger overallocated warnings if your stock levels have changed since the project was cancelled.

### Completing a Project

When you mark a project as **Completed**, no inventory changes occur. The items were physically consumed — they're gone. Your `qty_available` was already decremented when the BOM items were added, and that stands.

> If you completed a project but actually had leftover parts, remove those BOM items before completing (or manually adjust your inventory count afterward).

### Deleting a Project

Deleting a project is permanent and cannot be undone.

When you click **Delete** from a project's detail page, a confirmation modal appears. For projects with inventory-linked BOM items, you'll see a checkbox:

**"Return X inventory item(s) to stock"**

- **Check it** if the project is being abandoned and the parts are still in your possession
- **Leave it unchecked** if the parts were already used or consumed

For **Cancelled** projects: no option is shown — inventory was already returned when the project was cancelled. The delete just removes the record.

> 📸 *[Screenshot: Delete Project modal showing the project name, the return-to-stock checkbox, and the Delete/Cancel buttons]*

---

## Common Use Cases

### Building Two Projects That Share Parts

You're building a Voron and a Box Turtle simultaneously, and both need the same NEMA17 motors.

1. Add your motors to inventory: **6× NEMA17 Stepper Motor**
2. Add the Voron project BOM: `NEMA17 Stepper × 5` → linked → inventory shows **1 remaining**
3. Add the Box Turtle BOM: `NEMA17 Stepper × 4` → linked → inventory shows **−3 (overallocated)**
4. The Box Turtle BOM shows a 🔴 **Overallocated** badge for the motor item
5. Go to the inventory item detail → see both projects in the allocation panel → decide to order 3 more motors

### Planning Ahead (Before You Have Stock)

You're planning a Trident build but haven't bought the linear rails yet.

1. Add linear rails to inventory with quantity **0**
2. Add BOM items and link to the rail SKUs → inventory shows **−8** (fully overallocated)
3. The red badge reminds you to order before you start the build

### Tracking What to Buy

On any BOM table, items marked **Needs Purchase** or showing **Overallocated** are the ones you need to action. Use the **status filter chips** at the top of the BOM table to show only those items — click **Needs Purchase** or **Overallocated** to isolate your shopping list without scrolling through the full parts list.

### Multiple Build Sizes

A Voron Trident comes in 250mm, 300mm, and 350mm variants with different quantities. Create a separate project for each size you're building, and enter the quantities specific to your chosen variant. The BOM system doesn't interpret variants — you just enter the right numbers for your build.

---

## Dashboard Shopping List

The **Dashboard** aggregates everything you need to buy into a single shopping list, so you don't have to visit each project or inventory item individually.

### What Appears on the List

Two types of items surface here:

| Reason | Source | Meaning |
|--------|--------|---------|
| **Overallocated** | Inventory item | You have more committed to projects than you have in stock — quantity available is negative |
| **Needs Purchase** | BOM item (unlinked) | A BOM item is flagged for purchase and has no inventory link yet |

### Marking Items as Ordered from the Dashboard

Each row in the shopping list has a **"Mark as Ordered"** button. Click it to record that a restock order has been placed.

- **Overallocated items** — the flag is stored on the **inventory item** itself. Marking it ordered here is the same action as marking it ordered from the inventory detail page. The 🔴 Overallocated badge changes to 🟢 Ordered everywhere it appears.
- **Needs Purchase items** — the flag is stored on the **BOM item**. Clicking "Mark as Ordered" records the order against that specific BOM line.

Click **"Undo"** on any row to reset the ordered flag if the order was cancelled or you want to clear it.

> **Note**: Ordered items remain on the shopping list so you can track what's in-flight. They're distinguished by the 🟢 Ordered status rather than disappearing from the list.

---

- **Enter descriptions exactly as written in the creator's BOM** — this makes cross-referencing the original BOM document easy later
- **Don't link items you've already consumed** for a completed project — the system treats "quantity on hand" as what's physically available right now
- **Overallocation is normal during planning** — it's the system working correctly: telling you what to order before you start
- **Use the Notes field** on BOM items for variant-specific reminders, substitution notes, or links to specific product pages
- **The Wizard is faster for bulk entry** — use it for the initial BOM, then use individual Add for ongoing updates

---

## Related Sections

- **Inventory** — where you manage your parts stock and see the allocation panel
- **Projects** — where BOM items live and are managed
- **Dashboard** — overallocation alerts and project health status appear here
