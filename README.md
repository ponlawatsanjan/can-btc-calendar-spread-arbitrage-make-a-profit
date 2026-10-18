# Can BTC Calendar Spread Arbitrage Make a Profit?

An interactive research presentation exploring the price difference between Bitcoin futures contracts with different expiry dates.

**[View the website](https://ponlawatsanjan.github.io/can-btc-calendar-spread-arbitrage-make-a-profit/)**

## Explore the project

1. **The method** - how trades from earlier- and later-expiring contracts are matched.
2. **The market** - an interactive chart of real trade-based spreads across 25 expiry pairs, with zoom, hover details and pair selection.
3. **Data validation** - an illustrative draft of the cleaning stage.
4. **The backtest** - a hypothetical cost illustration, with historical testing still to come.
5. **Findings** - the evidence needed to answer the research question.

Profitability has not been established. The raw spread chart uses real observations; the cleaning and backtest examples remain clearly labeled illustrations.

## How the chart works

Each near-contract trade is matched with the latest far-contract trade at or before its timestamp, provided the far trade is less than one second old:

```text
0 <= near time - far time < 1,000 milliseconds
Spread = far price - near price
```

Each line connects consecutive accepted observations for one expiry pair. The chart uses a saved, sampled overview of matched trades. Zoom enlarges saved points; it does not fetch omitted ticks or run calculations on a server. A spread between trade prices does not establish that both legs could be executed together or at a profit.

Data source: [Binance public trade archives](https://github.com/binance/binance-public-data/). Dataset use is subject to the [source terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md).

## Website source

This repository contains the presentation website, saved chart data and deployment workflow. It uses HTML, CSS, JavaScript and Plotly. Visitors do not need Python, an API key or an account. Research scripts and full raw datasets are maintained outside this repository's current files.

- `website/` - presentation pages and styles.
- `website/data/spreads.json` - prepared spread observations and data provenance.
- `website/vendor/plotly.min.js` - bundled chart library.
- `.github/workflows/pages.yml` - publishes `website/` to GitHub Pages when website changes are pushed to `main`.

## Preview locally

With Node.js installed:

```sh
cd website
npm run dev
```

Open http://127.0.0.1:5180. No package installation or build step is required. Any static web server can also serve the `website/` directory.
