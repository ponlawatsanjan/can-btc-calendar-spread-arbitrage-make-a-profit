"""Near-anchored backward trade matching, before any display sampling."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
import threading
from itertools import combinations
import webbrowser

from plot_raw_ticks import DAY, ROOT, HTML, duckdb, inventory, midnight, make_handler, ThreadingHTTPServer


def pairs_from(contracts):
    groups = {}
    for symbol in contracts:
        match = re.fullmatch(r'([A-Z0-9]+)_(\d{6})', symbol)
        if match:
            groups.setdefault(match[1], []).append(symbol)
    result = {}
    for group in groups.values():
        for near,far in combinations(sorted(group),2):
            near_days={d for d,_ in contracts[near]}
            far_days={d for d,_ in contracts[far]}
            if near_days & far_days or any(d-DAY in far_days for d in near_days):
                result[near+' / '+far]=(near,far,contracts[near],contracts[far])
    return result


def read_leg(connection, name, files, start, end):
    if not files:
        connection.execute(f'CREATE TEMP TABLE {name}(id BIGINT,p DOUBLE,q DOUBLE,t BIGINT,m BOOLEAN)')
        return 0
    connection.execute(f"""CREATE TEMP TABLE {name}_source AS
      SELECT try_cast(id AS BIGINT) id, try_cast(price AS DOUBLE) p,
             try_cast(qty AS DOUBLE) q, try_cast(time AS BIGINT) t,
             try_cast(maker AS BOOLEAN) m,
             lower(trim(id)) IN ('id','trade_id','tradeid') AS header
      FROM read_csv(?,header=false,auto_detect=false,
        columns={{'id':'VARCHAR','price':'VARCHAR','qty':'VARCHAR','quote_qty':'VARCHAR','time':'VARCHAR','maker':'VARCHAR'}},ignore_errors=false)
    """, [[str(p) for p in files]])
    valid='id IS NOT NULL AND isfinite(p) AND p>0 AND isfinite(q) AND q>0 AND t IS NOT NULL AND m IS NOT NULL'
    invalid=connection.execute(f'SELECT count(*) FROM {name}_source WHERE NOT coalesce(header,false) AND NOT coalesce(({valid}),false)').fetchone()[0]
    connection.execute(f'CREATE TEMP TABLE {name} AS SELECT id,p,q,t,m FROM {name}_source WHERE ({valid}) AND t>=? AND t<?',[start,end])
    connection.execute(f'DROP TABLE {name}_source')
    return invalid


def query_matched(near_files, far_files, start, end, budget, sample_window=None):
    con=duckdb.connect()
    con.execute('SET threads=2')
    con.execute("SET memory_limit='768MB'")
    try:
        invalid=read_leg(con,'near_leg',near_files,start,end)
        # 999 ms of carry-in from the previous day is sufficient for <1s.
        invalid+=read_leg(con,'far_source',far_files,start-999,end)
        # Millisecond ties cannot reveal sub-ms execution order. Select the
        # highest far trade ID at that timestamp as a deterministic convention.
        con.execute('CREATE TEMP TABLE far_leg AS SELECT * FROM far_source QUALIFY row_number() OVER(PARTITION BY t ORDER BY id DESC)=1')
        examined=con.execute('SELECT count(*) FROM near_leg').fetchone()[0]
        con.execute('''CREATE TEMP TABLE joined AS
          SELECT n.t AS nt,n.p AS np,n.q AS nq,n.id AS nid,n.m AS nm,
                 f.t AS ft,f.p AS fp,f.id AS fid,n.t-f.t AS age,f.p-n.p AS spread
          FROM near_leg n ASOF LEFT JOIN far_leg f ON n.t>=f.t''')
        # Derive continuity from ALL original near ticks before discarding
        # unmatched rows or sampling; omitted failures must still break lines.
        con.execute('''CREATE TEMP TABLE segmented AS
          WITH flags AS (
            SELECT *,coalesce(ft IS NOT NULL AND age<1000,false) AS accepted,
              nt-lag(nt) OVER(ORDER BY nt,nid) AS anchor_gap FROM joined
          ) SELECT *,sum(CASE WHEN NOT accepted OR anchor_gap>=1000 THEN 1 ELSE 0 END)
            OVER(ORDER BY nt,nid ROWS UNBOUNDED PRECEDING) AS segment FROM flags''')
        con.execute('CREATE TEMP TABLE matched AS SELECT nt,np,nq,nid,nm,ft,fp,fid,age,spread,segment FROM segmented WHERE accepted')
        first=con.execute('SELECT nt,accepted,segment FROM segmented ORDER BY nt,nid LIMIT 1').fetchone()
        last=con.execute('SELECT nt,accepted,segment FROM segmented ORDER BY nt DESC,nid DESC LIMIT 1').fetchone()
        count=con.execute('SELECT count(*) FROM matched').fetchone()[0]
        sampled=count>budget
        if sampled:
            origin,finish=sample_window or (start,end)
            step=max(1,math.ceil((finish-origin)/max(1,budget//4)))
            packed='struct_pack(nt:=nt,np:=np,nq:=nq,nid:=nid,nm:=nm,ft:=ft,fp:=fp,fid:=fid,age:=age,spread:=spread,segment:=segment)'
            rows=con.execute(f'''SELECT
              arg_min({packed},struct_pack(t:=nt,id:=nid)),
              arg_min({packed},struct_pack(p:=spread,t:=nt,id:=nid)),
              arg_max({packed},struct_pack(p:=spread,t:=nt,id:=nid)),
              arg_max({packed},struct_pack(t:=nt,id:=nid))
              FROM matched GROUP BY floor((nt-?)/?)''',[origin,step]).fetchall()
            unique={(p['nt'],p['nid']):p for group in rows for p in group}
            observations=sorted(unique.values(),key=lambda p:(p['nt'],p['nid']))
        else:
            columns=['nt','np','nq','nid','nm','ft','fp','fid','age','spread','segment']
            observations=[dict(zip(columns,row)) for row in con.execute('SELECT * FROM matched ORDER BY nt,nid').fetchall()]
        return {'ticks':[[p['nt'],p['spread'],p['nq'],str(p['nid']),p['nm'],p['np'],p['fp'],p['ft'],str(p['fid']),p['age'],int(p['segment'])] for p in observations],
                'first_anchor':first,'last_anchor':last,
                'raw_rows_in_window':count,'sampled':sampled,'near_ticks_examined':examined,
                'unmatched_near_ticks':examined-count,'invalid_rows_in_source_files':invalid,
                'rule':'0 <= near_time - far_time < 1000 ms; latest far timestamp <= near timestamp'}
    finally:
        con.close()


def query_days(near_entries,far_entries,start,end,budget,progress=None):
    """Bound ASOF memory to a UTC day, then combine actual matched ticks."""
    summary={'ticks':[],'raw_rows_in_window':0,'near_ticks_examined':0,
             'unmatched_near_ticks':0,'invalid_rows_in_source_files':0}
    buckets={};exact=[];previous_boundary=None;previous_segment=None
    step=max(1,math.ceil((end-start)/max(1,budget//4)))
    days=sorted({d for d,_ in near_entries if d<end and d+DAY>start})
    for index,day in enumerate(days):
        if progress:
            progress(index,day)
        a,b=max(start,day),min(end,day+DAY)
        nf=[p for d,p in near_entries if d==day]
        ff=[p for d,p in far_entries if d<b and d+DAY>a-999]
        result=query_matched(nf,ff,a,b,budget,(start,end))
        first=result.get('first_anchor');last=result.get('last_anchor')
        continuous=(first and previous_boundary and first[1] and previous_boundary[1]
                    and 0<=first[0]-previous_boundary[0]<1000)
        for row in result['ticks']:
            row[10]=previous_segment if continuous and row[10]==first[2] else f'{day}:{row[10]}'
        if last and last[1] and result['ticks']:
            previous_segment=result['ticks'][-1][10]
        else:
            previous_segment=None
        previous_boundary=last
        for field in ('raw_rows_in_window','near_ticks_examined','unmatched_near_ticks','invalid_rows_in_source_files'):
            summary[field]+=result[field]
        if summary['raw_rows_in_window']<=budget:
            exact.extend(result['ticks'])
        else:
            exact=[]
        for row in result['ticks']:
            group=buckets.setdefault((row[0]-start)//step,[row,row,row,row])
            if (row[0],int(row[3]))<(group[0][0],int(group[0][3])):group[0]=row
            if (row[1],row[0],int(row[3]))<(group[1][1],group[1][0],int(group[1][3])):group[1]=row
            if (row[1],row[0],int(row[3]))>(group[2][1],group[2][0],int(group[2][3])):group[2]=row
            if (row[0],int(row[3]))>(group[3][0],int(group[3][3])):group[3]=row
        if progress:
            progress(index+1,day)
    summary['sampled']=summary['raw_rows_in_window']>budget
    if summary['sampled']:
        selected={(r[0],r[3]):r for group in buckets.values() for r in group}
        summary['ticks']=sorted(selected.values(),key=lambda r:(r[0],int(r[3])))
    else:
        summary['ticks']=sorted(exact,key=lambda r:(r[0],int(r[3])))
    return summary


def build_matched(pairs,start,end,budget,cache,progress=None):
    cache.mkdir(parents=True,exist_ok=True)
    response={'start':start,'end':end,'contracts':[],'total_raw_rows':0,'total_shown':0}
    total=sum(len({d for d,_ in ne if d<end and d+DAY>start}) for _,_,ne,_ in pairs.values())
    completed=0
    for pair_index,(label,(near,far,near_entries,far_entries)) in enumerate(pairs.items()):
        nf=[p for day,p in near_entries if day<end and day+DAY>start]
        if not nf:
            continue
        pair_days=len({d for d,_ in near_entries if d<end and d+DAY>start})
        def day_progress(done,day=None):
            if progress:
                progress({'completed':completed+done,'total':total,'unit':'pair-days',
                          'pair':label,'pair_index':pair_index+1,'pair_total':len(pairs),
                          'day':datetime.fromtimestamp(day/1000,timezone.utc).date().isoformat() if day is not None else '',
                          'pair_completed':done,'pair_days':pair_days})
        day_progress(0)
        ff=[p for day,p in far_entries if day<end and day+DAY>start-999]
        fingerprint=[(str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in nf+ff]
        key=hashlib.sha256(json.dumps(['matched-v3-segments',label,start,end,budget,fingerprint]).encode()).hexdigest()
        target=cache/(key+'.json')
        if target.exists():
            result=json.loads(target.read_text())
        else:
            print(f'Matching {label}: {len(nf)} near / {len(ff)} far daily files...',flush=True)
            result=query_days(near_entries,far_entries,start,end,budget,day_progress)
            temp=target.with_suffix('.part');temp.write_text(json.dumps(result));temp.replace(target)
        result['symbol']=label
        result['sampling_bucket_ms']=max(1,math.ceil((end-start)/max(1,budget//4))) if result['sampled'] else 0
        response['contracts'].append(result)
        response['total_raw_rows']+=result['raw_rows_in_window']
        response['total_shown']+=len(result['ticks'])
        day_progress(pair_days)
        completed+=pair_days
    return response


def matched_html():
    html=HTML.replace('Raw Tick Explorer','Matched Tick Explorer').replace('All downloaded contracts on one chart. Local viewer only &middot; project website unchanged.','Near-anchored ticks; latest far at or before near; match age strictly below 1 second.')
    html=html.replace('ACTUAL TRADE OBSERVATIONS','SPREAD = FAR - NEAR; AGE &lt; 1s')
    html=html.replace('<label>Display <select', '<label>Plot <select id="matched-view"><option value="spread" selected>Spread: far minus near</option><option value="prices">Matched near / far prices</option></select></label><label>Display <select')
    start=html.index('const traces=data.contracts.filter')
    end=html.index('const sampled=',start)
    html=html[:start]+'const traces=matchedTraces(data.contracts);'+html[end:]
    helpers="""
