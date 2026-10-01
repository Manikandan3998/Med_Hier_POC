# Plan: Nodes Tab — Inline Editable Table (Add / Edit / Delete)

## Context

The current Nodes page (`app.py` lines 116-136) has three separate sections:
1. A read-only `st.dataframe` showing nodes filtered by type
2. An "Add node" form at the bottom
3. A "Rename node" selectbox + form further below

The client wants a single editable table where users can:
- **Edit** a node name by clicking its cell
- **Add** a new node via a `+` button at the bottom of the table
- **Delete** a node by selecting a row and pressing Delete

Streamlit's `st.data_editor` supports all three via:
- `num_rows="dynamic"` — shows `+` button for new rows and allows row deletion
- `disabled=[columns]` — marks columns as read-only
- `key="..."` — stores edit state in `st.session_state` with `edited_rows`, `added_rows`, `deleted_rows`

### Key design decisions

- **Only `node_name` is editable.** `node_id` is shown read-only for reference. `node_type_id` is hidden (implicit from the dropdown filter).
- **Delete is allowed** but blocked at save time if the node is referenced in any relationship (parent or child). A clear error message tells the user which nodes cannot be deleted.
- **Root type (0) is excluded** from the Node type dropdown entirely.
- **A "Save changes" button** below the table commits all edits, additions, and deletions in one batch.

### UI mockup

```
Node type: [Area v]

| node_id (read-only) | node_name (editable)  |
|----------------------|-----------------------|
| 10001                | EMEA                  |
| 10002                | Greater China         |
| 10003                | LatAm                 |
| 10004                | Asia                  |
| 10005                | Americas              |
| + (add new row)      |                       |

[Save changes]
```

Users can:
- Click a `node_name` cell to edit it inline
- Click the `+` row at the bottom to add a new node
- Select a row checkbox and press Delete to mark it for removal
- Click "Save changes" to commit all pending operations

## Implementation steps

### Step 1 — Exclude Root from Node type dropdown

In `app.py` line 117, add `if t['node_type_id'] != '0'` to the filter:

```python
typ = st.selectbox(
    'Node type',
    [t['node_type_id'] for t in db['node_types'] if t['node_type_id'] != '0'],
    format_func=lambda x: next(t['node_type_name'] for t in db['node_types'] if t['node_type_id'] == x)
)
```

### Step 2 — Replace the read-only table + forms with st.data_editor

Replace lines 118-136 (the `show()` call + add form + rename form) with the data editor:

```python
filtered = [n for n in db['nodes'] if n['node_type_id'] == typ]
df = pd.DataFrame(filtered, columns=['node_id', 'node_name'])

edited = st.data_editor(
    df,
    column_config={
        'node_id': st.column_config.TextColumn('Node ID', disabled=True),
        'node_name': st.column_config.TextColumn('Node Name'),
    },
    disabled=['node_id'],
    num_rows='dynamic',
    use_container_width=True,
    hide_index=True,
    key='nodes_editor',
)
```

- `node_type_id` is excluded from the DataFrame — it's implicit from the dropdown.
- `node_id` is disabled (read-only) — shown for reference.
- `num_rows='dynamic'` enables both the `+` add-row button and row deletion.

### Step 3 — Save button with add/edit/delete logic

```python
if st.button('Save changes', icon=':material/save:'):
    d = copy.deepcopy(db)
    errors = []
    original_ids = {r['node_id'] for r in filtered}

    # Detect deletions (original IDs not in the edited DataFrame)
    surviving_ids = set()
    for _, row in edited.iterrows():
        nid = str(row['node_id']).strip() if pd.notna(row['node_id']) and str(row['node_id']).strip() else ''
        if nid:
            surviving_ids.add(nid)
    deleted_ids = original_ids - surviving_ids

    if deleted_ids:
        in_use = {r['parent'] for r in db['node_relationships']} | {r['child'] for r in db['node_relationships']}
        blocked = deleted_ids & in_use
        if blocked:
            names = ', '.join(
                next(n['node_name'] for n in db['nodes'] if n['node_id'] == nid) for nid in blocked
            )
            errors.append(f"Cannot delete nodes used in relationships: {names}")
        else:
            d['nodes'] = [n for n in d['nodes'] if n['node_id'] not in deleted_ids]

    # Process edits and additions
    seen_names = set()
    for _, row in edited.iterrows():
        name = str(row['node_name']).strip() if pd.notna(row['node_name']) else ''
        nid = str(row['node_id']).strip() if pd.notna(row['node_id']) and str(row['node_id']).strip() else ''

        if not name:
            errors.append('Node name cannot be empty.')
            continue

        if name.casefold() in seen_names:
            errors.append(f'Duplicate name in editor: {name}')
            continue
        seen_names.add(name.casefold())

        # Check duplicate against other types too
        same_name = [n for n in d['nodes'] if n['node_type_id'] == typ
                     and n['node_name'].casefold() == name.casefold() and n['node_id'] != nid]
        if same_name:
            errors.append(f'Duplicate name: {name}')
            continue

        if nid and nid in original_ids:
            # Rename existing node
            node = next(n for n in d['nodes'] if n['node_id'] == nid)
            node['node_name'] = name
        elif not nid:
            # New node
            new_id = next_id(d['nodes'], 'node_id')
            d['nodes'].append({'node_id': new_id, 'node_type_id': typ, 'node_name': name})

    if errors:
        for e in errors:
            st.error(e)
    else:
        commit(d, 'nodes')
```

### Step 4 — Remove old forms

Delete the entire old add-node form (lines 119-126) and rename selectbox + form (lines 127-136). They are fully replaced by the data_editor + save button.

## Verification

1. Run `streamlit run app.py`
2. Navigate to **Nodes** tab
3. Verify Root type is not in the dropdown
4. Select "Area" — table shows with editable `node_name` and read-only `node_id`
5. **Edit**: Click a node name, change it, click "Save changes" — verify rename persists
6. **Add**: Click `+`, type a new name, click "Save changes" — verify new node appears with auto-generated ID
7. **Delete**: Select a row checkbox, press Delete, click "Save changes" — verify node is removed
8. **Delete blocked**: Try to delete a node used in relationships — verify error message shows the node name
9. **Validation**: Try empty name, duplicate name — verify error messages

## Critical files

- [app.py](app.py) — Nodes page section (lines 116-136), sole file to modify
- [core.py](core.py) — `next_id()`, `save()`, `validate()` used by save logic (no changes needed)
- [data/nodes.csv](data/nodes.csv) — backing data (modified indirectly via `commit()`)
