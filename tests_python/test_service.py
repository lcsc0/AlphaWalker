"""Tests for AlphaWalker service-layer behavior."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from api.models import AnalysisOptions, AnalysisRequest, ClientContext, Holding, PortfolioInput
from api.service import AnalysisService
from api.storage import RunStorage


class AnalysisServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "runs.db"
        self.storage = RunStorage(str(db_path))
        self.service = AnalysisService(self.storage)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_submit_normalizes_duplicate_tickers_and_weights(self) -> None:
        request = AnalysisRequest(
            portfolio=PortfolioInput(
                holdings=[
                    Holding(ticker="aapl", weight=0.2),
                    Holding(ticker="AAPL", weight=0.2),
                    Holding(ticker="MSFT", weight=0.3),
                ],
                as_of_date="2026-04-04",
            ),
            options=AnalysisOptions(),
            client_context=ClientContext(),
        )

        run = self.service.submit_run(request)
        stored = self.storage.get_run(run.run_id)

        assert stored is not None
        self.assertEqual(stored.portfolio_summary.holdings_count, 2)
        self.assertAlmostEqual(stored.portfolio_summary.total_weight, 1.0, places=5)
        self.assertEqual([item["ticker"] for item in stored.normalized_holdings], ["AAPL", "MSFT"])

    def test_completed_run_persists_result_and_events(self) -> None:
        request = AnalysisRequest(
            portfolio=PortfolioInput(
                holdings=[
                    Holding(ticker="NVDA", weight=0.6),
                    Holding(ticker="TSLA", weight=0.4),
                ],
                as_of_date="2026-04-04",
            )
        )

        submitted = self.service.submit_run(request)

        deadline = time.time() + 5
        run = None
        while time.time() < deadline:
            run = self.storage.get_run(submitted.run_id)
            if run is not None and run.status in {"completed", "failed"}:
                break
            time.sleep(0.05)

        assert run is not None
        self.assertEqual(run.status, "completed")
        self.assertIsNotNone(run.result)
        self.assertIn("graph", run.result)

        events, _ = self.service.get_events(submitted.run_id)
        self.assertGreaterEqual(len(events), 4)
        self.assertEqual(events[-1].stage, "completed")

    def test_recover_marks_incomplete_runs_failed(self) -> None:
        request = AnalysisRequest(
            portfolio=PortfolioInput(
                holdings=[Holding(ticker="AAPL", weight=1.0)],
                as_of_date="2026-04-04",
            )
        )
        submitted = self.service.submit_run(request)
        self.storage.update_run(submitted.run_id, status="running", progress=0.4)

        count = self.service.recover_incomplete_runs()
        run = self.storage.get_run(submitted.run_id)

        self.assertEqual(count, 1)
        assert run is not None
        self.assertEqual(run.status, "failed")
        self.assertEqual(run.error["code"], "run_interrupted")


if __name__ == "__main__":
    unittest.main()