function matchedRows(c){return c.ticks;}
function matchedTraces(contracts){return contracts.filter(c=>c.ticks.length).flatMap(c=>{const rows=matchedRows(c);const spread=$('matched-view').value==='spread';const color=colors[meta.symbols.indexOf(c.symbol)%colors.length];return (spread?['spread']:['near','far']).map(leg=>({type:'scattergl',name:c.symbol+(spread?'':' '+leg),meta:{pair:c.symbol},legendgroup:c.symbol,showlegend:leg!=='far',visible:visible[c.symbol]?true:'legendonly',x:rows.map(t=>t?new Date(t[0]).toISOString():null),y:rows.map(t=>!t?null:leg==='near'?t[5]:leg==='far'?t[6]:t[1]),mode:$('connect').checked?'lines':'markers',connectgaps:false,line:{width:1.2,color},marker:{size:leg==='far'?4:3,symbol:leg==='far'?'square':'circle',opacity:leg==='far'?.6:1,color},customdata:rows.map(t=>t?[t[5],t[6],new Date(t[7]).toISOString(),t[3],t[8],t[9],t[1],c.sampled?'SAMPLED AFTER MATCHING':'ALL MATCHED TICKS']:null),hovertemplate:'<b>'+leg+' | '+c.symbol+'</b><br>Near time: %{x|%Y-%m-%d %H:%M:%S.%L} UTC<br>Near price: %{customdata[0]}<br>Far price: %{customdata[1]}<br>Far time: %{customdata[2]}<br>Near ID: %{customdata[3]} | Far ID: %{customdata[4]}<br>Far age: %{customdata[5]} ms<br>Far - near: %{customdata[6]}<br>%{customdata[7]}<extra></extra>'}));});}
"""
    html=html.replace('async function load(a,b)',helpers+'\nasync function load(a,b)')
    a=html.index('function visibility()');b=html.index('function filter()',a)
    html=html[:a]+"function visibility(){if(!current)return;const chart=$('chart');Plotly.restyle(chart,{visible:chart.data.map(t=>visible[t.meta.pair]?true:'legendonly')});sidebar();filter();}\n"+html[b:]
    html=html.replace("visible[t.name]=t.visible", "visible[t.meta.pair]=t.visible")
    html=html.replace("title:'Trade price'", "title:{text:$('matched-view').value==='spread'?'Far - near (USDT)':'Matched trade price (USDT)'}")
    html=html.replace("$('apply').onclick=", "$('matched-view').onchange=()=>load(ms($('start').value),ms($('end').value));$('apply').onclick=")
    html=html.replace('raw rows |','matched near ticks |').replace('contracts with trades','plotted traces').replace('EXACT DETAIL - every valid trade in this window','EXACT DETAIL - every accepted near/far match').replace('SAMPLED OVERVIEW - zoom in for individual trades','SAMPLED MATCHES - matching performed before display selection')
    a=html.index("$('quality').textContent=");b=html.index(';const chart=',a)
    html=html[:a]+"$('quality').textContent=`${data.contracts.reduce((n,c)=>n+c.near_ticks_examined,0).toLocaleString()} near ticks examined; ${data.contracts.reduce((n,c)=>n+c.unmatched_near_ticks,0).toLocaleString()} unmatched near ticks omitted; ${invalid} invalid source rows excluded. No future far ticks. Far ticks may be reused.`"+html[b:]
    a=html.index('<div class="help">');b=html.index('</div></section>',a)
    html=html[:a]+'''<div class="help">Each dot uses a near tick and the latest far tick with 0 &le; near time - far time &lt; 1000 ms. Exact 1000 ms matches and future ticks are rejected. Far ticks can be reused.<br>All same-underlying dated-contract pairs with overlapping source days are available. The two price series share the near timestamp; hover gives the actual far timestamp. Same-millisecond far ties use highest trade ID, not inferred sub-ms ordering.<br>Wide views select first/minimum-spread/maximum-spread/last matched rows per bucket; zoom for all matches. Matching always uses original ticks first. No candles or executable-fill claims.''' +html[b:]
    html=html.replace('fixedrange:false',"fixedrange:false,rangemode:$('matched-view').value==='spread'?'tozero':'normal',zeroline:true,zerolinecolor:'#61758c',zerolinewidth:1.5,tickformat:',.2f'")
    html=html.replace("title:'Time (UTC)'","title:{text:'Near tick time (UTC)'}")
    html=html.replace('No candles or executable-fill claims.', 'No candles or executable-fill claims. Lines connect consecutive accepted spread observations within each pair. The 1-second threshold filters matches only; it does not limit the interval between plotted points. All pairs use one shared USDT scale with zero visible; no rebasing.')
    html=html.replace("checked?'lines':'markers'","checked?'lines':'markers'")
    return html


def launch(args):
    contracts=inventory(args.input.resolve(),set(args.symbols) if args.symbols else None)
    pairs=pairs_from(contracts)
    if not pairs:
        raise SystemExit('Matching needs at least two dated contracts for the same underlying.')
    days=[d for entries in contracts.values() for d,_ in entries]
    start=midnight(args.start) if args.start else min(days)
    end=midnight(args.end+timedelta(days=1)) if args.end else max(days)+DAY
    if start>=end:
        raise SystemExit('Start must precede end.')
    handler=make_handler(pairs,start,end,ROOT/'.cache'/'matched-viewer',build_matched,matched_html())
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler);server.daemon_threads=True
    url=f'http://127.0.0.1:{server.server_port}'
    print(f'Matched Tick Explorer: {url}\n{len(pairs)} overlapping dated-contract pairs. Strict backward age < 1000 ms. Ctrl+C to stop.',flush=True)
    if not args.no_browser:
        threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
