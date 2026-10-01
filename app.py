from datetime import date, datetime, time
import copy, io, csv, json
import importlib
import pandas as pd
import streamlit as st
import relationship_actions as _ra; importlib.reload(_ra)
from relationship_actions import add_relationship, modify_relationship, end_relationship
import core as _core; importlib.reload(_core)
from core import load, save, validate, flatten, move, next_id, active, write_csv, DATA

from pathlib import Path

# Force light theme (no auto dark mode): applied now, and saved for next launch
LIGHT={'theme.base':'light','theme.primaryColor':'#1010EB','theme.backgroundColor':'#FFFFFF','theme.secondaryBackgroundColor':'#F3F4FA','theme.textColor':'#170F4F'}
for _k,_v in LIGHT.items():
    try: st._config.set_option(_k,_v)
    except Exception: pass
try:
    _cfg=Path(__file__).parent/'.streamlit'/'config.toml'
    if not _cfg.exists():
        _cfg.parent.mkdir(exist_ok=True)
        _cfg.write_text('[theme]\nbase = "light"\nprimaryColor = "#1010EB"\nbackgroundColor = "#FFFFFF"\nsecondaryBackgroundColor = "#F3F4FA"\ntextColor = "#170F4F"\n')
except OSError: pass

st.set_page_config(page_title='Hierarchy Studio',page_icon='🌐',layout='wide')

