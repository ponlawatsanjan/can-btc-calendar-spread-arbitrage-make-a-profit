const colors=['#60a5fa','#a78bfa','#fbbf24','#34d399','#fb7185','#22d3ee','#c4b5fd','#fdba74','#93c5fd','#f0abfc'];
let snapshot, traces, exploring=false;
const chart=document.getElementById('chart');
function expiry(symbol){return symbol.replace(/[A-Z0-9]+_(\d{2})(\d{2})(\d{2})/g,(_,y,m,d)=>new Date(`20${y}-${m}-${d}T00:00:00Z`).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}));}
function notify(){parent.postMessage({type:'spread-ready',pairs:traces.filter(t=>t.visible!==false&&t.visible!=='legendonly').length},location.origin);}
async function draw(){
 await Plotly.react(chart,traces,{
  autosize:true,paper_bgcolor:'#111b2e',plot_bgcolor:'#111b2e',font:{family:'Arial, sans-serif',color:'#9caec5',size:11},margin:{l:76,r:24,t:24,b:60},showlegend:false,dragmode:'pan',hovermode:'closest',uirevision:'saved-spreads',
  xaxis:{type:'date',gridcolor:'#26344a',title:{text:'Date (UTC)'}},
  yaxis:{gridcolor:'#26344a',rangemode:'tozero',zeroline:true,zerolinecolor:'#587498',tickformat:',.2f',title:{text:'Price difference (USDT per BTC)'}},
  hoverlabel:{bgcolor:'#142137',bordercolor:'#344963',font:{color:'#eaf0f9',size:12}}
 },{responsive:true,displayModeBar:exploring,scrollZoom:exploring,displaylogo:false,modeBarButtonsToRemove:['toImage','lasso2d','select2d']});notify();
}
async function start(){
 try{
  const response=await fetch('data/spreads.json');if(!response.ok)throw Error('Saved dataset missing');snapshot=await response.json();
  traces=snapshot.pairs.map((pair,i)=>({type:'scattergl',mode:'lines',connectgaps:false,name:expiry(pair.symbol),visible:true,line:{width:1.6,color:colors[i%colors.length]},x:pair.rows.map(r=>new Date(r[0]).toISOString()),y:pair.rows.map(r=>r[1]),customdata:pair.rows.map(r=>[r[2],r[3]]),hovertemplate:'<b>Expiries: '+expiry(pair.symbol)+'</b><br>%{x|%d %b %Y, %H:%M:%S} UTC<br><b>Price difference: %{y:,.2f} USDT</b><br>Earlier contract: %{customdata[0]:,.2f} USDT<br>Later contract: %{customdata[1]:,.2f} USDT<extra></extra>'}));
  document.getElementById('from').value=new Date(snapshot.start).toISOString().slice(0,10);document.getElementById('to').value=new Date(snapshot.end-1).toISOString().slice(0,10);
  snapshot.pairs.forEach((pair,i)=>{const label=document.createElement('label'),input=document.createElement('input'),dot=document.createElement('span');input.type='checkbox';input.checked=true;input.onchange=()=>{traces[i].visible=input.checked;Plotly.restyle(chart,{visible:input.checked},[i]);notify();};dot.className='dot';dot.style.background=colors[i%colors.length];label.append(input,dot,document.createTextNode(expiry(pair.symbol)));document.getElementById('pairs').append(label);});
  document.getElementById('message').hidden=true;await draw();
 }catch(error){document.getElementById('message').textContent='The saved chart could not be opened. Please reload.';parent.postMessage({type:'spread-error'},location.origin);}
}
document.getElementById('apply').onclick=()=>{const a=Date.parse(document.getElementById('from').value+'T00:00:00Z'),b=Date.parse(document.getElementById('to').value+'T00:00:00Z')+86400000;if(!Number.isFinite(a)||!Number.isFinite(b)||a>=b){document.getElementById('message').hidden=false;document.getElementById('message').textContent='Choose a start date on or before the end date.';return;}document.getElementById('message').hidden=true;Plotly.relayout(chart,{'xaxis.range':[new Date(a).toISOString(),new Date(b).toISOString()],'xaxis.autorange':false});};
document.getElementById('reset').onclick=()=>Plotly.relayout(chart,{'xaxis.autorange':true,'yaxis.autorange':true});
function showAll(visible){traces.forEach(t=>t.visible=visible);document.querySelectorAll('#pairs input').forEach(c=>c.checked=visible);Plotly.restyle(chart,{visible});notify();}
document.getElementById('all').onclick=()=>showAll(true);document.getElementById('none').onclick=()=>showAll(false);
window.addEventListener('message',async e=>{if(e.origin!==location.origin||e.source!==parent||e.data.type!=='spread-explore')return;exploring=e.data.enabled;document.body.classList.toggle('exploring',exploring);if(traces)await draw();});
new ResizeObserver(()=>{if(chart.data)Plotly.Plots.resize(chart);}).observe(chart);
start();
