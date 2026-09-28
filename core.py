"""CSV repository and hierarchy rules. Single-user local POC."""
from pathlib import Path
from datetime import date
import csv, os, shutil, tempfile

SCHEMAS = {
 'node_types':['node_type_id','node_type_name'],
 'nodes':['node_id','node_type_id','node_name'],
 'hierarchies':['hier_id','hier_desc','active'],
 'level_rules':['hier_id','level','parent_node_type','child_node_type'],
 'node_relationships':['relationship_id','hier_id','level','parent','child','start','end'],
}
KEYS={'node_types':['node_type_id'],'nodes':['node_id'],'hierarchies':['hier_id'],'level_rules':['hier_id','level'],'node_relationships':['relationship_id']}
DATA=Path(__file__).parent/'data'

def load(folder=DATA):
    result={}
    for name, cols in SCHEMAS.items():
        with (Path(folder)/f'{name}.csv').open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            if reader.fieldnames != cols: raise ValueError(f'{name}: expected columns {cols}')
            result[name]=list(reader)
    return result

def write_csv(path, rows, columns):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=columns); w.writeheader(); w.writerows(rows)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def save(db,table,folder=DATA):
    errors=validate(db)
    if errors: raise ValueError('\n'.join(errors[:15]))
    path=Path(folder)/f'{table}.csv'
    if path.exists(): shutil.copy2(path,path.with_suffix('.csv.bak'))
    write_csv(path,db[table],SCHEMAS[table])

def next_id(rows,key): return str(max([int(r[key]) for r in rows]+[0])+1)
def active(r,day): return r['start']<=day and (not r['end'] or day<r['end'])

def validate(db):
    errors=[]
    for name,cols in SCHEMAS.items():
        seen=set()
        for i,r in enumerate(db[name],1):
            if set(r)!=set(cols) or any(v is None for v in r.values()):
                errors.append(f'{name} row {i}: invalid CSV columns'); continue
            key=tuple(r[k] for k in KEYS[name])
            if key in seen: errors.append(f'{name}: duplicate key {key}')
            seen.add(key)
            for c in cols:
                if c!='end' and not r[c].strip(): errors.append(f'{name} row {i}: missing {c}')
                if c.endswith('_id') or c in ('level','parent','child','parent_node_type','child_node_type'):
                    if not r[c].isdigit(): errors.append(f'{name} row {i}: {c} must be a nonnegative integer')
    if errors: return errors
    types={r['node_type_id'] for r in db['node_types']}
    nodes={r['node_id']:r for r in db['nodes']}
    hi={r['hier_id'] for r in db['hierarchies']}
    rules={(r['hier_id'],r['level']):r for r in db['level_rules']}
    if '0' not in nodes or nodes['0']['node_type_id']!='0': errors.append('Root node 0 of type 0 is required')
    for n in nodes.values():
        if n['node_type_id'] not in types: errors.append(f"Node {n['node_id']}: unknown type")
    for h in db['hierarchies']:
        if h['active'] not in ('Y','N'): errors.append('Hierarchy active must be Y or N')
    for h in hi:
        rr=sorted([r for r in rules.values() if r['hier_id']==h],key=lambda r:int(r['level']))
        for i,r in enumerate(rr):
            if int(r['level'])!=i+1: errors.append(f'Hierarchy {h}: levels must be consecutive from 1')
            expected='0' if i==0 else rr[i-1]['child_node_type']
            if r['parent_node_type']!=expected: errors.append(f'Hierarchy {h}: disconnected level rules')
        chain=['0']+[r['child_node_type'] for r in rr]
        if len(chain)!=len(set(chain)): errors.append(f'Hierarchy {h}: a type cannot repeat in the level chain')
    for r in rules.values():
        if r['hier_id'] not in hi or r['parent_node_type'] not in types or r['child_node_type'] not in types: errors.append('Level rule has an unknown reference')
    valid=[]
    for r in db['node_relationships']:
        tag=f"Relationship {r['relationship_id']}"
        try:
            date.fromisoformat(r['start'])
            if r['end']: date.fromisoformat(r['end'])
            if r['end'] and r['end']<=r['start']: raise ValueError()
        except ValueError: errors.append(tag+': invalid date interval'); continue
        rule=rules.get((r['hier_id'],r['level']))
        p=nodes.get(r['parent']); c=nodes.get(r['child'])
        if not rule or not p or not c: errors.append(tag+': missing reference'); continue
        if p['node_type_id']!=rule['parent_node_type'] or c['node_type_id']!=rule['child_node_type']: errors.append(tag+': wrong parent/child type')
        if r['parent']==r['child']: errors.append(tag+': self-link')
        valid.append(r)
    for i,a in enumerate(valid):
        for b in valid[i+1:]:
            if a['hier_id']==b['hier_id'] and a['child']==b['child'] and a['start']<(b['end'] or '9999-12-31') and b['start']<(a['end'] or '9999-12-31'):
                errors.append(f"Child {a['child']}: overlapping parent assignments")
    return list(dict.fromkeys(errors))

def flatten(db,hier_id,day):
    errors=validate(db)
    if errors: raise ValueError('; '.join(errors))
    h=next(h for h in db['hierarchies'] if h['hier_id']==hier_id)
    if h['active']!='Y': raise ValueError('This hierarchy is inactive')
    rules=sorted([r for r in db['level_rules'] if r['hier_id']==hier_id],key=lambda r:int(r['level']))
    if not rules: raise ValueError('Add level rules first')
    nodes={n['node_id']:n for n in db['nodes']}
    types={r['node_type_id']:r['node_type_name'].lower().replace(' ','_') for r in db['node_types']}
    links=[r for r in db['node_relationships'] if r['hier_id']==hier_id and active(r,day)]
    rows=[]; visited=set(); incomplete=[]
    def walk(parent,i,out):
        if i==len(rules): rows.append(out); return
        edges=[r for r in links if r['parent']==parent and r['level']==rules[i]['level']]
        if not edges: incomplete.append(parent); return
        for r in edges:
            visited.add(r['relationship_id']); n=nodes[r['child']]; prefix=types[n['node_type_id']]
            walk(n['node_id'],i+1,{**out,prefix+'_id':n['node_id'],prefix+'_name':n['node_name'],prefix+'_node_type':n['node_type_id']})
    walk('0',0,{'hier_id':hier_id,'as_of_date':day})
    warnings=[f'Incomplete branch ends at {nodes[n]["node_name"]} (ID {n})' for n in incomplete]
    warnings += [f"Unreachable active relationship {r['relationship_id']}" for r in links if r['relationship_id'] not in visited]
    cols=['hier_id','as_of_date']
    for r in rules:
        p=types[r['child_node_type']]; cols += [p+'_id',p+'_name',p+'_node_type']
    return rows,cols,warnings

def move(db,rel_id,new_parent,day):
    r=next(r for r in db['node_relationships'] if r['relationship_id']==rel_id)
    if not active(r,day) or day<=r['start']: raise ValueError('Move date must be inside the interval and later than its start')
    if new_parent==r['parent']: raise ValueError('Select a different parent')
    new={**r,'relationship_id':next_id(db['node_relationships'],'relationship_id'),'parent':new_parent,'start':day}
    r['end']=day; db['node_relationships'].append(new)
