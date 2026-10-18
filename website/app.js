// All observations below are deterministic illustrations, not downloaded market data.
// Replace this demo layer with reviewed, versioned research outputs later.
const chapters = ['overview', 'raw', 'clean', 'backtest', 'findings'];
const titles = ['Plotting rules', 'Raw spread explorer', 'Clean data', 'The backtest', 'Findings & limits'];
const main = document.querySelector('main');
const state = { range: 90, fees: 2, slippage: 1, costs: true, clean: true };
const series = Array.from({ length: 90 }, (_, i) => ({
  near: 80000 + i * 31 + Math.sin(i * .23) * 520 + Math.cos(i * .71) * 130,
  spread: 530 - i * 3.5 + Math.sin(i * .18) * 95 + Math.cos(i * .55) * 30,
})).map(d => ({ ...d, far: d.near + d.spread }));
const ticks = [
  { id: 101, time: '12:00:00.104', price: '80,012.10', qty: .012, side: 'Sell' },
  { id: 102, time: '12:00:00.218', price: '80,013.40', qty: .034, side: 'Buy' },
  { id: 102, time: '12:00:00.218', price: '80,013.40', qty: .034, side: 'Buy', flag: 'Duplicate ID' },
  { id: 103, time: '12:00:00.310', price: '80,011.80', qty: 0, side: 'Sell', flag: 'Zero quantity' },
  { id: 105, time: '12:00:00.541', price: '80,014.20', qty: .021, side: 'Buy' },
  { id: 104, time: '12:00:00.462', price: '80,012.70', qty: .008, side: 'Sell' },
  { id: 106, time: '12:00:00.728', price: '80,015.10', qty: .016, side: 'Buy' },
  { id: 107, time: '12:00:00.901', price: '80,014.90', qty: .043, side: 'Sell' },
];
function cleanTicks() {
  const seen = new Set();
  return ticks.filter(t => { if (seen.has(t.id) || t.qty <= 0) return false; seen.add(t.id); return true; }).sort((a, b) => a.time.localeCompare(b.time));
}
const notice = `<div class="draft-notice"><span class="notice-symbol">✳</span><p><strong>Illustrative edition.</strong> All charts and table values are synthetic examples. Downloaded trade data is not connected. No profitability result has been established.</p></div>`;
function hero(number, title, lede) {
  return `<section class="hero"><div class="eyebrow">CHAPTER ${number} / RESEARCH IN PROGRESS</div><h1>${title}</h1><p class="lede">${lede}</p><div class="hero-meta"><span>BTC · QUARTERLY FUTURES</span><span>BY PONLAWAT SANJAN</span><span>ILLUSTRATIVE DRAFT</span></div></section>${notice}`;
}
function figure(title, sub, legend, ranges = false) {
  return `<div class="figure"><div class="figure-top"><div><h3 class="figure-title">${title}</h3><p class="figure-sub">${sub}</p></div>${ranges ? `<div class="segmented" aria-label="Chart sample window">${[30, 60, 90].map(n => `<button data-range="${n}" aria-pressed="${state.range === n}" class="${state.range === n ? 'selected' : ''}">${n}D</button>`).join('')}</div>` : '<span class="badge">SAMPLE DATA</span>'}</div><div class="legend">${legend}</div><div id="research-chart" class="chart"></div><div class="figcaption"><span id="chart-caption">FIG. 01 — SYNTHETIC OBSERVATIONS · HOVER TO EXPLORE</span><span>NOT A RESEARCH RESULT</span></div></div>`;
}
function stats(items) {
  return `<div class="stats">${items.map(([label, value, note]) => `<div class="stat"><div class="stat-label">${label}</div><div class="stat-value">${value}</div><div class="stat-note">${note}</div></div>`).join('')}</div>`;
}
function pager(chapter) {
  const i = chapters.indexOf(chapter);
  return `<div class="chapter-bottom">${i ? `<a class="prev-link" href="#${chapters[i - 1]}">← ${titles[i - 1]}</a>` : '<span class="small-label">START WITH THE QUESTION.</span>'}${i < 4 ? `<a class="next-link" href="#${chapters[i + 1]}">Next: ${titles[i + 1]} <span>→</span></a>` : '<a class="next-link" href="#overview">Return to the question <span>↗</span></a>'}</div>`;
}
function table(rows, flags = false) {
  return `<div class="table-wrap"><table class="data-table"><caption class="sr-only">Synthetic near-contract trade examples. Side is an illustrative aggressor-side label.</caption><thead><tr><th>TRADE ID</th><th>TIME · UTC</th><th>PRICE · USDT</th><th>QTY · BTC</th><th>TAKER SIDE</th>${flags ? '<th>REVIEW NOTE</th>' : ''}</tr></thead><tbody>${rows.map(t => `<tr class="${flags && t.flag ? 'removed' : ''}"><td>${t.id}</td><td>${t.time}</td><td>${t.price}</td><td>${t.qty.toFixed(3)}</td><td>${t.side}</td>${flags ? `<td>${t.flag || '—'}</td>` : ''}</tr>`).join('')}</tbody></table></div>`;
}
function overview() {
  return hero('00', 'Can the calendar spread<br>be a <em>profitable trade?</em>', 'Two contracts. One underlying asset. A difference in time.<br>This notebook follows the evidence from raw trades to an execution-aware backtest.') +
    `<div class="section-head"><h2>The space between two prices</h2><span class="small-label">AN ILLUSTRATION, NOT AN EDGE</span></div>` +
    figure('Near & far quarterly futures', 'Synthetic prices · USDT per BTC · sample day index', '<span>Near contract</span><span class="gold">Far contract</span>', true) +
    `<div class="two-col"><div class="prose"><h2>A simple question. A careful test.</h2><p>When two Bitcoin futures expire at different dates, they trade at different prices. The difference is a calendar spread. That difference alone is not an arbitrage profit.</p><p>The test is whether a defined, reproducible strategy retains an edge after costs, liquidity constraints, and the risk of trading two legs.</p></div><aside class="margin-note"><div class="note-label">THE WORKING HYPOTHESIS</div><blockquote>“A spread on a chart is an observation.<br>A tradable edge must survive execution.”</blockquote><p>Research question · conclusion intentionally open</p></aside></div>` +
    `<div class="pipeline"><a href="#raw"><span class="step">01 / OBSERVE</span><span class="arrow">↗</span><h3>Raw data</h3><p>Start with individual trades and their provenance.</p></a><a href="#clean"><span class="step">02 / VALIDATE</span><span class="arrow">↗</span><h3>Clean data</h3><p>Check integrity, timing, and gaps before measuring.</p></a><a href="#backtest"><span class="step">03 / CHALLENGE</span><span class="arrow">↗</span><h3>The backtest</h3><p>Put the hypothesis under realistic constraints.</p></a></div>` + pager('overview');
}
function raw() {
  return hero('01', 'First, <em>observe.</em><br>Keep the original evidence.', 'Begin with individual executions from each futures contract. Preserve the source before interpreting the spread.') +
    stats([['SOURCE', 'Binance Vision', 'Planned source · USD-M trade archives'], ['GRANULARITY', 'Trade ticks', 'Individual executions, not candles'], ['REAL DATA', 'Not connected', 'This chapter uses synthetic examples']]) +
    `<div class="section-head"><h2>Two legs, observed independently</h2><span class="small-label">PRICES ≠ SIMULTANEOUS FILLS</span></div>` +
    figure('Trade-price illustration', 'Synthetic near / far prices · not actual exchange executions', '<span>Near contract</span><span class="gold">Far contract</span>') +
    `<div class="table-toolbar"><span>Sample raw records · near leg <span class="badge">8 DEMO ROWS</span></span><button class="text-button" id="export-sample">Download sample CSV ↓</button></div>` + table(ticks, true) +
    `<div class="two-col"><div class="prose"><h2>Preserve first. Interpret second.</h2><p>The download workflow retains daily ZIPs and their published checksums. A later data manifest will record contract identity, UTC coverage, trade counts, and quality findings.</p><p>These example anomalies demonstrate the review interface. They are deliberately constructed, not findings about Binance’s dataset.</p></div><aside class="margin-note"><div class="note-label">WHAT TRADES CANNOT TELL US</div><blockquote>The last traded price is not the price you can necessarily trade.</blockquote><p>Quote and depth history are still needed to model the executable spread.</p></aside></div>` + pager('raw');
}
function clean() {
  return hero('02', 'Make the data <em>trustworthy.</em><br>Then measure the spread.', 'An auditable cleaning process should explain every change, preserve market timing, and leave uncertainty visible.') +
    stats([['DEMO INPUT', '8 records', 'Constructed fixture · one near contract'], ['DEMO OUTPUT', '6 records', 'One duplicate + one zero-quantity row excluded'], ['LIVE PIPELINE', 'Pending', 'Rules below are a research specification']]) +
    `<div class="section-head"><h2>Spread behavior, before a strategy</h2><span class="small-label">FAR CLOSE − NEAR CLOSE</span></div>` + figure('Calendar spread illustration', 'Synthetic synchronized observations · USDT per BTC', '<span>Far − near spread</span>') +
    `<div class="table-toolbar"><span>Inspect the cleaning example</span><div class="segmented" aria-label="Cleaning view"><button data-clean="false" class="${!state.clean ? 'selected' : ''}" aria-pressed="${!state.clean}">Original · 8</button><button data-clean="true" class="${state.clean ? 'selected' : ''}" aria-pressed="${state.clean}">Reviewed · 6</button></div></div><div id="clean-table">${table(state.clean ? cleanTicks() : ticks, !state.clean)}</div>` +
    `<div class="two-col"><div class="prose"><h2>A traceable set of rules</h2><ul class="checklist"><li>Verify ZIP checksum & CSV schema <span>SPECIFIED</span></li><li>Deduplicate by contract + trade ID <span>SPECIFIED</span></li><li>Validate price, size & UTC timestamps <span>SPECIFIED</span></li><li>Track ordering, gaps & rejected records <span>SPECIFIED</span></li><li>Join legs using only past information <span>NOT IMPLEMENTED</span></li></ul></div><aside class="margin-note"><div class="note-label">NO LOOK-AHEAD</div><blockquote>Never borrow tomorrow’s observation to explain today’s trade.</blockquote><p>Use a backward as-of join with a declared maximum staleness. Do not silently forward-fill across gaps or contract expiry.</p></aside></div>` + pager('clean');
}
function backtest() {
  return hero('03', 'An edge must survive<br><em>the cost of trading.</em>', 'A backtest is an experiment with assumptions. This interactive illustration shows how costs change a hypothetical path—not how the strategy actually performed.') +
    `<div class="controls"><label><input id="costs" type="checkbox" ${state.costs ? 'checked' : ''}> Include costs</label><label for="fees">Fee / fill <input id="fees" type="range" min="0" max="8" step="0.5" value="${state.fees}"><output id="fees-value">${state.fees} bps</output></label><label for="slippage">Slippage / fill <input id="slippage" type="range" min="0" max="8" step="0.5" value="${state.slippage}"><output id="slippage-value">${state.slippage} bps</output></label></div>` +
    `<div id="backtest-stats"></div>` + figure('Hypothetical cumulative price-return proxy', 'Synthetic path · bps of one-leg notional · not a capital return', '<span>After selected costs</span><span class="gold">Before costs</span>') +
    `<div class="two-col"><div class="prose"><h2>Define the experiment before the result.</h2><p>The real backtest will need explicit entry and exit rules, contract selection, roll and settlement handling, position sizing, and an untouched evaluation period. These are not implemented in this draft.</p><p>This illustration deducts four fills per completed round trip across two legs. Fees and slippage are basis points per fill on a simplified constant one-leg notional; it ignores margin, variable notionals, latency, and actual fills.</p></div><aside class="margin-note"><div class="note-label">A HARDER STANDARD</div><blockquote>Positive before costs<br>is not the same as<br>profitable in practice.</blockquote><p>Costs here are user-selected scenarios, not verified exchange fees. A final result must disclose the full execution model.</p></aside></div>` + pager('backtest');
}
function findings() {
  return hero('04', 'Let the evidence<br><em>write the conclusion.</em>', 'The goal is not to prove a profitable story. It is to find out whether a defined calendar-spread strategy can support one.') +
    `<div class="verdict"><div class="note-label">CURRENT VERDICT</div><div class="verdict-title">Not established.</div><p>No cleaned market dataset or historical backtest has been connected. The visuals in this notebook cannot answer the profitability question.</p></div>` +
    `<div class="section-head"><h2>What would make the answer credible?</h2><span class="small-label">EVIDENCE STILL TO BUILD</span></div>` +
    [['01', 'A reproducible dataset', 'Archive provenance, contract lifetimes, coverage, quality reports, and a versioned cleaning pipeline.'], ['02', 'An executable strategy', 'Rules fixed before evaluation, bid/ask-aware fills, two-leg risk, costs, liquidity, settlement, and realistic capital constraints.'], ['03', 'A result that generalizes', 'Out-of-sample performance, sensitivity tests, drawdowns, uncertainty, and failure cases—not just a favorable sample.']].map(([n,t,p]) => `<div class="finding"><span>${n}</span><div><h3>${t}</h3><p>${p}</p></div></div>`).join('') +
    `<div class="two-col"><div class="prose"><h2>Research, with a paper trail.</h2><p>Future editions will replace the examples with reviewed results, publish methods alongside assumptions, and explain where the evidence is weak.</p><p>Data reference: <a href="https://github.com/binance/binance-public-data/" target="_blank" rel="noopener noreferrer">Binance public data ↗</a>. Dataset use remains subject to the source’s terms.</p></div><aside class="margin-note"><div class="note-label">PUBLICATION NOTE</div><blockquote>A living research notebook.<br>Not a completed profit claim.</blockquote><p>This local draft will later be linked from the researcher’s portfolio once it has a published address.</p></aside></div>` + pager('findings');
}
function chart(lines, labels, format, indexLabel = 'Sample day') {
  const host = document.querySelector('#research-chart');
  const W=850,H=250,L=53,R=15,T=20,B=35, n=lines[0].values.length;
  const values=lines.flatMap(l=>l.values);let min=Math.min(...values),max=Math.max(...values);const pad=(max-min)*.18 || 1;min-=pad;max+=pad;
  const x=i=>L+i/(n-1)*(W-L-R),y=v=>T+(max-v)/(max-min)*(H-T-B);
  let grid='';
  for(let j=0;j<5;j++){const v=min+(max-min)*j/4;grid+=`<line class="grid" x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}"/><text x="${L-11}" y="${y(v)+3}" text-anchor="end">${format(v)}</text>`;}
  for(let j=0;j<5;j++){const i=Math.round((n-1)*j/4);grid+=`<text x="${x(i)}" y="${H-8}" text-anchor="middle">${indexLabel === 'Sample day' ? 'Day ' : 'Trip '}${indexLabel === 'Sample day' ? i+1 : i}</text>`;}
  const paths=lines.map(l=>`<path class="plot-line" stroke="${l.color}" d="${l.values.map((v,i)=>`${i?'L':'M'}${x(i).toFixed(2)},${y(v).toFixed(2)}`).join(' ')}"/>`).join('');
  host.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${labels}. Illustrative synthetic values, not actual research results."><title>${labels}</title>${grid}${paths}<line class="crosshair" x1="${L}" x2="${L}" y1="${T}" y2="${H-B}"/><rect x="${L}" y="${T}" width="${W-L-R}" height="${H-T-B}" fill="transparent"/></svg><div class="chart-tooltip" hidden></div>`;
  const svg=host.querySelector('svg'),tooltip=host.querySelector('.chart-tooltip'),cross=host.querySelector('.crosshair');
  svg.addEventListener('pointermove',e=>{const bounds=svg.getBoundingClientRect(),px=(e.clientX-bounds.left)/bounds.width*W;const i=Math.max(0,Math.min(n-1,Math.round((px-L)/(W-L-R)*(n-1))));cross.setAttribute('x1',x(i));cross.setAttribute('x2',x(i));tooltip.textContent=`${indexLabel} ${i+1} · illustrative\n`+lines.map(l=>`${l.label}: ${format(l.values[i])}`).join('\n');tooltip.hidden=false;tooltip.style.left=Math.min(Math.max(0,e.clientX-bounds.left+10),Math.max(0,bounds.width-215))+'px';tooltip.style.top='25px';});
  svg.addEventListener('pointerleave',()=>tooltip.hidden=true);
}
function drawPrices(){const s=series.slice(-state.range);chart([{label:'Near',values:s.map(d=>d.near),color:'#315c4c'},{label:'Far',values:s.map(d=>d.far),color:'#ad8150'}],'Synthetic near and far futures prices',v=>Math.round(v).toLocaleString('en-US'));}
function drawBacktest(){
  const gross=Array.from({length:19},(_,i)=>i===0?0:i*13+Math.sin(i*.95)*27-15);
  const totalPerTrade=4*(state.fees+state.slippage);
  const net=gross.map((v,i)=>v-(state.costs?i*totalPerTrade:0));
  document.querySelector('#backtest-stats').innerHTML=stats([['DEMO GROSS',`${gross.at(-1).toFixed(0)} bps`,'Synthetic price-return proxy'],['DEMO NET',`${net.at(-1).toFixed(0)} bps`,'Same path after selected costs'],['ASSUMED ROUND TRIPS','18','Four fills each · notional-based cost model']]);
  chart([{label:'After costs',values:net,color:'#315c4c'},{label:'Before costs',values:gross,color:'#ad8150'}],'Hypothetical before and after cost comparison',v=>`${Math.round(v)}`,'Round trip');
  document.querySelector('#chart-caption').textContent='FIG. 03 — SYNTHETIC SCENARIO · UNITS: BASIS POINTS OF ONE-LEG NOTIONAL';
}
function exportSample(){
  const rows=[['trade_id','time_utc','price_usdt','quantity_btc','illustrative_taker_side'],...ticks.map(t=>[t.id,t.time,t.price.replaceAll(',',''),t.qty,t.side])];
  const url=URL.createObjectURL(new Blob([rows.map(r=>r.join(',')).join('\n')],{type:'text/csv'}));const a=document.createElement('a');a.href=url;a.download='SYNTHETIC-example-trades.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);document.querySelector('#announcement').textContent='Synthetic example CSV downloaded.';
}

