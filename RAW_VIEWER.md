# Standalone raw tick explorer

## Near/far matched ticks, strict age below one second

```powershell
python plot_raw_ticks.py --matched --start 2021-03-16 --end 2021-03-16
```

This opens a separate matched-tick viewer on port **5191**. Remove the dates for the entire available history (the first query may be expensive). The running preview now defaults to the complete available history. Use the From/To controls to inspect another window.

Loading shows a live percentage, current pair, UTC day, completed/total pair-days and elapsed time. The percentage measures completed pair-day work units, not a time estimate; cached pairs can advance it quickly. A separate state reports waiting for another request or transferring/rendering a completed result. Changing the window requests cancellation of the previous job at the next daily checkpoint. Completed per-pair caches remain reusable. Progress is polled per request, so one tab does not display another tab's job.

For every valid **near** tick, select the **latest valid far tick at or before the near timestamp**. Accept only `0 <= near_time - far_time < 1000 ms`. Exactly 1000 ms and future far ticks are rejected; unmatched near ticks are omitted and counted. A far tick may match several near ticks. The previous day's final 999 ms are included for correct matching across midnight.

The initial chart plots **spread lines without dot markers**: `far_price - near_price`, anchored to the near timestamp. Hover shows both leg prices, original timestamps, trade IDs and match age. All spreads share one USDT y-axis with a visible zero reference; no independent scaling, normalization or rebasing is applied. Uncheck Line chart for points only. The Plot selector can optionally show matched near/far prices instead. Every same-underlying dated-symbol combination with overlapping downloaded source days is considered as a near/far pair; this is not a dynamic continuous-contract roll rule. Restrict `--symbols NEAR FAR` to explicitly select one pair.

Lines connect each displayed accepted spread observation to the next one for the same pair. The strict sub-second threshold determines which near/far ticks may form a spread; it does not limit the time between consecutive spread observations. Unmatched near ticks are omitted, without inserting extra line breaks. Separate pairs remain separate traces. Connecting lines are visual guides, not forward-filled data rows or executable prices.

At a shared far millisecond, the highest far trade ID is used as a deterministic tie-break. Millisecond data cannot establish sub-millisecond ordering relative to a same-time near trade. This is historical trade matching, not evidence of simultaneous executable quotes or fills.

Matching runs on original valid ticks **before** display sampling. Wide windows select first/minimum-spread/maximum-spread/last accepted matches per display bucket and are labeled sampled. Zoom for every match. Price-mode overview selection uses those same spread-selected matched rows, not independent price extrema. Full-history matching is processed in UTC daily chunks to bound working memory. Daily quality counts can include repeated far carry-in source files. The separate matched cache is `.cache/matched-viewer/`. Original CSVs and the project website are unchanged.

`plot_raw_ticks.py` runs a separate local interactive viewer. It does not change or connect to `website/`. All extracted contract symbols are shown on one price chart by default. "Pair" here means each downloaded futures contract symbol; the viewer does not construct synthetic near/far combinations or spread prices.

## Run

On this computer, use the prepared isolated environment:

```powershell
cd D:\Workspace\EM_Github\Calendar_Spread_Arbitrage
python plot_raw_ticks.py
```

The script opens a browser tab at http://127.0.0.1:5190. Keep Python running; Ctrl+C stops it. This is an interactive chart rendered by the Python viewer, not a PNG or integration into your project site. No external chart service or CDN is needed at runtime.

Your default Python 3.15 is preserved. If its dependencies are unavailable, the script automatically runs through the prepared `.venv-raw-viewer` environment using a project-local Python 3.13 runtime. You can also double-click `Start Raw Tick Viewer.cmd`, or invoke `.\.venv-raw-viewer\Scripts\python.exe` explicitly. Start only one viewer on port 5190 at a time.

For another machine, use Python 3.13 (or a version with DuckDB binary wheels):

```powershell
python -m pip install -r requirements-viewer.txt
python plot_raw_ticks.py
```

Optional initial window/subset:

```powershell
.\.venv-raw-viewer\Scripts\python.exe plot_raw_ticks.py --start 2021-03-16 --end 2021-03-16
.\.venv-raw-viewer\Scripts\python.exe plot_raw_ticks.py --symbols BTCUSDT_260925 BTCUSDT_261225 --start 2026-09-01 --end 2026-09-24
```

`--start` and `--end` are inclusive UTC dates for the initial view. The chart's exact From/To controls use an exclusive end timestamp. Full history resets to the configured initial date window. `--input` changes the CSV directory; `--port` changes the port; `--no-browser` starts without opening a tab. Discovery occurs at startup, so restart after extracting more files.

## Explore

- Scroll to zoom; drag to pan; the Plotly toolbar also provides box zoom and reset.
- Zooming the time axis automatically queries the original daily CSVs again.
- Hover shows UTC milliseconds, contract, trade price, quantity, trade ID and aggressor side.
- Click legend items or use sidebar checkboxes to hide/show contracts. Double-click a legend to isolate it. Filter names with the search box.
- Change the display budget, choose UTC timestamps, or select the last available day.
- Line charts are displayed by default. Uncheck Line chart to switch to individual points. Lines connect displayed observations as a visual guide; they are not observed prices between trades.
- Lines never cross missing source-file days. In exact detail, gaps over five minutes without trades also break the line. In sampled overviews, the interval cutoff is the larger of five minutes and two sampling buckets, so display sampling alone does not create false gaps. Zoom in to inspect shorter intraday gaps. This identifies absent observations, not the cause of the absence (quiet trading versus a feed gap).

## Raw data and display sampling

The first full-history view can take time: your current data include thousands of daily CSVs. Progress prints per contract in Python. File names select the appropriate UTC days before scanning rows. Display responses are cached under `.cache/raw-viewer/`, keyed by source paths, sizes, modification times, window and point budget. Source CSVs and ZIPs are never rewritten.

Wide windows use first/lowest/highest/last **actual trade observations** per time bucket, not generated OHLC bars or resampled candle closes. This is explicitly labeled **SAMPLED OVERVIEW**. When a contract's valid trade count fits the point budget, the viewer returns every tick in that window, including same-time records, and reports **EXACT DETAIL** only if all returned contracts are exact. A maximum of 100,000 points per contract can be requested. Use a narrower window for full tick-level detail.

Documented six-column USD-M trade CSVs are read directly. Optional headers are recognized. Unparseable, non-finite, nonpositive price/quantity or invalid maker-flag records are excluded from plotting and counted in the displayed quality note. That count covers entire daily files touched by the query, not only the zoom window. Structural CSV errors stop the query visibly. No deduplication or forward filling is performed in exact mode. Overview selection may collapse duplicate time/ID records; inspect exact mode for duplicate detail.

All symbols share one price axis: compare same-underlying contracts for meaningful absolute price comparisons. Trade ticks are executions, not synchronized executable quotes. This is a data-inspection tool, not a spread strategy, cleaned dataset or backtest.
