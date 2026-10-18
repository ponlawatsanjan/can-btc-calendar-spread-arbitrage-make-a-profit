# Website source

Live presentation: https://ponlawatsanjan.github.io/can-btc-calendar-spread-arbitrage-make-a-profit/

This folder is a complete static website: HTML, CSS, JavaScript, bundled Plotly and prepared chart data. It has no Python dependency or research API.

## Local preview

Run `npm run dev` in this folder, then open http://127.0.0.1:5180. Node.js is needed only for this optional preview server. No dependencies or build step are required.

## Chart data

`snapshot.html` and `snapshot.js` render `data/spreads.json` entirely in the browser. The saved dataset includes 25 expiry pairs with accepted trade matches. Hover, zoom, date selection and pair visibility work without a backend.

The dataset records generation time, coverage, matching method, display budget, total match counts and sampling flags. Rows retain original near timestamps, far-minus-near spread and both leg prices. The saved overview selects first/minimum-spread/maximum-spread/last observations per time bucket after matching. Zooming does not retrieve omitted observations.

To update the published chart, replace `data/spreads.json` with a newly prepared dataset in the same format and push it to `main`. Data preparation happens separately from the website. Include all saved-data and vendor files in deployments.

## Deployment

The repository's GitHub Actions workflow publishes this folder to GitHub Pages. All asset links are relative so the presentation works under the repository URL. Clean-data and backtest pages are still illustrative drafts; no historical profitability result has been established.
