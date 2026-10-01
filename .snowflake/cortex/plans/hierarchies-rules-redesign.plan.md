# Plan: Hierarchies and Rules Tab Redesign

## Context

### Current State (lines 183-207 of app.py)
The Hierarchies and Rules tab currently has a cluttered layout with multiple stacked forms:
1. A raw hierarchy table showing `hier_id`, `hier_desc`, `active` (IDs visible)
2. A "Create hierarchy" form (always visible)
3. A hierarchy selector dropdown
4. An "Edit hierarchy" form (name + active checkbox + Save button)
5. A level rules table showing raw IDs (`hier_id`, `level`, `parent_node_type`, `child_node_type`)
6. A multiselect for ordered levels + Save button

### Client Feedback (from transcript)
- **"Wherever IDs are displayed, please display the name rather than the ID"** -- the level rules table shows raw node type IDs (0, 11, 12...) instead of names (Root, Area, Region...)
- The hierarchy table shows `hier_id` which is an internal ID

### Design Decision
Apply the same Add/Edit/Delete three-button pattern from the Nodes tab for a consistent UX across the app. This replaces the current always-visible stacked forms.

## Current vs Proposed Layout

```
CURRENT LAYOUT                          PROPOSED LAYOUT
------------------                      ------------------
[Hierarchy table (raw IDs)]             [Add] [Edit] [Delete]   <-- mode buttons
[New hierarchy name ___]                [Hierarchy table with display names]
[Create hierarchy]
                                        --- if Add mode ---
[Hierarchy: v dropdown]                 [New hierarchy name ___]
[Hierarchy description ___]             [Done] [Cancel]
[x] Active
[Save hierarchy]                        --- if Edit mode ---
                                        [Hierarchy: v dropdown]
[Level rules table (raw IDs)]           [Hierarchy description ___]
Choose types in order...                [x] Active
[Ordered levels: multiselect]           [Level rules table with names]
[Save level rules]                      [Ordered levels: multiselect]
                                        [Finish] [Cancel]

                                        --- if Delete mode ---
                                        [Hierarchy table with row selection]
                                        [Confirm] [Cancel]
```

## Implementation Steps

### Task 1: Add/Edit/Delete Mode Buttons for Hierarchies

Replace the current code block (lines 183-207) with the three-button pattern. Reuse the same CSS marker approach that works on the Nodes tab (hidden `span#hier-btn-row` in the 4th column).

```python
elif page=='Hierarchies & rules':
    if 'hier_mode' not in st.session_state: st.session_state['hier_mode']=None
    # CSS reuses same pattern as Nodes tab
    st.markdown("""<style>
div[data-testid="stHorizontalBlock"]:has(span#hier-btn-row) {flex-wrap:nowrap!important;gap:.5rem!important;justify-content:flex-start!important;}
div[data-testid="stHorizontalBlock"]:has(span#hier-btn-row) > div[data-testid="stColumn"] {flex:0 0 auto!important;width:auto!important;min-width:0!important;}
div[data-testid="stElementContainer"]:has(span#hier-btn-row) {display:none!important;}
</style>""",unsafe_allow_html=True)
    btn_row=st.columns([1,1,1,5],gap='small')
    btn_row[3].markdown('<span id="hier-btn-row"></span>',unsafe_allow_html=True)
    if btn_row[0].button('Add',icon=':material/add_circle:',key='hier_add'): st.session_state['hier_mode']='add'; st.rerun()
    if btn_row[1].button('Edit',icon=':material/edit:',key='hier_edit'): st.session_state['hier_mode']='edit'; st.rerun()
    if btn_row[2].button('Delete',icon=':material/delete:',key='hier_del'): st.session_state['hier_mode']='delete'; st.rerun()
    mode=st.session_state['hier_mode']
```

### Task 2: Display Names Instead of IDs

**Hierarchy table**: Show `hier_desc` and `active` columns. Drop `hier_id` from the display (internal ID not useful to users). Or rename it to "Hierarchy ID" if the user wants it visible.

**Level rules table**: Replace `parent_node_type` / `child_node_type` IDs with node type names using a lookup:
```python
type_names={t['node_type_id']:t['node_type_name'] for t in db['node_types']}
rules_df=pd.DataFrame(rules_for_hier)
rules_df['parent_node_type']=rules_df['parent_node_type'].map(type_names)
rules_df['child_node_type']=rules_df['child_node_type'].map(type_names)
```

### Task 3: Add Mode -- Create New Hierarchy

When mode is `'add'`:
- Show the read-only hierarchy table (so user can see existing hierarchies)
- Below it, show a form with a text input for hierarchy name
- Done/Cancel buttons (same pattern as Nodes Add)
- On Done: validate name not empty, create hierarchy with auto-generated `hier_id` and `active='Y'`

### Task 4: Edit Mode -- Edit Hierarchy + Level Rules

When mode is `'edit'`:
- Show a hierarchy dropdown selector
- Text input for hierarchy description (pre-filled)
- Active checkbox (pre-filled)
- Level rules table (with names, read-only display)
- Multiselect for ordered levels (pre-filled with current chain)
- Caption: "Rule changes are blocked once this hierarchy has relationships."
- Finish/Cancel buttons
- On Finish: save both hierarchy metadata and level rules together

### Task 5: Delete Mode -- Delete Hierarchy

When mode is `'delete'`:
- Show hierarchy table with `on_select='rerun'` and `selection_mode='multi-row'`
- Confirm/Cancel buttons
- On Confirm: check if selected hierarchy has any relationships in `node_relationships`. If yes, block with error. If no, delete the hierarchy and its associated level rules.

### Task 6: Verify All Modes and Edge Cases

- Add: empty name validation, successful creation
- Edit: name change, active toggle, level rule reordering, block rule changes when relationships exist
- Delete: block deletion when relationships exist, successful deletion cleans up level rules too
- Button sizing: verify buttons don't shrink on sidebar expand (same CSS pattern)

## Critical Files

- [app.py](app.py) -- Lines 183-207, the entire Hierarchies and Rules section to rewrite
- [core.py](core.py) -- Reference for `next_id()`, `save()`, data structure (read-only)
- [data/hierarchies.csv](data/hierarchies.csv) -- Hierarchy data structure: hier_id, hier_desc, active
- [data/level_rules.csv](data/level_rules.csv) -- Level rules structure: hier_id, level, parent_node_type, child_node_type

## Verification

1. Navigate to Hierarchies and Rules tab -- should see three buttons (Add, Edit, Delete) aligned, and a read-only hierarchy table with names
2. Click Add -- form appears below table, create a hierarchy, verify it appears in table
3. Click Edit -- select a hierarchy, modify name/active/levels, save, verify changes
4. Click Edit on a hierarchy with relationships -- level multiselect should show warning about being blocked
5. Click Delete -- select a hierarchy without relationships, confirm, verify it and its level rules are removed
6. Click Delete on a hierarchy with relationships -- should show error blocking deletion
7. Expand/collapse sidebar -- buttons should not shrink
