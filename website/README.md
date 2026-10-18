# Calendar spread research presentation

Run `npm.cmd run dev` in this folder and open http://127.0.0.1:5180.
The website is static: it does not start Python, read tick CSVs, or call the research API. The chart uses saved real trade matches in `data/spreads.json` with a local Plotly bundle in `vendor/`. These files must be included when publishing the website.

1. Plotting rules and a worked example.
2. Saved interactive raw spread overview, all qualifying pairs. Hover, zoom, date selection and pair visibility run entirely in the browser.
3. Clean data: synthetic draft.
4. Backtest: hypothetical cost illustration, not historical performance.
5. Findings: profitability remains unestablished.

## Refresh the saved chart

From the project root, run:

```powershell
python export_website_chart.py
```

This is an author-only preparation step. It reuses the matched viewer cache where available; new data may take time to process. The default is 6,000 display points per pair across the full history. Matching always uses original ticks first, then keeps first/minimum-spread/maximum-spread/last observations per bucket. The actual number saved can be much smaller when a contract covers only a small portion of the full date range. All pairs with accepted matches are included.

The snapshot records generation time, coverage, matching method, display budget, total match counts and whether each pair was sampled. Rows retain original near timestamps, far-minus-near spread and both leg prices. Zooming magnifies the saved observations; it does not retrieve omitted ticks. Use `python plot_raw_ticks.py --matched` for original-tick research detail.

The static preview server uses gzip for assets. Initial browser rendering and downloading still take a moment, but never trigger raw-data processing. Changes to local CSVs appear on the website only after rerunning the export. No public deployment has been made.
