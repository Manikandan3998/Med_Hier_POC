# Plan: Nodes Tab — Three Mode Buttons (Add / Edit / Delete)

## Context

The current `st.data_editor` approach has several issues flagged by the user:
1. Table columns were changed (missing `node_type_id`)
2. Sorting arrows gone (data_editor with `num_rows="dynamic"` disables sorting)
3. Unwanted three-dot menu (Autosize, Pin, Hide columns)
4. Empty rows get created when Add is clicked without entering a name
5. No visible delete button
6. User wants three explicit mode buttons instead of the always-editable table

## New design

The Nodes page will have three states controlled by `st.session_state['nodes_mode']`:

```
Node type: [Area v]

[Add]  [Edit]  [Delete]       <-- three buttons at the top

+-----------+--------------+-----------+
| node_id   | node_type_id | node_name |    <-- read-only, sortable st.dataframe
+-----------+--------------+-----------+
| 10001     | 11           | EMEA      |
| 10002     | 11           | G. China  |
| ...       | ...          | ...       |
+-----------+--------------+-----------+
```

### Default state (no mode)
- Read-only `st.dataframe` with all 3 columns, sortable, no three-dot menu
- Three buttons: Add, Edit, Delete

### Add mode
- A text input for the new node name appears below the table
- "Done" button saves the new node (auto-generates `node_id`, uses the selected `node_type_id`)
- "Cancel" button exits add mode
- Blank names are rejected; duplicates are caught

### Edit mode
- A `st.data_editor` appears showing `node_name` as editable, `node_id` as read-only
- `num_rows="fixed"` (no add/delete, so sorting works and no three-dot menu issues)
- "Finish" button compares edits and saves changes
- "Cancel" button exits edit mode

### Delete mode
- Table shows with checkboxes via `st.dataframe` with `on_select_rows`
- User selects rows to delete
- "Confirm Delete" button removes selected nodes (blocked if in use by relationships)
- "Cancel" button exits delete mode

## Implementation (lines 117-162 of app.py)

Replace the entire current Nodes section with:

