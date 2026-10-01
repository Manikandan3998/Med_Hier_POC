# Plan: Client Feedback Changes

## Summary
Implement all client feedback items from the meeting transcription and follow-up email, applied to `app.py` and `core.py`.

## Change 1: Display Names Instead of IDs Everywhere

**Files:** `app.py`

Currently, several tables display raw IDs (node_type_id, parent, child, hier_id). The client specifically called out the relationships table at ~17:00 in the meeting.

Changes needed:
- **Relationships table** (line 166): Replace raw `parent`/`child` IDs with node names, `hier_id` with hierarchy description, and `level` with level + node type name.
- **Level rules table** (line 152): Replace `parent_node_type`/`child_node_type` IDs with node type names, `hier_id` with hierarchy description.
- **Nodes table** (line 118): Replace `node_type_id` with node type name.
- **Overview tables** (line 113): When showing any table, enrich ID columns with names.

Approach: Create a helper function `enrich_df(df, table_name, db)` that replaces ID columns with name columns for display purposes. The underlying data stays as IDs — only the display DataFrame gets names.

## Change 2: Root Node — Remove Creation Option

**Files:** `app.py`

Currently line 122 shows an error if you try to add a root node. Instead:
- Filter node_type_id `'0'` (Root) out of the Node type dropdown on the Nodes page entirely.
- This means users never even see Root as an option to add nodes to.
- The root node is fixed and immutable.

## Change 3: Add Node Type Management

**Files:** `app.py`, `core.py`

Currently there's no UI to create/rename/delete node types. Add a section (either on the Nodes page or as a new sidebar entry):
- **Create node type**: Form with name input, auto-generates ID.
- **Rename node type**: Select existing type (excluding Root), edit name.
- **Delete node type**: Only allow if no nodes of that type exist and no level rules reference it.

I'll add this as a new expandable section on the Nodes page or a separate "Node Types" area within the Nodes page since they're closely related.

## Change 4: Level + Node Type Name in Level Dropdown

**Files:** `app.py` (Relationships page, ~line 170)

Change the Level selectbox `format_func` to show `"Level {level} — {child_node_type_name}"` instead of just the level number. This uses the `child_node_type` from the level rule to look up the node type name.

## Change 5: Filter Parent Dropdown by Hierarchy Context

**Files:** `app.py` (Relationships page, ~line 172)

Currently `parents` shows ALL nodes of the parent node type. For level > 1, we should only show nodes that are already assigned as **children** in existing active relationships at the previous level for the same hierarchy.

Logic:
- Level 1: parent is always root (node 0) — no change needed.
- Level > 1: get all active relationships at level-1 for this hierarchy, collect their `child` IDs — those are the valid parents.

## Change 6: Bulk Upload for Nodes and Relationships

**Files:** `app.py`, `core.py`

Add file upload widgets (CSV format) on the Nodes page and Relationships page:
- **Node upload**: CSV with columns `node_type_name, node_name`. Look up node_type_id from name, auto-generate node_id, validate no duplicates, then bulk insert.
- **Relationship upload**: CSV with columns like `hierarchy, level, parent_name, child_name, start_date`. Resolve names to IDs, validate, then bulk insert.
- Show a preview table before committing.
- Run full validation before saving.

This is lower priority per client and more complex — will implement last.
