---
name: "node type management"
created: "2026-10-05T13:12:01.127Z"
status: pending
---

# Plan: Node Type Management in the Nodes Tab

## Context

Currently, `node_types` is a read-only table displayed in the Overview tab. There is no UI to add, rename, or delete node types. The data lives in `data/node_types.csv` with columns `[node_type_id, node_type_name]`.

### Key dependencies and constraints

Node types are referenced by:

- **`nodes`** — every node has a `node_type_id`
- **`level_rules`** — `parent_node_type` and `child_node_type` reference node type IDs
- **`node_relationships`** — indirectly, via level rules (relationship validity is checked against rule types)

Special handling:

- **Type `0` (Root)** is a system type: hardcoded as chain start in level rules, excluded from the level-chain multiselect, and must always exist. It must never be renamed or deleted.

### Existing UI pattern in Nodes tab

The Nodes tab (app.py:122-185) uses a three-button pattern (Add / Edit / Delete) with session state tracking `nodes_mode`. A `st.selectbox` picks the node type, and all operations happen below. Root type disables Add and Delete buttons.

### Where node type management goes

Above the node type selectbox at line 122. The flow becomes:

```
Nodes tab
  |-- Node Types section (new - collapsible expander)
  |     |-- Table of node types
  |     |-- Add / Rename / Delete controls
  |
  |-- Nodes section (existing, unchanged)
        |-- Type selectbox
        |-- Add / Edit / Delete nodes
```

Using `st.expander` keeps it out of the way when not needed, since node types change rarely.

## Implementation steps

### Step 1: Add the node types expander UI

At the top of the `elif page=='Nodes':` block (line 122 in app.py), before the existing type selectbox, add:

```python
with st.expander('Manage node types', icon=':material/category:'):
    show(db['node_types'])
    # Add, Rename, Delete controls go here (Steps 2-4)
```

### Step 2: Add new node type

Inside the expander, add a form to create a new type:

```python
with st.form('add_node_type'):
    new_type_name = st.text_input('New node type name')
    if st.form_submit_button('Add node type', icon=':material/add:'):
        if not new_type_name.strip():
            st.error('Name is required.')
        elif any(t['node_type_name'].casefold() == new_type_name.strip().casefold() for t in db['node_types']):
            st.error('This node type name already exists.')
        else:
            d = copy.deepcopy(db)
            d['node_types'].append({
                'node_type_id': next_id(d['node_types'], 'node_type_id'),
                'node_type_name': new_type_name.strip()
            })
            commit(d, 'node_types')
```

The `next_id()` function already works for any table — it finds the max integer ID and increments by 1.

### Step 3: Rename node type

A selectbox (excluding Root) + text input for the new name:

```python
non_root = [t for t in db['node_types'] if t['node_type_id'] != '0']
if non_root:
    with st.form('rename_node_type'):
        rename_id = st.selectbox('Rename type', [t['node_type_id'] for t in non_root],
            format_func=lambda x: next(t['node_type_name'] for t in db['node_types'] if t['node_type_id']==x))
        new_name = st.text_input('New name')
        if st.form_submit_button('Rename', icon=':material/edit:'):
            # validate not empty, not duplicate, then update
```

Root (`0`) is excluded from the rename selectbox since it is a system type.

### Step 4: Delete node type with safety guards

A selectbox (excluding Root) + confirmation. Deletion is blocked if:

1. Any **node** has this `node_type_id`
2. Any **level rule** references this type as `parent_node_type` or `child_node_type`

```python
with st.form('delete_node_type'):
    del_id = st.selectbox('Delete type', ...)
    if st.form_submit_button('Delete node type', icon=':material/delete:'):
        nodes_using = [n for n in db['nodes'] if n['node_type_id'] == del_id]
        rules_using = [r for r in db['level_rules']
            if r['parent_node_type'] == del_id or r['child_node_type'] == del_id]
        if nodes_using:
            st.error(f'Cannot delete: {len(nodes_using)} node(s) use this type. Delete the nodes first.')
        elif rules_using:
            st.error(f'Cannot delete: {len(rules_using)} level rule(s) reference this type. Remove the rules first.')
        else:
            d = copy.deepcopy(db)
            d['node_types'] = [t for t in d['node_types'] if t['node_type_id'] != del_id]
            commit(d, 'node_types')
```

### Step 5: Protect Root type in all operations

The Root type (`node_type_id='0'`) must be excluded from rename and delete selectboxes. This is consistent with the existing pattern where the Nodes tab already disables Add/Delete buttons when Root type is selected.

## Verification

1. **Add type** — create "District", verify it appears in the node type table and in the Nodes selectbox and in the level-chain multiselect on Hierarchies and Rules.
2. **Rename type** — rename "Tower" to "Site", verify the name change propagates to all displays (Nodes tab, level rules display, relationship display). Note: only the name changes, the ID stays the same, so all references remain valid.
3. **Delete unused type** — delete a type that has no nodes and no rules. Verify it disappears from all selectboxes.
4. **Delete used type (blocked)** — try to delete "Area" (has nodes + rules). Verify the error message appears.
5. **Root protection** — verify Root type does not appear in rename or delete selectboxes.
6. **Validation tab** — confirm "Structural validation passed" after all operations.

## Critical files

- app.py — Nodes tab section (line 122+), where the expander and forms will be added
- core.py — `validate()` and `next_id()` functions (used as-is, no changes needed)
- data/node\_types.csv — the backing data file