```python
elif page=='Nodes':
    typ=st.selectbox('Node type',
        [t['node_type_id'] for t in db['node_types'] if t['node_type_id']!='0'],
        format_func=lambda x:next(t['node_type_name'] for t in db['node_types']
                                  if t['node_type_id']==x))
    filtered=[n for n in db['nodes'] if n['node_type_id']==typ]
    df=pd.DataFrame(filtered,columns=['node_id','node_type_id','node_name'])

    if 'nodes_mode' not in st.session_state:
        st.session_state['nodes_mode']=None

    # --- Mode buttons ---
    bcols=st.columns([1,1,1,5])
    if bcols[0].button('Add',icon=':material/add_circle:',
                        use_container_width=True):
        st.session_state['nodes_mode']='add'
    if bcols[1].button('Edit',icon=':material/edit:',
                        use_container_width=True):
        st.session_state['nodes_mode']='edit'
    if bcols[2].button('Delete',icon=':material/delete:',
                        use_container_width=True):
        st.session_state['nodes_mode']='delete'

    mode=st.session_state['nodes_mode']

    # --- Default / Add mode: read-only sortable table ---
    if mode is None or mode=='add':
        st.dataframe(df, use_container_width=True, hide_index=True)
        if mode=='add':
            with st.form('add_node'):
                name=st.text_input('New node name')
                c1,c2,_=st.columns([1,1,6])
                done=c1.form_submit_button('Done',icon=':material/check:')
                cancel=c2.form_submit_button('Cancel',icon=':material/close:')
            if cancel:
                st.session_state['nodes_mode']=None; st.rerun()
            if done:
                if not name.strip():
                    st.error('Enter a name.')
                elif any(n['node_type_id']==typ
                         and n['node_name'].casefold()==name.strip().casefold()
                         for n in db['nodes']):
                    st.error('This name already exists for the selected type.')
                else:
                    d=copy.deepcopy(db)
                    d['nodes'].append({
                        'node_id': next_id(d['nodes'],'node_id'),
                        'node_type_id': typ,
                        'node_name': name.strip()})
                    commit(d,'nodes')

    # --- Edit mode: editable data_editor, fixed rows ---
    elif mode=='edit':
        edit_df=df[['node_id','node_name']].copy()
        edited=st.data_editor(
            edit_df,
            column_config={
                'node_id': st.column_config.TextColumn('Node ID',disabled=True),
                'node_name': st.column_config.TextColumn('Node Name'),
            },
            disabled=['node_id'],
            num_rows='fixed',
            use_container_width=True,
            hide_index=True,
            key='nodes_edit_editor',
        )
        c1,c2,_=st.columns([1,1,6])
        if c1.button('Finish',icon=':material/check:'):
            d=copy.deepcopy(db); errors=[]
            seen_names=set()
            for _,row in edited.iterrows():
                name=str(row['node_name']).strip()
                                    if pd.notna(row['node_name']) else ''
                nid=str(row['node_id'])
                if not name:
                    errors.append('Node name cannot be empty.'); continue
                if name.casefold() in seen_names:
                    errors.append(f'Duplicate name: {name}'); continue
                seen_names.add(name.casefold())
                next(n for n in d['nodes']
                     if n['node_id']==nid)['node_name']=name
            if errors:
                for e in errors: st.error(e)
            else:
                st.session_state['nodes_mode']=None; commit(d,'nodes')
        if c2.button('Cancel',icon=':material/close:'):
            st.session_state['nodes_mode']=None; st.rerun()

    # --- Delete mode: table with row selection ---
    elif mode=='delete':
        event=st.dataframe(
            df, use_container_width=True, hide_index=True,
            on_select='rerun', selection_mode='multi-row',
            key='nodes_delete_df',
        )
        selected_indices=event.selection.rows if event.selection else []
        c1,c2,_=st.columns([1,1,6])
        if c1.button('Confirm Delete',icon=':material/delete:'):
            if not selected_indices:
                st.error('Select at least one row to delete.')
            else:
                ids_to_delete={
                    filtered[i]['node_id'] for i in selected_indices}
                in_use=({r['parent'] for r in db['node_relationships']}
                        | {r['child'] for r in db['node_relationships']})
                blocked=ids_to_delete & in_use
                if blocked:
                    names=', '.join(
                        next(n['node_name'] for n in db['nodes']
                             if n['node_id']==nid) for nid in blocked)
                    st.error(
                        f'Cannot delete nodes in relationships: {names}')
                else:
                    d=copy.deepcopy(db)
                    d['nodes']=[n for n in d['nodes']
                                if n['node_id'] not in ids_to_delete]
                    st.session_state['nodes_mode']=None
                    commit(d,'nodes')
        if c2.button('Cancel',icon=':material/close:',key='del_cancel'):
            st.session_state['nodes_mode']=None; st.rerun()
```

### Key points addressing each feedback item

1. **Table structure preserved**: All 3 columns (`node_id`, `node_type_id`, `node_name`) shown in the read-only table.
2. **Sorting restored**: Default mode uses `st.dataframe` which supports column sorting. Edit mode uses `num_rows="fixed"` which also supports sorting.
3. **Three-dot menu removed**: `st.dataframe` does not show it. `st.data_editor` with `num_rows="fixed"` minimizes toolbar clutter.
4. **Add auto-generates IDs**: Only `node_name` input shown. `node_id` and `node_type_id` are auto-assigned.
5. **No blank records**: Add requires a non-empty name via explicit validation before committing.
6. **Delete button visible**: Explicit "Delete" mode button + "Confirm Delete" action button.
7. **Three-button mode pattern**: Add, Edit, Delete buttons at top. Each activates its own mode with Done/Finish/Confirm + Cancel to exit.

## Verification

1. **Default view**: Table is read-only, sortable, shows all 3 columns
2. **Add mode**: Click Add -> type name -> Done saves, Cancel exits. Empty name rejected.
3. **Edit mode**: Click Edit -> table becomes editable (name only) -> Finish saves, Cancel exits. Empty/duplicate names caught.
4. **Delete mode**: Click Delete -> select rows via checkboxes -> Confirm Delete removes them. Nodes in relationships blocked.
5. **Root hidden**: Node type dropdown excludes Root (type 0).

## Critical files

- [app.py](app.py) lines 117-162 — sole file to modify (Nodes section)
- [core.py](core.py) — `next_id()`, `save()`, `validate()` referenced (no changes)
