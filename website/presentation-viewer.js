// Presentation styling only. Tick matching and chart coordinates stay in Python.
const originalReact = Plotly.react;
function expiryLabel(symbol) {
  return symbol.replace(/([A-Z0-9]+)_(\d{2})(\d{2})(\d{2})/g, (_, asset, year, month, day) =>
    `${new Date(`20${year}-${month}-${day}T00:00:00Z`).toLocaleDateString('en-GB', {day:'numeric',month:'short',year:'numeric',timeZone:'UTC'})}`);
}
Plotly.react = function(host, traces, layout, config) {
  const detailed = document.body.classList.contains('exploring');
  traces.forEach(trace => {
    trace.name = expiryLabel(trace.meta.pair);
    trace.line.width = 1.6;
    trace.hovertemplate = '<b>Expiries: ' + trace.name + '</b><br>%{x|%d %b %Y, %H:%M:%S} UTC<br><b>Price difference: %{customdata[6]:,.2f} USDT</b><br>Earlier contract: %{customdata[0]:,.2f} USDT<br>Later contract: %{customdata[1]:,.2f} USDT<extra></extra>';
  });
  const result = originalReact.call(this, host, traces, {
    ...layout, autosize:true, width:undefined, height:undefined, paper_bgcolor:'#ffffff', plot_bgcolor:'#ffffff',
    font:{family:'Arial, sans-serif',color:'#607479',size:11},
    margin:{l:76,r:24,t:24,b:60}, showlegend:false,
    xaxis:{...layout.xaxis,gridcolor:'#eff3f2',title:{text:'Date (UTC)'},zeroline:false},
    yaxis:{...layout.yaxis,gridcolor:'#edf2f0',zerolinecolor:'#a7bdb5',title:{text:'Price difference (USDT per BTC)'}},
    hoverlabel:{bgcolor:'#ffffff',bordercolor:'#d9e6e1',font:{color:'#203b35',size:12}}
  }, {...config,displayModeBar:detailed,scrollZoom:detailed});
  return Promise.resolve(result).then(() => {
    parent.postMessage({type:'spread-ready',pairs:traces.filter(t=>t.showlegend!==false).length},location.origin);
  });
};
window.addEventListener('message', e => {
  if(e.origin!==location.origin || e.source!==parent || e.data.type!=='spread-explore')return;
  document.body.classList.toggle('exploring',e.data.enabled);
  const chart=document.getElementById('chart');
  if(chart?.data) {
    Plotly.react(chart,chart.data,chart.layout,chart._context);
  }
});
document.addEventListener('DOMContentLoaded',()=>{
  const chart=document.getElementById('chart');
  new ResizeObserver(()=>{if(chart?.data)Plotly.Plots.resize(chart);}).observe(chart);
});
