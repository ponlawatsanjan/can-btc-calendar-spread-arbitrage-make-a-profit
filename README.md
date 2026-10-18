# Can BTC Calendar Spread Arbitrage Make a Profit?

Research into Bitcoin futures calendar spreads, from individual trade observations through data validation to a planned execution-aware backtest. Profitability has not been established.

## Standalone interactive raw chart

Run `Start Raw Tick Viewer.cmd`, or `.\.venv-raw-viewer\Scripts\python.exe plot_raw_ticks.py`. All downloaded contracts appear on one interactive chart with zoom/pan, hover detail, visibility controls and automatic detail reloads. Wide windows are explicitly sampled for display; narrow windows show exact ticks. See `RAW_VIEWER.md`. This viewer is separate from the draft project website.

## Research website draft

The paginated research presentation is in `website/`. With Node.js installed, double-click `Start Research Notebook.cmd`, then open http://127.0.0.1:5180. See [website/README.md](website/README.md) for details. Page 1 explains the matching method; page 2 shows saved real spread observations for all 25 pairs with accepted matches. Zoom and hover work in the browser without Python. Clean-data and backtest pages remain labeled synthetic drafts.

Refresh the saved chart after adding tick data with `python export_website_chart.py`. Install `requirements-viewer.txt` first if the isolated local environment is unavailable. The website includes a compact sampled chart snapshot, not the full raw dataset. Zoom enlarges saved observations; use the Python viewer for original-tick detail.

Downloads original **individual trades** (`trades`, not `aggTrades` or candles) for Binance USD-M futures. Python 3.10+; no packages or API key required.

## Run yourself

For **all BTCUSDT dated quarterly contracts** with published tick archives in your date range:

```powershell
python download_ticks.py --quarterly BTCUSDT --start 2026-09-01 --end 2026-09-30 --extract
```

For **every archived USD-M futures symbol**, including other coins, perpetuals and dated contracts:

```powershell
python download_ticks.py --all-symbols --start 2026-09-01 --end 2026-09-30 --extract
```

All-symbol downloads can be large. These modes discover historical symbols from the public archive, including delisted symbols, and schedule only published daily ZIPs within the date range. They do not infer complete coverage from a listing; inspect the per-file download report and later validate tick coverage. `--quarterly ETHUSDT` selects another base. Neither mode is limited to currently active exchange symbols.

To select contracts explicitly:

```powershell
cd D:\Workspace\EM_Github\Calendar_Spread_Arbitrage
python download_ticks.py --symbols BTCUSDT_260925 BTCUSDT_261225 --start 2026-09-01 --end 2026-09-24 --extract
```

Change the symbols/dates to your research period. Dates are inclusive UTC. This example avoids the near contract's September 25 expiry day. Choose dates within each contract's listed lifetime.

Add `--dry-run` to preview URLs without downloading trade data or writing files. Discovery modes still read the archive's directory listings; explicit `--symbols` dry runs need no network. Downloads only happen when you run the command without `--dry-run`.

Files go to `data/ticks/<symbol>/`: daily ZIPs, official `.CHECKSUM` files, and original CSVs with `--extract`. Use `--output D:\MarketData\ticks` to change this location. Each run writes a timestamped JSON report listing successes, missing archives and failures.

The downloader streams archives to disk, retries transient failures, verifies SHA-256 checksums and skips verified existing ZIPs. Interrupted files restart from the beginning. Corrupt existing ZIPs are reported without replacement. Missing archives fail the run unless you deliberately add `--skip-missing`; missing files remain recorded in the report. Other failures always produce a nonzero exit. Run one instance per output folder at a time.

## Extract already downloaded ZIPs separately

```powershell
python extract_ticks.py
```

Recursively finds tick-trade ZIPs under `data/ticks` and writes CSVs beside them. It preserves ZIPs, verifies SHA-256 when a `.CHECKSUM` file is present, and checks ZIP member CRC during extraction. Without a checksum file, only ZIP integrity is checked. Existing CSVs are validated by size/CRC before being skipped; use `--overwrite` to replace them. Failures are recorded in a timestamped JSON report and produce a nonzero exit code.

Use `--input D:\MarketData\ticks` for another directory, or `--dry-run` to preview without changing files. Run after the downloader finishes, and run one extractor per folder at a time. The extraction script makes no network requests.

## Data scope

USD-M trade fields: trade ID, price, quantity, quote quantity, timestamp in milliseconds and buyer-is-maker. CSVs are preserved as published, including any header. There is no resampling, merging, forward filling or backtesting.

Trade ticks are observed executions, not executable bid/ask quotes. They cannot establish simultaneous fills in both legs. A realistic execution model also needs historical quotes/depth, latency, fees, liquidity and settlement/roll rules. This script downloads trade archives only.

Source and schema: [Binance public data](https://github.com/binance/binance-public-data/). Attribution: Binance Vision. Usage is governed by the [dataset terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md). Data files are excluded from Git.