# ---------- Medtronic-style light theme (single-file, no night mode) ----------
THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');
:root { --navy:#170F4F; --blue:#1010EB; --soft:#F3F4FA; color-scheme: light only; }
html, body, .stApp, [class*="css"] { font-family:'Montserrat','Segoe UI',Arial,sans-serif; color:var(--navy); background:#fff; }
.stApp p, .stApp label, .stApp span, .stApp li { color:var(--navy); }

header[data-testid="stHeader"] { background:var(--navy); height:3.4rem; }
header[data-testid="stHeader"] * { color:#fff !important; }
.block-container { padding-top:4.5rem; max-width:1300px; }

h1 { color:var(--navy); font-weight:700; letter-spacing:-.5px; font-size:2.6rem; }
h2, h3 { color:var(--navy); font-weight:600; }
[data-testid="stCaptionContainer"] { color:#5b5a80; }

/* Sidebar: navy panel, bigger nav items and icons */
[data-testid="stSidebar"] { background:var(--navy); }
[data-testid="stSidebar"] * { color:#fff !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color:#b9b8dc !important; }
[data-testid="stSidebar"] .stRadio label {
  font-size:1.1rem; font-weight:600; padding:.6rem .9rem; border-radius:999px;
  transition:background .15s; width:100%;
}
[data-testid="stSidebar"] .stRadio label:hover { background:rgba(255,255,255,.12); }
[data-testid="stSidebar"] .stRadio label:has(input:checked) { background:var(--blue); }
[data-testid="stSidebar"] .stRadio label > div:first-child { display:none; }
[data-testid="stSidebar"] .stRadio label p { font-size:1.1rem; }

/* Pill buttons with larger icons */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  border:1.5px solid var(--blue); color:var(--blue); background:#fff;
  border-radius:999px; padding:.55rem 1.6rem; font-weight:600; transition:all .15s;
}
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
  background:var(--blue); color:#fff; border-color:var(--blue);
}
.stButton > button:hover *, .stDownloadButton > button:hover *, [data-testid="stFormSubmitButton"] > button:hover * { color:#fff; }
.stButton button [data-testid="stIconMaterial"], .stDownloadButton button [data-testid="stIconMaterial"],
[data-testid="stFormSubmitButton"] button [data-testid="stIconMaterial"] { font-size:1.6rem; }

[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] { border-radius:12px !important; }
/* Light inputs, selects, date pickers and dropdown menus even if the browser is in dark mode */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div, [data-baseweb="textarea"], [data-baseweb="textarea"] textarea { background:#F3F4FA !important; border:1px solid #d9daf0 !important; }
.stApp input, .stApp textarea, [data-baseweb="select"] *, [data-testid="stDateInput"] * { color:#170F4F !important; -webkit-text-fill-color:#170F4F !important; }
[data-baseweb="popover"] > div, [data-baseweb="popover"] ul, [data-baseweb="menu"], [data-baseweb="calendar"] { background:#fff !important; color:#170F4F !important; }
[data-baseweb="popover"] li:hover { background:#F3F4FA !important; }
[data-baseweb="tag"] { background:#1010EB !important; } [data-baseweb="tag"], [data-baseweb="tag"] *, [data-baseweb="tag"] span, [data-baseweb="tag"] svg { color:#fff !important; -webkit-text-fill-color:#fff !important; fill:#fff !important; }
span[data-tag] { background:#1010EB !important; } span[data-tag], span[data-tag] * { color:#fff !important; -webkit-text-fill-color:#fff !important; fill:#fff !important; }
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within { border-color:var(--blue) !important; }

[data-testid="stMetric"] { background:var(--soft); border-left:5px solid var(--blue); border-radius:14px; padding:1rem 1.3rem; }
[data-testid="stMetricValue"] { color:var(--blue); font-weight:700; }
[data-testid="stForm"] { background:var(--soft); border:none; border-radius:16px; padding:1.4rem; }
[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; border:1px solid #e1e2f0; }
[data-testid="stAlert"] { border-radius:12px; }
</style>
"""
st.logo('logo.png', size='large')

st.markdown(THEME_CSS, unsafe_allow_html=True)

st.title('Hierarchy App')
st.caption('RST hierarchy management')

try: db=load()
except Exception as e: st.error(f'Cannot load CSV files: {e}'); st.stop()
if 'notice' in st.session_state: st.success(st.session_state.pop('notice'))

PAGES={'Overview':'','Nodes':'','Hierarchies & rules':'','Relationships':'','Hierarchy explorer':'','Validation':'','Reporting output':''}
page=st.sidebar.radio('Workspace',list(PAGES),format_func=lambda p:f'{PAGES[p]}  {p}')


def commit(candidate,table):
    try: save(candidate,table)
    except (ValueError,OSError) as e: st.error(str(e)); return
    st.session_state['notice']='Saved successfully.'; st.rerun()

def show(rows): st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
def label(n):
    r=next(r for r in db['nodes'] if r['node_id']==n)
    return f"{r['node_name']} - ID {n}"
def hselect(key):
    return st.selectbox('Hierarchy',[h['hier_id'] for h in db['hierarchies']],format_func=lambda x:next(h['hier_desc'] for h in db['hierarchies'] if h['hier_id']==x),key=key)

if page=='Overview':
    cols=st.columns(3)
    for col,title,table in zip(cols,['Nodes','Hierarchies','Relationships'],['nodes','hierarchies','node_relationships']): col.metric(title,len(db[table]))
    
    st.subheader('Tables')
    table=st.selectbox('Table',list(db)); show(db[table])
    st.download_button('Download table',(DATA/f'{table}.csv').read_bytes(),f'{table}.csv','text/csv',icon=':material/download:')

elif page=='Nodes':
    typ=st.selectbox('Node type',[t['node_type_id'] for t in db['node_types']],format_func=lambda x:next(t['node_type_name'] for t in db['node_types'] if t['node_type_id']==x))
    is_root=typ=='0'
    filtered=[n for n in db['nodes'] if n['node_type_id']==typ]
    df=pd.DataFrame(filtered,columns=['node_id','node_type_id','node_name'])
    if 'nodes_mode' not in st.session_state: st.session_state['nodes_mode']=None
    if is_root and st.session_state['nodes_mode'] in ('add','delete'): st.session_state['nodes_mode']=None
    st.markdown("""<style>
div[data-testid="stHorizontalBlock"]:has(span#node-btn-row) {flex-wrap:nowrap!important;gap:.5rem!important;justify-content:flex-start!important;}
div[data-testid="stHorizontalBlock"]:has(span#node-btn-row) > div[data-testid="stColumn"] {flex:0 0 auto!important;width:auto!important;min-width:0!important;}
div[data-testid="stElementContainer"]:has(span#node-btn-row) {display:none!important;}
</style>""",unsafe_allow_html=True)
    btn_row=st.columns([1,1,1,5],gap='small')
    btn_row[3].markdown('<span id="node-btn-row"></span>',unsafe_allow_html=True)
    if btn_row[0].button('Add',icon=':material/add_circle:',key='node_add',disabled=is_root): st.session_state['nodes_mode']='add'; st.rerun()
    if btn_row[1].button('Edit',icon=':material/edit:',key='node_edit'): st.session_state['nodes_mode']='edit'; st.rerun()
    if btn_row[2].button('Delete',icon=':material/delete:',key='node_del',disabled=is_root): st.session_state['nodes_mode']='delete'; st.rerun()
    mode=st.session_state['nodes_mode']
    if mode is None or mode=='add':
        st.dataframe(df,use_container_width=True,hide_index=True)
        if mode=='add':
            with st.form('add_node'):
                name=st.text_input('New node name')
                c1,c2,_=st.columns([2,2,4])
                done=c1.form_submit_button('Done',icon=':material/check:')
                cancel=c2.form_submit_button('Cancel',icon=':material/close:')
            if cancel: st.session_state['nodes_mode']=None; st.rerun()
            if done:
                if not name.strip(): st.error('Enter a name.')
                elif any(n['node_type_id']==typ and n['node_name'].casefold()==name.strip().casefold() for n in db['nodes']): st.error('This name already exists for the selected type.')
                else:
                    d=copy.deepcopy(db); d['nodes'].append({'node_id':next_id(d['nodes'],'node_id'),'node_type_id':typ,'node_name':name.strip()}); st.session_state['nodes_mode']=None; commit(d,'nodes')
    elif mode=='edit':
        edit_df=df[['node_id','node_name']].copy()
        edited=st.data_editor(edit_df,column_config={'node_id':st.column_config.TextColumn('Node ID',disabled=True),'node_name':st.column_config.TextColumn('Node Name')},disabled=['node_id'],num_rows='fixed',use_container_width=True,hide_index=True,key='nodes_edit_editor')
        c1,c2,_=st.columns([2,2,4])
        if c1.button('Finish',icon=':material/check:'):
            d=copy.deepcopy(db); errors=[]; seen_names=set()
            for _,row in edited.iterrows():
                name=str(row['node_name']).strip() if pd.notna(row['node_name']) else ''; nid=str(row['node_id'])
                if not name: errors.append('Node name cannot be empty.'); continue
                if name.casefold() in seen_names: errors.append(f'Duplicate name: {name}'); continue
                seen_names.add(name.casefold())
                same=[n for n in d['nodes'] if n['node_type_id']==typ and n['node_name'].casefold()==name.casefold() and n['node_id']!=nid]
                if same: errors.append(f'Duplicate name: {name}'); continue
                next(n for n in d['nodes'] if n['node_id']==nid)['node_name']=name
            if errors:
                for e in errors: st.error(e)
            else: st.session_state['nodes_mode']=None; commit(d,'nodes')
        if c2.button('Cancel',icon=':material/close:'): st.session_state['nodes_mode']=None; st.rerun()
    elif mode=='delete':
        event=st.dataframe(df,use_container_width=True,hide_index=True,on_select='rerun',selection_mode='multi-row',key='nodes_delete_df')
        selected_indices=event.selection.rows if event.selection else []
        c1,c2,_=st.columns([2,2,4])
        if c1.button('Confirm',icon=':material/delete:'):
            if not selected_indices: st.error('Select at least one row to delete.')
            else:
                ids_to_delete={filtered[i]['node_id'] for i in selected_indices}
                in_use={r['parent'] for r in db['node_relationships']}|{r['child'] for r in db['node_relationships']}
                blocked=ids_to_delete&in_use
                if blocked:
                    names=', '.join(next(n['node_name'] for n in db['nodes'] if n['node_id']==nid) for nid in blocked)
                    st.error(f'Cannot delete nodes used in relationships: {names}')
                else:
                    d=copy.deepcopy(db); d['nodes']=[n for n in d['nodes'] if n['node_id'] not in ids_to_delete]; st.session_state['nodes_mode']=None; commit(d,'nodes')
        if c2.button('Cancel',icon=':material/close:',key='del_cancel'): st.session_state['nodes_mode']=None; st.rerun()

elif page=='Hierarchies & rules':
    show(db['hierarchies'])
    with st.form('new_h'):
        name=st.text_input('New hierarchy name')
        if st.form_submit_button('Create hierarchy',icon=':material/account_tree:'):
            if name.strip():
                d=copy.deepcopy(db); d['hierarchies'].append({'hier_id':next_id(d['hierarchies'],'hier_id'),'hier_desc':name.strip(),'active':'Y'}); commit(d,'hierarchies')
            else: st.error('Name is required.')
    hid=hselect('rules_h')
    selected=next(h for h in db['hierarchies'] if h['hier_id']==hid)
    with st.form('edit_h'):
        name=st.text_input('Hierarchy description',selected['hier_desc']); enabled=st.checkbox('Active',selected['active']=='Y')
        if st.form_submit_button('Save hierarchy',icon=':material/save:'):
            d=copy.deepcopy(db); h=next(h for h in d['hierarchies'] if h['hier_id']==hid); h.update(hier_desc=name.strip(),active='Y' if enabled else 'N'); commit(d,'hierarchies')
    type_map={t['node_type_id']:f"{t['node_type_id']} - {t['node_type_name']}" for t in db['node_types']}
    rules_display=pd.DataFrame([r for r in db['level_rules'] if r['hier_id']==hid])
    if not rules_display.empty:
        rules_display['parent_node_type']=rules_display['parent_node_type'].map(type_map)
        rules_display['child_node_type']=rules_display['child_node_type'].map(type_map)
    st.dataframe(rules_display,use_container_width=True,hide_index=True)
    st.caption('Choose types in order. Rule changes are blocked once this hierarchy has relationships.')
    types={t['node_type_id']:t['node_type_name'] for t in db['node_types'] if t['node_type_id']!='0'}
    chain=st.multiselect('Ordered levels',list(types),format_func=types.get,default=[r['child_node_type'] for r in sorted(db['level_rules'],key=lambda x:int(x['level'])) if r['hier_id']==hid])
    if st.button('Save level rules',icon=':material/save:'):
        if any(r['hier_id']==hid for r in db['node_relationships']): st.error('Create a new hierarchy to use a different level structure.')
        elif not chain: st.error('Select at least one level.')
        else:
            d=copy.deepcopy(db); d['level_rules']=[r for r in d['level_rules'] if r['hier_id']!=hid]
            for i,t in enumerate(chain): d['level_rules'].append({'hier_id':hid,'level':str(i+1),'parent_node_type':'0' if i==0 else chain[i-1],'child_node_type':t})
            commit(d,'level_rules')

elif page=='Relationships':
    hid=hselect('rel_h')
    node_lookup={n['node_id']:n for n in db['nodes']}
    type_lookup={t['node_type_id']:t['node_type_name'] for t in db['node_types']}
    hier_lookup={h['hier_id']:h['hier_desc'] for h in db['hierarchies']}
    rule_lookup={r['level']:r for r in db['level_rules'] if r['hier_id']==hid}
    rel_rows=[r for r in db['node_relationships'] if r['hier_id']==hid]
    if rel_rows:
        rel_df=pd.DataFrame(rel_rows)
        def enrich_node(nid):
            n=node_lookup.get(nid)
            return f"{nid} - ({n['node_name']})" if n else nid
        def enrich_level(lvl):
            r=rule_lookup.get(lvl)
            if not r: return lvl
            ptype=type_lookup.get(r['parent_node_type'],'')
            ctype=type_lookup.get(r['child_node_type'],'')
            return f"{lvl} - {ptype} \u2192 {ctype}"
        rel_df['hier_id']=rel_df['hier_id'].map(lambda x:f"{x} - {hier_lookup.get(x,x)}")
        rel_df['level']=rel_df['level'].apply(enrich_level)
        rel_df['parent']=rel_df['parent'].apply(enrich_node)
        rel_df['child']=rel_df['child'].apply(enrich_node)
        with st.expander('Filters',icon=':material/filter_alt:'):
            fc1,fc2,fc3=st.columns(3)
            f_level=fc1.multiselect('Level',sorted(rel_df['level'].unique()),key='rel_f_level')
            _after_level=rel_df[rel_df['level'].isin(f_level)] if f_level else rel_df
            parent_opts=sorted(_after_level['parent'].unique())
            # clear stale parent selections that no longer match filtered options
            if 'rel_f_parent' in st.session_state:
                st.session_state['rel_f_parent']=[v for v in st.session_state['rel_f_parent'] if v in parent_opts]
            f_parent=fc2.multiselect('Parent',parent_opts,key='rel_f_parent')
            _after_parent=_after_level[_after_level['parent'].isin(f_parent)] if f_parent else _after_level
            child_opts=sorted(_after_parent['child'].unique())
            if 'rel_f_child' in st.session_state:
                st.session_state['rel_f_child']=[v for v in st.session_state['rel_f_child'] if v in child_opts]
            f_child=fc3.multiselect('Child',child_opts,key='rel_f_child')
        display_df=_after_parent[_after_parent['child'].isin(f_child)] if f_child else _after_parent
        st.dataframe(display_df,use_container_width=True,hide_index=True)
    else:
        st.info('No relationships for this hierarchy.')
    rules=sorted([r for r in db['level_rules'] if r['hier_id']==hid], key=lambda r:int(r['level']))
    if not rules:
        st.warning('Define level rules first.'); st.stop()
    def level_label(lvl):
        r=next((r for r in rules if r['level']==lvl),None)
        if not r: return lvl
        return f"{lvl} - {type_lookup.get(r['parent_node_type'],'')} \u2192 {type_lookup.get(r['child_node_type'],'')}"
    existing_rels=[r for r in db['node_relationships'] if r['hier_id']==hid and not r['end']]
    levels_with_data={r['level'] for r in existing_rels}
    action=st.radio('Action',['Add new relationship','Modify relationship','End relationship'])
    st.caption('Timestamps are effective timestamps. End is exclusive. Closed rows remain in history.')
    # determine unlocked levels based on action
    all_levels=[r['level'] for r in rules]
    if action=='Add new relationship':
        unlocked=set()
        for i,r in enumerate(rules):
            lvl=r['level']
            if i==0:
                unlocked.add(lvl)
            elif rules[i-1]['level'] in levels_with_data:
                unlocked.add(lvl)
            else:
                break
        def add_level_label(lvl):
            base=level_label(lvl)
            return base if lvl in unlocked else f"\U0001f512\uFE0E {base} (complete previous level first)"
        level=st.selectbox('Level',all_levels,format_func=add_level_label)
        if level not in unlocked:
            st.warning('Complete relationships at the previous level before adding to this level.')
            st.stop()
    else:
        available_levels=[r['level'] for r in rules if r['level'] in levels_with_data]
        if not available_levels:
            st.info('No relationships exist yet for this hierarchy.'); st.stop()
        level=st.selectbox('Level',available_levels,format_func=level_label)
    rule=next(r for r in rules if r['level']==level)
    rule_idx=next(i for i,r in enumerate(rules) if r['level']==level)
    # parent filtering: for Add, cascade from previous level's children
    if action=='Add new relationship':
        if rule_idx==0:
            parents=[n['node_id'] for n in db['nodes'] if n['node_type_id']==rule['parent_node_type']]
        else:
            prev_level=rules[rule_idx-1]['level']
            parents=sorted({r['child'] for r in existing_rels if r['level']==prev_level})
        if not parents:
            st.warning('Complete the previous level first to unlock parent options.'); st.stop()
    else:
        if rule_idx==0:
            parents=[n['node_id'] for n in db['nodes'] if n['node_type_id']==rule['parent_node_type']]
        else:
            prev_level=rules[rule_idx-1]['level']
            parents=sorted({r['child'] for r in existing_rels if r['level']==prev_level})
    children=[n['node_id'] for n in db['nodes'] if n['node_type_id']==rule['child_node_type']]
    if not parents or not children:
        st.warning('Add nodes of the required types first.'); st.stop()
    if action=='Add new relationship':
        with st.form('add_relationship'):
            parent=st.selectbox('Parent',parents,format_func=label)
            child=st.selectbox('Child',children,format_func=label)
            st.caption('Start timestamp is captured automatically when the record is created. End timestamp stays blank.')
            if st.form_submit_button('Add relationship',icon=':material/add_link:'):
                try:
                    d=add_relationship(db,hid,level,parent,child,datetime.now().isoformat(timespec='seconds'))
                    commit(d,'node_relationships')
                except ValueError as e: st.error(str(e))
    else:
        rr=[r for r in db['node_relationships'] if r['hier_id']==hid and r['level']==level and not r['end']]
        if not rr:
            st.info('No open-ended relationships at this level. Closed relationships remain in the history table.')
        else:
            by_id={r['relationship_id']:r for r in rr}
            def relationship_label(x):
                r=by_id[x]
                return f"ID {x}: {label(r['parent'])} → {label(r['child'])} | Start: {r['start']}"
            rid=st.selectbox('Select existing relationship',list(by_id),format_func=relationship_label)
            selected=by_id[rid]
            if action=='Modify relationship':
                alternatives=[p for p in parents if p!=selected['parent']]
                st.write('Child:',label(selected['child']))
                st.caption('Changing parent ends the selected row and creates a new ID for the same child. Descendants remain attached.')
                if not alternatives:
                    st.info('Add another parent node of the required type first.')
                else:
                    with st.form(f'modify_relationship_{rid}'):
                        parent=st.selectbox('New parent',alternatives,format_func=label)
                        st.caption('Effective timestamp is captured automatically when the modification is submitted.')
                        if st.form_submit_button('Modify relationship',icon=':material/swap_horiz:'):
                            try:
                                d=modify_relationship(db,rid,parent,datetime.now().isoformat(timespec='seconds'))
                                commit(d,'node_relationships')
                            except ValueError as e: st.error(str(e))
            else:
                with st.form(f'end_relationship_{rid}'):
                    st.caption('Keeps the selected relationship ID. No replacement row is created. End timestamp is captured automatically.')
                    if st.form_submit_button('End relationship',icon=':material/event_busy:'):
                        try:
                            d=end_relationship(db,rid,datetime.now().isoformat(timespec='seconds'))
                            commit(d,'node_relationships')
                        except ValueError as e: st.error(str(e))

elif page=='Validation':
    errors=validate(db)
    if errors:
        for e in errors: st.error(e)
    else: st.success('Structural validation passed: IDs, references, types, timestamp intervals and overlapping parent assignments.')
    linked={r['child'] for r in db['node_relationships']}
    st.subheader('Nodes without any child assignment')
    st.caption('Expected for workbook names whose business mappings have not been supplied.')
    show([n for n in db['nodes'] if n['node_id']!='0' and n['node_id'] not in linked])
else:
    hid=hselect('view_h')
    dc1,dc2=st.columns(2)
    as_d=dc1.date_input('As of date',date.today())
    as_t=dc2.time_input('As of time',time(23,59,59))
    day=datetime.combine(as_d,as_t).isoformat()
    try: rows,cols,warnings=flatten(db,hid,day)
    except ValueError as e: st.error(str(e)); st.stop()
    for w in warnings: st.warning(w)
    if page=='Hierarchy explorer':
        edges=[r for r in db['node_relationships'] if r['hier_id']==hid and active(r,day)]
        dot=['digraph G {','rankdir=TB;','node [shape=box style="rounded,filled" fillcolor="#F3F4FA" color="#1010EB" fontcolor="#170F4F" fontname="Arial"];','edge [color="#170F4F"];']
        ids={x for r in edges for x in (r['parent'],r['child'])}
        for n in ids: dot.append(f'{json.dumps(n)} [label={json.dumps(label(n))}];')
        for r in edges: dot.append(f'{json.dumps(r["parent"])} -> {json.dumps(r["child"])};')
        dot.append('}'); st.graphviz_chart('\n'.join(dot))
    else:
        st.caption('One row per complete path to the final configured level. Incomplete paths are excluded and flagged above. Names reflect current node names even for historical dates.')
        st.dataframe(pd.DataFrame(rows,columns=cols),use_container_width=True,hide_index=True)
        if st.button('Generate and save rst_hier.csv',icon=':material/description:'):
            write_csv(DATA/'rst_hier.csv',rows,cols); st.success('Snapshot saved. Regenerate after changes.')
        buf=io.StringIO(); w=csv.DictWriter(buf,fieldnames=cols); w.writeheader(); w.writerows(rows)
        st.download_button('Download current report',buf.getvalue(),'rst_hier.csv','text/csv',icon=':material/download:')