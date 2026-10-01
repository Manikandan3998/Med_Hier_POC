# Plan: Cascading Relationship Creation

## Problem
Currently, when adding a relationship, the **Level** selector allows any level to be picked, and the **Parent** dropdown shows ALL nodes of the parent type regardless of what was added at previous levels. This lets users build broken hierarchies (e.g., starting at level 3, or selecting a parent at level 2 that doesn't exist as a child at level 1).

## Design

### Current code (lines 255-280 of app.py)
```python
level = st.selectbox('Level', [r['level'] for r in rules], format_func=level_label)
rule = next(r for r in rules if r['level'] == level)
parents = [n['node_id'] for n in db['nodes'] if n['node_type_id'] == rule['parent_node_type']]
children = [n['node_id'] for n in db['nodes'] if n['node_type_id'] == rule['child_node_type']]
```

### New logic

**1. Sequential level unlocking (for Add mode only)**

Determine which levels are "available" based on existing relationships for this hierarchy:
- Level 1 is always available
- Level N (where N > 1) is available only if there is at least one relationship at level N-1

```python
existing_rels = [r for r in db['node_relationships'] if r['hier_id'] == hid and not r['end']]
levels_with_data = {r['level'] for r in existing_rels}

available_levels = []
for r in rules:
    lvl = r['level']
    if lvl == rules[0]['level']:  # first level always available
        available_levels.append(lvl)
    elif prev_lvl in levels_with_data:  # previous level has data
        available_levels.append(lvl)
    else:
        break  # stop at first gap
    prev_lvl = lvl
```

The Level selectbox only shows `available_levels`. If all levels have data, all are available (the "fully-built" case).

**2. Parent filtering by previous level's children**

For level 1: the parent is always node `0` (root) — either auto-select it or show only root.

For level N > 1: instead of showing all nodes of the parent type, show only nodes that appear as `child` in existing relationships at level N-1:

```python
if level == rules[0]['level']:
    # Level 1: parent is always root
    parents = ['0']
else:
    # Parent options = children from previous level's relationships
    prev_level = rules[rules.index(rule) - 1]['level']  # actually use sorted order
    parents = list({r['child'] for r in existing_rels if r['level'] == prev_level})
```

**3. Child dropdown stays unrestricted (by node type)**

No change to child logic — it shows all nodes of the child_node_type defined in the level rule:
```python
children = [n['node_id'] for n in db['nodes'] if n['node_type_id'] == rule['child_node_type']]
```

**4. Modify/End actions**

The sequential level restriction applies only to the **Add** action. For **Modify** and **End**, the user is picking from existing relationships, so the Level selector should show all levels that have existing relationships (no restriction needed — they're editing, not creating).

### Scope of changes

- **File**: `app.py` only (lines ~255-280)
- **No changes** to `core.py`, `relationship_actions.py`, or CSV files
- The filter/display enrichment code above this section is untouched
