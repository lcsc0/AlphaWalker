# Base44 Integration Assets

This folder contains the app-facing pieces for the AlphaWalker x Base44 flow.

## What to create in Base44

Create these entities:

- `AnalysisRun`
- `AnalysisEvent`
- `PortfolioSnapshot`

Recommended fields:

- `AnalysisRun`: `run_id`, `status`, `user_id`, `portfolio_name`, `holdings_count`, `submitted_input`, `result`, `error`, `created_date`, `updated_date`, `completed_date`
- `AnalysisEvent`: `run_id`, `analysis_run_id`, `seq`, `agent`, `stage`, `message`, `event_time`
- `PortfolioSnapshot`: `analysis_run_id`, `holdings`, `source_type`, `raw_csv_file_url`

## Secrets

Configure these Base44 secrets:

- `ALPHAWALKER_API_BASE_URL`
- `ALPHAWALKER_API_KEY`

## Backend functions

Use the templates in `functions/`:

- `submitPortfolioAnalysis.ts`
- `syncPortfolioAnalysisRun.ts`

## Suggested app prompt

Prompt Base44 with:

> Build a portfolio analysis dashboard for AlphaWalker. Users can enter stock tickers and weights manually or upload a CSV. On submit, call the `submitPortfolioAnalysis` backend function, redirect to a live analysis page, poll `syncPortfolioAnalysisRun` every 2-3 seconds, show a real-time agent activity feed, then render overall risk, per-holding risk and sentiment, rebalancing suggestions, and a run history view.