const slides = [...chapters];
function introSlide() {
  return `<section class="closed-book page-enter" aria-label="Introduction slide"><div class="cover-kicker">INDEPENDENT RESEARCH / CRYPTO DERIVATIVES</div><div class="cover-number">— 001 —</div><h1>The Calendar<br>Spread</h1><p class="cover-subtitle">Can the distance between two futures<br>become a profitable trade?</p><div class="cover-rule"></div><svg class="cover-illustration" viewBox="0 0 180 75" aria-hidden="true"><path d="M10 62H170M10 10V62" fill="none" stroke="#9eae8366"/><path d="M12 51L30 40L48 46L66 29L84 34L102 20L120 28L138 15L168 8" fill="none" stroke="#d9c68c" stroke-width="1.5"/><path d="M12 59L30 49L48 51L66 39L84 42L102 31L120 36L138 26L168 22" fill="none" stroke="#b7c8a3" stroke-width="1.5"/></svg><div class="cover-author">PONLAWAT SANJAN</div><div class="cover-note">RAW DATA → CLEAN DATA → BACKTEST</div><div class="cover-note" style="margin-top:15px">DRAFT · ILLUSTRATIVE DATA ONLY</div></section>`;
}
function contentSlide(key) {
  if (key === 'overview') return `<section class="presentation-slide page-enter" aria-label="Plotting rules slide">
    <header class="slide-header"><div class="eyebrow">01 / METHOD</div><h1>From trade ticks to <em>calendar spreads.</em></h1><p class="lede">Can calendar spread arbitrage make a profit? First, define exactly how we observe the spread.</p></header>
    <div class="rule-equation"><span>Spread = far price &minus; near price</span><code>0 &le; near time &minus; far time &lt; 1,000 ms</code></div>
    <div class="rules-grid">
      <article><span>01 / PAIRS</span><h2>Same asset, different expiries</h2><p>Use all available pairs of dated contracts for the same underlying with overlapping source coverage. The earlier expiry is near; the later expiry is far.</p></article>
      <article><span>02 / MATCH</span><h2>Each near tick anchors a match</h2><p>Choose the latest far trade at or before the near timestamp. Accept ages from 0 to 999 milliseconds; reject future far ticks and ages of exactly 1,000 ms or more. A far trade may be reused.</p></article>
      <article><span>03 / CALCULATE</span><h2>Far minus near, in USDT</h2><p>Subtract the near trade price from its matched far trade price. Plot the result at the near timestamp in UTC. When far trades share a millisecond, use the highest trade ID; ordering within that millisecond is unknown.</p></article>
      <article><span>04 / DISPLAY</span><h2>Connect consecutive spread points</h2><p>Each pair gets its own line on a shared USDT scale with zero visible. Connect consecutive accepted observations; omit unmatched near ticks. The one-second matching limit does not break the line between observations.</p></article>
    </div><div class="method-example"><strong>Example</strong> Near at 12:00:00.800: 60,000 USDT. Latest far at 12:00:00.350: 60,120 USDT. Age = 450 ms &rarr; accepted spread = <strong>+120 USDT</strong>.</div>
    <footer class="slide-note">Wide views keep actual first / minimum-spread / maximum-spread / last observations per display bucket after tick matching. The website uses a saved overview; zoom enlarges these saved points. Use the Python research viewer to inspect every match in a smaller window. Trade prices are observations; execution costs and profitability remain to be tested.</footer>
  </section>`;
  if (key === 'raw') return `<section class="presentation-slide chart-slide page-enter" aria-label="Raw spread explorer slide">
    <header class="slide-header"><div class="eyebrow">02 / OBSERVE THE MARKET</div><h1>One Bitcoin. <em>Two expiry dates.</em></h1><p class="lede">How much more does a later-expiring futures contract cost? These lines show that price difference over time.</p></header>
    <div class="chart-reading-key"><span><i class="key-line"></i>Each color is a different pair of expiry dates</span><span><strong>Above zero</strong> Later contract costs more</span><span><strong>Below zero</strong> Earlier contract costs more</span></div>
    <div class="presentation-chart-shell"><div class="presentation-chart-heading"><div><h2>Bitcoin futures price differences</h2><p>Binance trade data <span aria-hidden="true">/</span> USDT per BTC</p></div><span id="viewer-status" role="status">Preparing chart...</span></div>
    <div id="viewer-unavailable" class="viewer-unavailable" hidden><strong>The chart is temporarily unavailable.</strong><p>Please try again in a moment.</p><button class="text-button" id="reload-viewer">Try again</button></div>
    <iframe id="spread-viewer" title="Bitcoin futures price differences over time" src="snapshot.html" allow="fullscreen"></iframe>
    <div class="chart-bottom-bar"><span>Hover for prices <span aria-hidden="true">/</span> Drag to move through time</span><button id="explore-chart" class="explore-button" aria-expanded="false">Explore chart</button></div></div>
    <aside class="chart-takeaway"><span>WHAT TO LOOK FOR</span><p>Watch how the difference widens and narrows. A bigger gap is a starting point for research &mdash; trading costs and the ability to buy and sell both contracts determine whether it can become a profit.</p></aside>
    <footer class="slide-note">Saved overview of matched trades. Zoom enlarges saved points; it does not reload individual ticks. The matching method is on page 1. Clean-data and backtest results are still in progress.</footer>
  </section>`;

  let left='',right='';
  if(key==='clean') {
    left=`<div class="eyebrow">02 / CLEAN DATA</div><h1>Make the data<br><em>trustworthy.</em></h1><p class="lede">Every correction needs a reason.<br>Every gap needs to stay visible.</p><div class="prose"><p>The demo table removes one duplicate trade ID and one zero-quantity row, then restores time order. This operates only on a small constructed fixture.</p></div><ul class="checklist"><li>Archive checksum & schema <span>SPECIFIED</span></li><li>Contract + trade ID deduplication <span>SPECIFIED</span></li><li>Price, quantity & UTC checks <span>SPECIFIED</span></li><li>Backward as-of join + staleness limit <span>PLANNED</span></li></ul><aside class="margin-note"><div class="note-label">NO LOOK-AHEAD</div><blockquote>Do not borrow a future<br>observation to price<br>a past decision.</blockquote></aside>${notice}`;
    right=`<h2>From records to observations.</h2>${figure('The spread, before a strategy','Synthetic far − near · USDT per BTC','<span>Calendar spread</span>')}<div class="table-toolbar"><span>Demo cleaning</span><div class="segmented"><button data-clean="false" class="${!state.clean?'selected':''}" aria-pressed="${!state.clean}">Original · 8</button><button data-clean="true" class="${state.clean?'selected':''}" aria-pressed="${state.clean}">Reviewed · 6</button></div></div><div id="clean-table">${table(state.clean?cleanTicks():ticks,!state.clean)}</div>`;
  }
  if(key==='backtest') {
    left=`<div class="eyebrow">03 / THE BACKTEST</div><h1>An edge must<br>survive <em>the cost<br>of trading.</em></h1><p class="lede">Define the experiment.<br>Then challenge its assumptions.</p><div class="prose"><p>The real backtest still needs fixed entry and exit rules, position sizing, settlement and roll handling, a two-leg fill model, and out-of-sample evaluation.</p><p>The interactive example uses 18 synthetic round trips and four fills per round trip. Costs are charged on a simplified constant one-leg notional. This is not portfolio or margin return.</p><p>Fee and slippage settings are scenarios, not verified exchange fee quotes. Bid/ask, latency, actual fills and capital constraints are not modeled here.</p></div>${notice}`;
    right=`<h2>What happens after costs?</h2><div class="controls"><label><input id="costs" type="checkbox" ${state.costs?'checked':''}> Include illustrative costs</label><label>Fee / fill <input id="fees" type="range" min="0" max="8" step="0.5" value="${state.fees}"><output id="fees-value">${state.fees} bps</output></label><label>Slippage / fill <input id="slippage" type="range" min="0" max="8" step="0.5" value="${state.slippage}"><output id="slippage-value">${state.slippage} bps</output></label></div><div id="backtest-stats"></div>${figure('Hypothetical cumulative path','Basis points of one-leg notional','<span>After costs</span><span class="gold">Before costs</span>')}<p class="figure-sub">Synthetic price-return proxy. Not historical performance.</p>`;
  }
  if(key==='findings') {
    left=`<div class="eyebrow">04 / FINDINGS & LIMITS</div><h1>Let the evidence<br><em>write the ending.</em></h1><p class="lede">The purpose is to test a claim.<br>Not to manufacture a profitable story.</p><div class="verdict"><div class="note-label">CURRENT VERDICT</div><div class="verdict-title">Not established.</div><p>Raw matched trade observations are connected locally. A reviewed dataset and historical backtest are still pending; profitability has not been established.</p></div><div class="prose"><p>Future editions will replace these illustrations with reviewed results and explain where the evidence is weak.</p><p>Data reference: <a href="https://github.com/binance/binance-public-data/" target="_blank" rel="noopener noreferrer">Binance public data ↗</a></p></div>`;
    right=`<h2>What would make<br>the answer credible?</h2>${[['01','Reproducible data','Provenance, coverage, contract lifetimes, quality reports and versioned transformations.'],['02','Executable rules','Bid/ask-aware fills, two-leg risk, costs, liquidity, capital requirements and settlement.'],['03','Robust results','Out-of-sample evaluation, sensitivity tests, uncertainty, drawdowns and failure cases.']].map(([n,t,p])=>`<div class="finding"><span>${n}</span><div><h3>${t}</h3><p>${p}</p></div></div>`).join('')}<aside class="margin-note"><div class="note-label">AN OPEN NOTEBOOK</div><blockquote>The most useful result<br>may be knowing why<br>a strategy does not work.</blockquote></aside><p class="figure-sub" style="margin-top:25px">Draft by Ponlawat Sanjan · portfolio link follows publication.</p>`;
  }
  const heading = document.createElement('template');
  heading.innerHTML = left;
  const content = document.createElement('template');
  content.innerHTML = right;
  content.content.querySelector('h2')?.remove();
  content.content.querySelectorAll('.draft-notice, .margin-note').forEach(el => el.remove());
  const verdict = heading.content.querySelector('.verdict')?.outerHTML ?? '';
  const title = heading.content.querySelector('h1').innerHTML.replaceAll('<br>', ' ');
  const lede = heading.content.querySelector('.lede').innerHTML.replaceAll('<br>', ' ');
  const eyebrow = heading.content.querySelector('.eyebrow').outerHTML;
  return `<section class="presentation-slide page-enter" aria-label="${titles[chapters.indexOf(key)]} slide"><header class="slide-header">${eyebrow}<h1>${title}</h1><p class="lede">${lede}</p></header><div class="slide-body">${verdict}${content.innerHTML}</div><footer class="slide-note">Illustrative draft. Synthetic examples only; no historical profitability result has been established.</footer></section>`;
}
function render(){
 const key=slides.includes(location.hash.slice(1))?location.hash.slice(1):'overview';const index=slides.indexOf(key);
 main.innerHTML=key==='cover'?introSlide():contentSlide(key);
 document.title=`${key==='cover'?'The Calendar Spread':titles[chapters.indexOf(key)]} — Research presentation`;
 document.querySelector('#previous-page').disabled=index===0;
 const next=document.querySelector('#next-page');next.disabled=index===slides.length-1;next.textContent='Next page';
 document.querySelector('#page-position').textContent=`Page ${index+1} of ${slides.length}`;
 document.querySelector('#page-dots').innerHTML=slides.map((p,i)=>`<span class="${i===index?'current':''}"></span>`).join('');
 if(key==='raw')connectViewer();
 if(key==='clean')chart([{label:'Spread',values:series.map(d=>d.spread),color:'#315c4c'}],'Synthetic far minus near spread',v=>Math.round(v).toString());
 if(key==='backtest')drawBacktest();
 document.querySelectorAll('[data-range]').forEach(b=>b.addEventListener('click',()=>{state.range=Number(b.dataset.range);document.querySelectorAll('[data-range]').forEach(a=>{a.classList.toggle('selected',a===b);a.setAttribute('aria-pressed',String(a===b));});drawPrices();}));
 document.querySelectorAll('[data-clean]').forEach(b=>b.addEventListener('click',()=>{state.clean=b.dataset.clean==='true';document.querySelector('#clean-table').innerHTML=table(state.clean?cleanTicks():ticks,!state.clean);document.querySelectorAll('[data-clean]').forEach(a=>{a.classList.toggle('selected',a===b);a.setAttribute('aria-pressed',String(a===b));});}));
 document.querySelector('#export-sample')?.addEventListener('click',exportSample);
 ['fees','slippage','costs'].forEach(id=>document.getElementById(id)?.addEventListener('input',e=>{state[id]=id==='costs'?e.target.checked:Number(e.target.value);if(id!=='costs')document.getElementById(id+'-value').textContent=state[id]+' bps';drawBacktest();}));
 document.querySelector('#announcement').textContent=`${titles[index]}, page ${index+1} of ${slides.length}.`;
}
async function connectViewer(){
 const frame=document.querySelector('#spread-viewer'),label=document.querySelector('#viewer-status'),error=document.querySelector('#viewer-unavailable');
 let exploring=false;
 document.querySelector('#explore-chart').onclick=e=>{
   exploring=!exploring;e.currentTarget.setAttribute('aria-expanded',String(exploring));e.currentTarget.textContent=exploring?'Back to presentation':'Explore chart';
   frame.classList.toggle('expanded',exploring);
   frame.contentWindow.postMessage({type:'spread-explore',enabled:exploring},location.origin);
 };
 frame.hidden=false;error.hidden=true;label.textContent='Opening saved chart...';
 document.querySelector('#reload-viewer').onclick=()=>{error.hidden=true;frame.hidden=false;frame.src='snapshot.html';};
}
window.addEventListener('message',e=>{
 const frame=document.querySelector('#spread-viewer');
 if(!frame||e.origin!==location.origin||e.source!==frame.contentWindow)return;
 if(e.data.type==='spread-error'){document.querySelector('#viewer-status').textContent='Chart unavailable';document.querySelector('#viewer-unavailable').hidden=false;frame.hidden=true;return;}
 if(e.data.type!=='spread-ready')return;
 document.querySelector('#viewer-status').textContent=`${e.data.pairs} expiry ${e.data.pairs===1?'pair':'pairs'} in this view`;
});
function turn(direction){const current=slides.includes(location.hash.slice(1))?slides.indexOf(location.hash.slice(1)):0;const target=current+direction;if(target>=0&&target<slides.length)location.hash=slides[target];}
 document.querySelector('#previous-page').addEventListener('click',()=>turn(-1));
 document.querySelector('#next-page').addEventListener('click',()=>turn(1));
 document.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)||e.target.isContentEditable||e.altKey||e.ctrlKey||e.metaKey)return;if(e.key==='ArrowRight'){e.preventDefault();turn(1);}if(e.key==='ArrowLeft'){e.preventDefault();turn(-1);}});
 window.addEventListener('hashchange',()=>{render();window.scrollTo({top:0,behavior:'instant'});});render();
