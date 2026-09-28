from datetime import date
import copy, io, csv, json
import pandas as pd
import streamlit as st
from relationship_actions import add_relationship, modify_relationship, end_relationship
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
[data-baseweb="tag"] { background:#1010EB !important; } [data-baseweb="tag"] * { color:#fff !important; -webkit-text-fill-color:#fff !important; }
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

st.title('Hierarchy Studio')
st.caption('RST hierarchy management • CSV proof of concept')
st.info('Demo mappings only. Master names come from HierDesign.xlsx; sample tower and connections are illustrative. Local single-user use.')
try: db=load()
except Exception as e: st.error(f'Cannot load CSV files: {e}'); st.stop()
if 'notice' in st.session_state: st.success(st.session_state.pop('notice'))

PAGES={'Overview':'','Nodes':'','Hierarchies & rules':'','Relationships':'','Hierarchy explorer':'','Validation':'','Reporting output':''}
page=st.sidebar.radio('Workspace',list(PAGES),format_func=lambda p:f'{PAGES[p]}  {p}')
st.sidebar.caption('Changes are saved to the data folder. Previous table versions are kept as .csv.bak files.')

def commit(candidate,table):
    try: save(candidate,table)
    except (ValueError,OSError) as e: st.error(str(e)); return
    st.session_state['notice']='Saved successfully.'; st.rerun()

def show(rows): st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
def label(n):
    r=next(r for r in db['nodes'] if r['node_id']==n)
    return f"{r['node_name']} · ID {n}"
def hselect(key):
    return st.selectbox('Hierarchy',[h['hier_id'] for h in db['hierarchies']],format_func=lambda x:next(h['hier_desc'] for h in db['hierarchies'] if h['hier_id']==x),key=key)

if page=='Overview':
    cols=st.columns(3)
    for col,title,table in zip(cols,['Nodes','Hierarchies','Relationships'],['nodes','hierarchies','node_relationships']): col.metric(title,len(db[table]))
    st.subheader('Start your demonstration')
    st.write('1. Explore the Canada path. 2. Rename a node. 3. Generate the report. 4. Add another compatible parent and move a branch using a later effective date.')
    st.write('All workbook master entries are available, but most are deliberately unassigned until real mappings are supplied.')
    st.subheader('CSV tables')
    table=st.selectbox('Table',list(db)); show(db[table])
    st.download_button('Download table',(DATA/f'{table}.csv').read_bytes(),f'{table}.csv','text/csv',icon=':material/download:')

elif page=='Nodes':
    typ=st.selectbox('Node type',[t['node_type_id'] for t in db['node_types']],format_func=lambda x:next(t['node_type_name'] for t in db['node_types'] if t['node_type_id']==x))
    show([n for n in db['nodes'] if n['node_type_id']==typ])
    with st.form('add_node'):
        name=st.text_input('New node name')
        if st.form_submit_button('Add node',icon=':material/add_circle:'):
            if typ=='0': st.error('Only the existing root is supported.')
            elif not name.strip(): st.error('Enter a name.')
            elif any(n['node_type_id']==typ and n['node_name'].casefold()==name.strip().casefold() for n in db['nodes']): st.error('This name already exists for the selected type.')
            else:
                d=copy.deepcopy(db); d['nodes'].append({'node_id':next_id(d['nodes'],'node_id'),'node_type_id':typ,'node_name':name.strip()}); commit(d,'nodes')
    ids=[n['node_id'] for n in db['nodes'] if n['node_type_id']==typ and n['node_id']!='0']
    if ids:
        node=st.selectbox('Rename node',ids,format_func=label)
        with st.form('rename'):
            name=st.text_input('Updated name',value=next(n['node_name'] for n in db['nodes'] if n['node_id']==node))
            if st.form_submit_button('Save name',icon=':material/edit:'):
                if not name.strip(): st.error('Name is required.')
                elif any(n['node_id']!=node and n['node_type_id']==typ and n['node_name'].casefold()==name.strip().casefold() for n in db['nodes']): st.error('Name already exists for this type.')
                else:
                    d=copy.deepcopy(db); next(n for n in d['nodes'] if n['node_id']==node)['node_name']=name.strip(); commit(d,'nodes')

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
    show([r for r in db['level_rules'] if r['hier_id']==hid])
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
    show([r for r in db['node_relationships'] if r['hier_id']==hid])
    rules=sorted([r for r in db['level_rules'] if r['hier_id']==hid], key=lambda r:int(r['level']))
    if not rules:
        st.warning('Define level rules first.'); st.stop()
    level=st.selectbox('Level',[r['level'] for r in rules])
    rule=next(r for r in rules if r['level']==level)
    parents=[n['node_id'] for n in db['nodes'] if n['node_type_id']==rule['parent_node_type']]
    children=[n['node_id'] for n in db['nodes'] if n['node_type_id']==rule['child_node_type']]
    if not parents or not children:
        st.warning('Add nodes of the required types first.'); st.stop()
    action=st.radio('Action',['Add new relationship','Modify relationship','End relationship'])
    st.caption('Dates are effective dates. End is exclusive. Closed rows remain in history.')
    if action=='Add new relationship':
        with st.form('add_relationship'):
            parent=st.selectbox('Parent',parents,format_func=label)
            child=st.selectbox('Child',children,format_func=label)
            start=st.date_input('Start date',date.today())
            st.caption('A new relationship ID is generated. End date stays blank.')
            if st.form_submit_button('Add relationship',icon=':material/add_link:'):
                try:
                    d=add_relationship(db,hid,level,parent,child,start.isoformat())
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
                        when=st.date_input('Effective change date',date.today())
                        if st.form_submit_button('Modify relationship',icon=':material/swap_horiz:'):
                            try:
                                d=modify_relationship(db,rid,parent,when.isoformat())
                                commit(d,'node_relationships')
                            except ValueError as e: st.error(str(e))
            else:
                with st.form(f'end_relationship_{rid}'):
                    when=st.date_input('End date',date.today())
                    st.caption('Keeps the selected relationship ID. No replacement row is created.')
                    if st.form_submit_button('End relationship',icon=':material/event_busy:'):
                        try:
                            d=end_relationship(db,rid,when.isoformat())
                            commit(d,'node_relationships')
                        except ValueError as e: st.error(str(e))

elif page=='Validation':
    errors=validate(db)
    if errors:
        for e in errors: st.error(e)
    else: st.success('Structural validation passed: IDs, references, types, date intervals and overlapping parent assignments.')
    linked={r['child'] for r in db['node_relationships']}
    st.subheader('Nodes without any child assignment')
    st.caption('Expected for workbook names whose business mappings have not been supplied.')
    show([n for n in db['nodes'] if n['node_id']!='0' and n['node_id'] not in linked])
else:
    hid=hselect('view_h'); day=st.date_input('As of date',date.today()).isoformat()
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