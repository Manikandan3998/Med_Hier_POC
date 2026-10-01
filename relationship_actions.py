"""Validated relationship operations; inputs are never mutated."""
from copy import deepcopy
from datetime import datetime
from core import validate, next_id


def checked_ts(value):
    try:
        parsed=datetime.fromisoformat(value)
    except (ValueError,TypeError):
        raise ValueError('Use a valid timestamp (YYYY-MM-DDTHH:MM:SS)') from None
    return parsed


def checked(db):
    for r in db['node_relationships']:
        checked_ts(r['start'])
        if r['end']: checked_ts(r['end'])
    errors=validate(db)
    if errors: raise ValueError('\n'.join(errors[:15]))
    return db


def require_active(db,hid):
    h=next((h for h in db['hierarchies'] if h['hier_id']==hid),None)
    if h is None or h['active']!='Y':
        raise ValueError('Select an active hierarchy')


def existing_open(db,rid,day):
    checked_ts(day)
    r=next((r for r in db['node_relationships'] if r['relationship_id']==rid),None)
    if r is None: raise ValueError('Relationship does not exist')
    require_active(db,r['hier_id'])
    if r['end']: raise ValueError('This relationship already has an end date; history cannot be overwritten here')
    if checked_ts(day)<=checked_ts(r['start']):
        raise ValueError('Effective timestamp must be later than the existing start timestamp.')
    return r


def add_relationship(db,hid,level,parent,child,start):
    checked_ts(start); require_active(db,hid)
    d=deepcopy(db)
    d['node_relationships'].append(dict(relationship_id=next_id(d['node_relationships'],'relationship_id'),hier_id=hid,level=level,parent=parent,child=child,start=start,end=''))
    return checked(d)


def modify_relationship(db,rid,parent,day):
    d=deepcopy(db); r=existing_open(d,rid,day)
    if parent==r['parent']: raise ValueError('Select a different parent')
    replacement={**r,'relationship_id':next_id(d['node_relationships'],'relationship_id'),'parent':parent,'start':day,'end':''}
    r['end']=day
    d['node_relationships'].append(replacement)
    return checked(d)


def end_relationship(db,rid,day):
    d=deepcopy(db); r=existing_open(d,rid,day); r['end']=day
    return checked(d)
