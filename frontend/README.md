# AlphaWalker Frontend

React dashboard for the AlphaWalker multi-agent investment research system.

## Setup

```bash
npm install
npm run dev       # starts at http://localhost:5173 (or --port 3000)
npm run build     # production build to dist/
```

Expects the AlphaWalker API running at `http://localhost:8000`.

## Tabs

| Tab | Description |
|---|---|
| **Dashboard** | Compact verdict cards for all analyzed tickers, color-coded by verdict (green/yellow/red). Expandable to show rationale. |
| **Analysis** | Full breakdown per ticker: bull/bear confidence bar chart, judge confidence radial gauge, expandable argument panels, and historical confidence trend chart. |
| **History** | Past analysis runs pulled from the Insforge cloud database, with drill-down into per-ticker verdicts. |

## Tech Stack

- React 19 + Vite 8
- Recharts for data visualization (bar charts, line charts, radial gauges)
- `@insforge/sdk` for cloud database reads (History tab, confidence trends)
- Single-file architecture (`src/App.jsx`)

## Environment

The API base URL is hardcoded to `http://localhost:8000` in `App.jsx`. For production deployments, update this or introduce an environment variable.
