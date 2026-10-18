"""Standalone interactive raw-trade viewer. Does not modify the project website.

Install: python -m pip install -r requirements-viewer.txt
Run:     python plot_raw_ticks.py
"""
import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import re
import sys
import subprocess
import threading
import time
from urllib.parse import parse_qs, urlparse
import webbrowser

try:
    import duckdb
    from plotly.offline import get_plotlyjs
except ImportError:
    isolated = Path(__file__).resolve().parent / '.venv-raw-viewer' / 'Scripts' / 'python.exe'
    if isolated.is_file() and Path(sys.executable).resolve() != isolated.resolve():
        raise SystemExit(subprocess.call([str(isolated), '-B', str(Path(__file__).resolve()), *sys.argv[1:]]))
    raise SystemExit('Install viewer dependencies first: python -m pip install -r requirements-viewer.txt')

ROOT = Path(__file__).resolve().parent
PATTERN = re.compile(r'([A-Z0-9]+(?:_\d{6})?)-trades-(\d{4}-\d{2}-\d{2})\.csv')
DAY = 86_400_000
QUERY_LOCK = threading.Lock()


def midnight(day):
    return int(datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)


def inventory(root, symbols=None):
    contracts = {}
    for file in sorted(root.rglob('*.csv')):
        match = PATTERN.fullmatch(file.name)
        if not match or (symbols and match[1] not in symbols):
            continue
        day = date.fromisoformat(match[2])
        contracts.setdefault(match[1], []).append((midnight(day), file))
    return contracts


def query_contract(files, start, end, max_points):
    """Select actual trade observations; never invent candles or interpolate."""
    # Read source columns as text: tolerate optional published header rows.
    # Explicitly classify header rows separately from malformed trade rows.
    sql = """
    WITH raw AS (
      SELECT * FROM read_csv(?, header=false, auto_detect=false,
        columns={'id':'VARCHAR','price':'VARCHAR','qty':'VARCHAR',
                 'quote_qty':'VARCHAR','time':'VARCHAR','maker':'VARCHAR'},
        ignore_errors=false)
    ), typed AS (
      SELECT try_cast(id AS BIGINT) AS id, try_cast(price AS DOUBLE) AS p,
             try_cast(qty AS DOUBLE) AS q, try_cast(time AS BIGINT) AS t,
             try_cast(maker AS BOOLEAN) AS m,
             lower(trim(id)) IN ('id','trade_id','tradeid') AS header
      FROM raw
    )
    """
    columns = 'id,p,q,t,m'
    valid = 'id IS NOT NULL AND isfinite(p) AND p>0 AND isfinite(q) AND q>0 AND t IS NOT NULL AND m IS NOT NULL'
    paths = [str(p) for p in files]
    connection = duckdb.connect()
    connection.execute("SET threads=2")
    connection.execute("SET memory_limit='768MB'")
    try:
        # Every group retains first, last, minimum and maximum priced ticks.
        # Count malformed rows explicitly, including rows with unparseable time.
        step = max(1, math.ceil((end - start) / max(1, max_points // 4)))
        packed = 'struct_pack(id:=id,p:=p,q:=q,t:=t,m:=m)'
        query = sql + f"""
          SELECT floor((t-?)/?) AS bucket, count(*) AS n,
            arg_min({packed},struct_pack(t:=t,id:=id)),
            arg_min({packed},struct_pack(p:=p,t:=t,id:=id)),
            arg_max({packed},struct_pack(p:=p,t:=t,id:=id)),
            arg_max({packed},struct_pack(t:=t,id:=id))
          FROM typed WHERE ({valid}) AND t>=? AND t<? GROUP BY bucket ORDER BY bucket
        """
        groups = connection.execute(query, [paths, start, step, start, end]).fetchall()
        count = sum(row[1] for row in groups)
        points = {}
        for row in groups:
            for tick in row[2:]:
                points[(tick['t'], tick['id'])] = tick
        sampled = count > max_points
        if not sampled and count:
            # Preserve all ticks, including equal-time ticks, for detail windows.
            rows = connection.execute(sql + f'SELECT {columns} FROM typed WHERE ({valid}) AND t>=? AND t<? ORDER BY t,id', [paths, start, end]).fetchall()
            ticks = [dict(zip(['id','p','q','t','m'], row)) for row in rows]
        else:
            ticks = sorted(points.values(), key=lambda p: (p['t'], p['id']))
        quality = connection.execute(sql + f"""
          SELECT count(*) FILTER (WHERE header),
                 count(*) FILTER (WHERE NOT coalesce(header,false) AND NOT coalesce(({valid}),false)),
                 count(*) FILTER (WHERE ({valid}) AND (t<? OR t>=?))
          FROM typed
        """, [paths, start, end]).fetchone()
        # Preserve duplicate IDs in exact mode; overview sampling may merge them.
        return {'ticks': [[p['t'], p['p'], p['q'], str(p['id']), p['m']] for p in ticks],
                'raw_rows_in_window': count, 'sampled': sampled,
                'header_rows': quality[0], 'invalid_rows_in_source_files': quality[1],
                'valid_rows_outside_window': quality[2], 'source_files': len(files)}
    finally:
        connection.close()


def build_response(contracts, start, end, max_points, cache, progress=None):
    response = {'start': start, 'end': end, 'contracts': [], 'total_raw_rows': 0, 'total_shown': 0}
    cache.mkdir(parents=True, exist_ok=True)
    for index, (symbol, entries) in enumerate(contracts.items()):
        if progress:
            progress({'completed':index,'total':len(contracts),'pair':symbol,'unit':'contracts'})
        files = [p for day, p in entries if day < end and day + DAY > start]
        if not files:
            continue
        fingerprint = [str(p) + ':' + str(p.stat().st_size) + ':' + str(p.stat().st_mtime_ns) for p in files]
        key = hashlib.sha256(json.dumps([start, end, max_points, fingerprint]).encode()).hexdigest()
        cached = cache / (key + '.json')
        if cached.exists():
            try:
                result = json.loads(cached.read_text(encoding='utf-8'))
            except (ValueError, OSError):
                result = query_contract(files, start, end, max_points)
        else:
            print(f'Reading {symbol}: {len(files)} daily CSVs...', flush=True)
            result = query_contract(files, start, end, max_points)
        # Cache only display observations; original trade archives stay untouched.
        temporary = cached.with_suffix('.part')
        temporary.write_text(json.dumps(result), encoding='utf-8')
        temporary.replace(cached)
        result['symbol'] = symbol
        # Source-day coverage is independent of sampling. Never bridge a day
        # without an extracted source file, even in the full-history overview.
        spans = []
        for day in sorted({day for day, _ in entries}):
            if spans and day == spans[-1][1]:
                spans[-1][1] = day + DAY
            else:
                spans.append([day, day + DAY])
        result['coverage_spans'] = spans
        result['sampling_bucket_ms'] = max(1, math.ceil((end-start) / max(1, max_points//4))) if result['sampled'] else 0
        response['contracts'].append(result)
        response['total_raw_rows'] += result['raw_rows_in_window']
        response['total_shown'] += len(result['ticks'])
    if progress:
        progress({'completed':len(contracts),'total':len(contracts),'unit':'contracts'})
    return response


HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Raw Tick Explorer</title><script src="/plotly.js"></script><style>
*{box-sizing:border-box}body{margin:0;background:#101620;color:#d6dfeb;font:13px Arial,sans-serif}header{padding:20px 24px;border-bottom:1px solid #273142;display:flex;justify-content:space-between;gap:20px;align-items:center}h1{margin:0 0 7px;font-size:20px}header p{margin:0;color:#8798af;font-size:11px}.pill{font-size:10px;border:1px solid #35524d;color:#8dd3be;padding:7px 10px;border-radius:5px;white-space:nowrap}.toolbar{padding:13px 24px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;background:#151d2a}button,select,input{font:11px Arial;background:#1b2738;color:#c9d9e9;border:1px solid #334158;border-radius:4px;padding:7px 9px}button{cursor:pointer}button:hover{border-color:#65b8bb}input[type=checkbox]{accent-color:#49c6b6}.status{color:#92a3b8;font-size:11px;padding:11px 24px;min-height:36px}.layout{display:grid;grid-template-columns:220px minmax(0,1fr)}aside{padding:14px 16px;border-right:1px solid #273142;height:calc(100vh - 207px);overflow:auto;min-height:350px}aside input[type=search]{width:100%;margin-bottom:12px}aside label{display:flex;align-items:center;gap:8px;font-size:10px;padding:7px 0;cursor:pointer}aside label[hidden]{display:none}aside .dot{height:7px;width:7px;border-radius:50%;flex-shrink:0}#chart{height:calc(100vh - 247px);min-height:400px}section{min-width:0}.help{padding:10px 24px;font-size:10px;line-height:1.8;color:#7e90a9;border-top:1px solid #273142}.error{color:#ffb6a8}.busy{color:#e1bd77}#quality{padding:7px 24px;font-size:10px;color:#97abc0}.date-input{max-width:192px}a{color:#65c7b4}@media(max-width:750px){.layout{grid-template-columns:1fr}aside{height:auto;max-height:145px;border-bottom:1px solid #273142}#symbols{display:flex;flex-wrap:wrap;gap:0 14px}aside input[type=search]{max-width:220px}#chart{height:65vh}header{padding:17px}.toolbar{padding:12px}.status{padding:10px 12px}}
</style></head><body><header><div><h1>Raw Tick Explorer</h1><p>All downloaded contracts on one chart. Local viewer only &middot; project website unchanged.</p></div><span class="pill">ACTUAL TRADE OBSERVATIONS</span></header>
<div class="toolbar"><label>From UTC <input class="date-input" type="datetime-local" id="start" step="0.001"></label><label>To UTC <input class="date-input" type="datetime-local" id="end" step="0.001"></label><button id="apply">Load window</button><button id="reset">Full history</button><button id="lastday">Last available day</button><label>Display <select id="limit"><option value="2000">2,000 pts / contract</option><option value="6000" selected>6,000 pts / contract</option><option value="20000">20,000 pts / contract</option><option value="100000">100,000 pts / contract</option></select></label><label><input type="checkbox" id="connect" checked> Line chart</label></div>
<div id="status" class="status" role="status">Discovering local contracts...</div><div class="layout"><aside><input id="search" type="search" placeholder="Filter contract names" aria-label="Filter contract names"><div style="display:flex;gap:6px;margin-bottom:10px"><button id="showall">Show all</button><button id="hideall">Hide all</button></div><div id="symbols"></div></aside><section><div id="chart"></div><div id="quality"></div><div class="help">Scroll to zoom &middot; drag to pan &middot; use the chart toolbar for box zoom &middot; double-click to reset &middot; click legend to hide, double-click to isolate.<br>Wide windows retain first / minimum / maximum / last observed ticks per time bucket. Zoom reloads detail from original CSVs. Exact mode appears only when the raw count fits the display budget.<br>Prices are executions, not simultaneous bid/ask quotes. No resampling into candles, forward filling, spread calculation or backtest. Lines break across missing source days. In exact detail, no-trade intervals over 5 minutes also break; sampled overviews use the larger of 5 minutes and two sampling buckets. Smaller gaps require zooming in. Connecting ticks is only a visual guide.</div></section></div>
<script>
const colors=['#59c9b2','#78a6ff','#e4b36b','#ce8cff','#f37989','#66c8e0','#aaca6a','#ef9c72','#9cacf0','#6de0ce'];let meta,current,request=0,controller,debounce,loading=false;const visible={};const $=id=>document.getElementById(id);const utc=t=>new Date(t).toISOString().slice(0,-1);const ms=s=>typeof s==='number'?s:Date.parse(s.endsWith('Z')?s:s+'Z');
function status(text,error=false){$('status').textContent=text;$('status').className='status '+(error?'error':'');}
function setDates(a,b){$('start').value=utc(a);$('end').value=utc(b);}
function sidebar(){ $('symbols').replaceChildren();meta.symbols.forEach((s,i)=>{const l=document.createElement('label');const cb=document.createElement('input');cb.type='checkbox';cb.checked=visible[s];cb.onchange=()=>{visible[s]=cb.checked;visibility();};const dot=document.createElement('span');dot.className='dot';dot.style.background=colors[i%colors.length];l.append(cb,dot,document.createTextNode(s));l.dataset.symbol=s;$('symbols').append(l);});}
function visibility(){if(!current)return;Plotly.restyle('chart',{visible:current.contracts.filter(c=>c.ticks.length).map(c=>visible[c.symbol]?true:'legendonly')});sidebar();filter();}
function filter(){const q=$('search').value.toUpperCase();$('symbols').querySelectorAll('label').forEach(l=>l.hidden=!l.dataset.symbol.includes(q));}
function gapTicks(c){const rows=[];let prev=null;const cutoff=Math.max(300000,2*(c.sampling_bucket_ms||0));for(const tick of c.ticks){if(prev){const missingDay=(c.coverage_spans||[]).some(span=>prev[0]<span[1]&&span[1]<=tick[0]);if(missingDay||tick[0]-prev[0]>cutoff)rows.push(null);}rows.push(tick);prev=tick;}return rows;}
async function load(a,b){if(!Number.isFinite(a)||!Number.isFinite(b)||a>=b){status('Choose valid UTC dates: From must precede To.',true);return;}const id=++request;if(controller)controller.abort();controller=new AbortController();loading=true;status('Reading original CSVs... first load of a wide window can take time. Progress is printed in Python.');$('status').classList.add('busy');setDates(a,b);try{const response=await fetch(`/api/ticks?start=${a}&end=${b}&limit=${$('limit').value}`,{signal:controller.signal});const data=await response.json();if(!response.ok)throw Error(data.error||'Query failed');if(id!==request)return;current=data;const traces=data.contracts.filter(c=>c.ticks.length).map(c=>({type:'scattergl',connectgaps:false,name:c.symbol,x:gapTicks(c).map(t=>t?new Date(t[0]).toISOString():null),y:gapTicks(c).map(t=>t?t[1]:null),mode:$('connect').checked?'lines':'markers',marker:{size:3,color:colors[meta.symbols.indexOf(c.symbol)%colors.length]},line:{width:1,color:colors[meta.symbols.indexOf(c.symbol)%colors.length]},visible:visible[c.symbol]?true:'legendonly',customdata:gapTicks(c).map(t=>t?[t[2],t[3],t[4]?'Sell (buyer maker)':'Buy (buyer taker)',c.sampled?'SAMPLED OVERVIEW':'ALL TICKS IN WINDOW']:null),hovertemplate:'<b>%{fullData.name}</b><br>%{x|%Y-%m-%d %H:%M:%S.%L} UTC<br>Price: %{y:.8f}<br>Quantity: %{customdata[0]}<br>Trade ID: %{customdata[1]}<br>Aggressor: %{customdata[2]}<br>%{customdata[3]}<extra></extra>'}));const sampled=data.contracts.some(c=>c.sampled);await Plotly.react('chart',traces,{paper_bgcolor:'#101620',plot_bgcolor:'#101620',font:{color:'#98acc5',size:10},margin:{l:75,r:35,t:25,b:55},dragmode:'pan',hovermode:'closest',showlegend:true,legend:{orientation:'h',y:-.15,font:{size:9}},xaxis:{type:'date',range:[new Date(a).toISOString(),new Date(b).toISOString()],gridcolor:'#222e40',showspikes:true,spikemode:'across',spikesnap:'cursor',title:'Time (UTC)'},yaxis:{title:'Trade price',gridcolor:'#222e40',showspikes:true,spikesnap:'cursor',fixedrange:false},uirevision:String(a)+':'+String(b)}, {responsive:true,scrollZoom:true,displaylogo:false,modeBarButtonsToRemove:['toImage','lasso2d','select2d']});if(id!==request)return;loading=false;status(`${sampled?'SAMPLED OVERVIEW - zoom in for individual trades':'EXACT DETAIL - every valid trade in this window'} | ${data.total_raw_rows.toLocaleString()} raw rows | ${data.total_shown.toLocaleString()} displayed points | ${traces.length} contracts with trades`);const invalid=data.contracts.reduce((s,c)=>s+c.invalid_rows_in_source_files,0);$('quality').textContent=`${invalid.toLocaleString()} invalid rows excluded from the selected daily files; headers are counted separately. Empty days are gaps, not filled prices. Same-time trades are preserved in exact mode.`;const chart=$('chart');chart.removeAllListeners('plotly_relayout');chart.on('plotly_relayout',ev=>{if(loading)return;let x=ev['xaxis.range[0]'],y=ev['xaxis.range[1]'];if(ev['xaxis.range']){[x,y]=ev['xaxis.range'];}if(ev['xaxis.autorange']){x=utc(meta.start);y=utc(meta.end);}if(x===undefined||y===undefined)return;clearTimeout(debounce);debounce=setTimeout(()=>load(ms(x),ms(y)),450);});chart.removeAllListeners('plotly_restyle');chart.on('plotly_restyle',()=>{chart.data.forEach(t=>visible[t.name]=t.visible!==false&&t.visible!=='legendonly');sidebar();filter();});}catch(e){if(e.name!=='AbortError'&&id===request){loading=false;status(e.message,true);}}}
$('apply').onclick=()=>load(ms($('start').value),ms($('end').value));$('reset').onclick=()=>load(meta.start,meta.end);$('lastday').onclick=()=>load(Math.max(meta.start,meta.end-86400000),meta.end);$('limit').onchange=()=>load(ms($('start').value),ms($('end').value));$('connect').onchange=()=>{if(current)Plotly.restyle('chart',{mode:$('connect').checked?'lines':'markers'});};$('search').oninput=filter;$('showall').onclick=()=>{meta.symbols.forEach(s=>visible[s]=true);visibility();};$('hideall').onclick=()=>{meta.symbols.forEach(s=>visible[s]=false);visibility();};
fetch('/api/meta').then(r=>r.json()).then(m=>{meta=m;m.symbols.forEach(s=>visible[s]=true);sidebar();load(m.start,m.end);}).catch(e=>status(e.message,true));
</script></body></html>'''


def progress_html(html):
    """Attach request-specific progress polling, without blocking data requests."""
    css='''#loading-progress[hidden]{display:none!important}#loading-progress{margin:0 24px 13px;padding:14px 16px;border:1px solid #35445a;background:#172232;border-radius:7px}#progress-heading{display:flex;justify-content:space-between;font-size:12px;margin-bottom:9px}#progress-percent{font-weight:bold;color:#6ed4bb}#progress-bar{display:block;width:100%;height:9px;accent-color:#51c6af}#progress-detail{color:#a4b4c9;font-size:10px;margin-top:9px;line-height:1.7}'''
    markup='''<div id="loading-progress" hidden><div id="progress-heading"><span id="progress-stage">Starting</span><span id="progress-percent">0%</span></div><progress id="progress-bar" max="100" value="0" aria-label="Processing progress"></progress><div id="progress-detail"></div></div>'''
    script=r'''
let activeJob=null,progressTimer;
function finishProgress(){clearTimeout(progressTimer);activeJob=null;$('loading-progress').hidden=true;}
function beginProgress(job){clearTimeout(progressTimer);activeJob=job;$('loading-progress').hidden=false;$('progress-percent').textContent='0%';$('progress-bar').value=0;$('progress-stage').textContent='Starting request';$('progress-detail').textContent='';
 async function poll(){try{const r=await fetch('/api/progress?job='+encodeURIComponent(job));const p=await r.json();if(activeJob!==job)return;const percent=p.percent||0;$('progress-percent').textContent=percent.toFixed(1)+'%';$('progress-bar').value=percent;const elapsed=Math.floor(p.elapsed_seconds||0);const clock=Math.floor(elapsed/60)+'m '+elapsed%60+'s';$('progress-stage').textContent=p.status==='queued'?'Waiting for the previous request to release the worker':p.status==='complete'?'Processing complete - transferring and rendering chart':p.status==='failed'?'Processing failed':p.status==='cancelled'?'Request cancelled':'Matching original ticks';$('progress-detail').textContent=[p.pair?`Pair ${p.pair_index||''}/${p.pair_total||''}: ${p.pair}`:'',p.day?`UTC day: ${p.day}`:'',p.total?`${(p.completed||0).toLocaleString()} / ${p.total.toLocaleString()} ${p.unit||'units'} complete`:'',`Elapsed: ${clock}`,p.error||''].filter(Boolean).join(' | ');if(p.status==='failed'){status(p.error||'Query failed',true);return;}}catch(e){if(activeJob!==job)return;$('progress-detail').textContent='Reconnecting to progress updates...';}if(activeJob===job)progressTimer=setTimeout(poll,500);}poll();}
'''
    html=html.replace('</style>',css+'</style>').replace('<div class="layout">',markup+'<div class="layout">')
    html=html.replace('async function load(a,b)',script+'\nasync function load(a,b)')
    html=html.replace('const id=++request;if(controller)controller.abort();',"const id=++request;const job=Date.now().toString(36)+'_'+id;if(activeJob)fetch('/api/cancel?job='+encodeURIComponent(activeJob),{method:'POST'}).catch(()=>{});if(controller)controller.abort();")
    html=html.replace('controller=new AbortController();loading=true;', 'controller=new AbortController();beginProgress(job);loading=true;')
    html=html.replace("limit=${$('limit').value}`", "limit=${$('limit').value}&job=${job}`")
    html=html.replace('loading=false;status(', 'loading=false;finishProgress();status(')
    html=html.replace('Reading original CSVs... first load of a wide window can take time. Progress is printed in Python.','Processing original CSVs... live progress is shown below.')
    # Keep the chosen point budget across refreshes, avoiding accidental rework.
    html=html.replace("fetch('/api/meta')", "const savedBudget=localStorage.getItem('tick-viewer-budget');if([...$('limit').options].some(o=>o.value===savedBudget))$('limit').value=savedBudget;$('limit').addEventListener('change',()=>localStorage.setItem('tick-viewer-budget',$('limit').value));fetch('/api/meta')")
    return html


def make_handler(contracts, start, end, cache, response_builder=build_response, html=HTML):
    html=progress_html(html)
    plotly_js = get_plotlyjs().encode()
    jobs = {}
    jobs_lock = threading.Lock()

    class QueryCancelled(Exception):
        pass

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, data, content_type='application/json', status=200):
            if not isinstance(data, bytes):
                data = json.dumps(data, allow_nan=False).encode()
            compressed = 'gzip' in self.headers.get('Accept-Encoding', '') and len(data) > 1024
            if compressed:
                data = gzip.compress(data, compresslevel=3)
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if compressed:
                self.send_header('Content-Encoding', 'gzip')
            self.end_headers()
            try:
                for offset in range(0, len(data), 64 * 1024):
                    self.wfile.write(data[offset:offset + 64 * 1024])
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def do_GET(self):
            # Bind to loopback only and reject foreign browser origins/hosts.
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
                self.respond({'error': 'Invalid host'}, status=403)
                return
            route = urlparse(self.path)
            job = None
            try:
                if route.path == '/':
                    self.respond(html.encode(), 'text/html; charset=utf-8')
                elif route.path == '/plotly.js':
                    self.respond(plotly_js, 'text/javascript; charset=utf-8')
                elif route.path == '/api/meta':
                    self.respond({'symbols': sorted(contracts), 'start': start, 'end': end})
                elif route.path == '/api/progress':
                    key = parse_qs(route.query).get('job', [''])[0]
                    with jobs_lock:
                        entry = jobs.get(key)
                        snapshot = dict(entry['state']) if entry else {'status':'starting','percent':0}
                        if entry:
                            snapshot['elapsed_seconds'] = round(time.monotonic()-entry['started'],1)
                    self.respond(snapshot)
                elif route.path == '/api/ticks':
                    args = parse_qs(route.query)
                    a, b = int(float(args['start'][0])), int(float(args['end'][0]))
                    limit = int(args.get('limit', ['6000'])[0])
                    if a >= b or limit < 100 or limit > 100_000:
                        raise ValueError('Invalid window or point budget')
                    job = args.get('job', [''])[0]
                    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', job):
                        job = 'request-' + str(time.monotonic_ns())
                    with jobs_lock:
                        # Bound job metadata while allowing active/queued work to finish.
                        for old in list(jobs):
                            if len(jobs)>64 and jobs[old]['state']['status'] in ('complete','failed','cancelled'):
                                del jobs[old]
                        entry={'state':{'status':'queued','percent':0,'completed':0,'total':0},
                               'started':time.monotonic(),'cancel':False}
                        jobs[job]=entry
                    def report(update):
                        with jobs_lock:
                            if entry['cancel']:
                                raise QueryCancelled('Superseded request cancelled')
                            entry['state'].update(update)
                            n,total=entry['state'].get('completed',0),entry['state'].get('total',0)
                            entry['state']['percent']=min(99,round(100*n/total,1)) if total else 0
                            entry['state']['status']='running'
                    with QUERY_LOCK:
                        report({})
                        result = response_builder(contracts, a, b, limit, cache, progress=report)
                    with jobs_lock:
                        entry['state'].update(status='complete',percent=100)
                    self.respond(result)
                else:
                    self.respond({'error': 'Not found'}, status=404)
            except Exception as error:
                if job:
                    with jobs_lock:
                        if job in jobs:
                            jobs[job]['state'].update(status='cancelled' if isinstance(error,QueryCancelled) else 'failed',error=str(error))
                print(f'Viewer error: {error}', flush=True)
                self.respond({'error': str(error)}, status=400)

        def do_POST(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):
                self.respond({'error':'Invalid host'},status=403)
                return
            route=urlparse(self.path)
            if route.path!='/api/cancel':
                self.respond({'error':'Not found'},status=404)
                return
            key=parse_qs(route.query).get('job',[''])[0]
            with jobs_lock:
                if key in jobs:
                    jobs[key]['cancel']=True
            self.respond({'cancel_requested':True})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'data' / 'ticks')
    parser.add_argument('--symbols', nargs='+', help='Optional contract subset; default is every CSV contract')
    parser.add_argument('--start', type=date.fromisoformat, help='Optional initial UTC date')
    parser.add_argument('--end', type=date.fromisoformat, help='Optional inclusive initial UTC date')
    parser.add_argument('--port', type=int, default=5190)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--matched', action='store_true', help='Near tick matched to latest past far tick, age strictly below 1 second')
    args = parser.parse_args()
    if args.matched:
        from plot_matched_ticks import launch
        if '--port' not in sys.argv:
            args.port = 5191
        launch(args)
        return
    contracts = inventory(args.input.resolve(), set(args.symbols) if args.symbols else None)
    if not contracts:
        parser.error('No extracted trade CSVs found. Run extract_ticks.py first or check --input.')
    days = [day for entries in contracts.values() for day, _ in entries]
    start = midnight(args.start) if args.start else min(days)
    end = midnight(args.end + timedelta(days=1)) if args.end else max(days) + DAY
    if start >= end:
        parser.error('--start must be on or before --end')
    handler = make_handler(contracts, start, end, ROOT / '.cache' / 'raw-viewer')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
    server.daemon_threads = True
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'{len(contracts)} contracts; {sum(map(len, contracts.values()))} extracted daily CSVs.', flush=True)
    print(f'Raw Tick Explorer: {url}\nKeep this Python process running. Ctrl+C to close.', flush=True)
    print('First wide-window query reads raw CSVs; subsequent identical views use a display cache.', flush=True)
    if not args.no_browser:
        threading.Timer(.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nViewer stopped.')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
