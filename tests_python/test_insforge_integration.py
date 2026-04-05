"""Integration tests for InsforgeClient wiring in AnalysisService."""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call

from api.models import AnalysisOptions, AnalysisRequest, ClientContext, Holding, PortfolioInput
from api.service import AnalysisService
from api.storage import RunStorage


class InsforgeIntegrationTests(unittest.TestCase):
    """Verify AnalysisService calls InsforgeClient at the right moments."""

    def setUp(self) -> None:
        self._prev_use_jac = os.environ.get("ALPHAWALKER_USE_JAC")
        os.environ["ALPHAWALKER_USE_JAC"] = "0"
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "runs.db"
        self.storage = RunStorage(str(db_path))
        self.insforge = MagicMock()
        self.insforge.insert_analysis_run.return_value = {"id": "fake-uuid-1234"}
        self.service = AnalysisService(self.storage, insforge=self.insforge)

    def tearDown(self) -> None:
        self.service.shutdown()
        if self._prev_use_jac is None:
            os.environ.pop("ALPHAWALKER_USE_JAC", None)
        else:
            os.environ["ALPHAWALKER_USE_JAC"] = self._prev_use_jac
        self.temp_dir.cleanup()

    def _make_request(self, tickers: list[tuple[str, float]] | None = None) -> AnalysisRequest:
        if tickers is None:
            tickers = [("AAPL", 0.6), ("MSFT", 0.4)]
        return AnalysisRequest(
            portfolio=PortfolioInput(
                holdings=[Holding(ticker=t, weight=w) for t, w in tickers],
                as_of_date="2026-04-04",
            ),
            options=AnalysisOptions(),
            client_context=ClientContext(),
        )

    def _wait_for_completion(self, run_id: str, timeout: float = 5.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            run = self.storage.get_run(run_id)
            if run is not None and run.status in {"completed", "failed"}:
                return
            time.sleep(0.05)
        raise TimeoutError(f"Run {run_id} did not finish within {timeout}s")

    # ---- submit_run tests ----

    def test_submit_run_calls_insert_analysis_run(self) -> None:
        submitted = self.service.submit_run(self._make_request())

        self.insforge.insert_analysis_run.assert_called_once()
        call_args = self.insforge.insert_analysis_run.call_args[0][0]
        self.assertEqual(sorted(call_args["tickers"]), ["AAPL", "MSFT"])
        self.assertEqual(call_args["status"], "queued")
        self.assertEqual(call_args["results"], {})

    def test_submit_run_stores_insforge_id(self) -> None:
        """After submit, the service should track the Insforge UUID internally."""
        submitted = self.service.submit_run(self._make_request())
        self.assertIn(submitted.run_id, self.service._insforge_ids)
        self.assertEqual(self.service._insforge_ids[submitted.run_id], "fake-uuid-1234")

    # ---- completed run tests ----

    def test_completed_run_updates_insforge_statuses_and_inserts_verdicts(self) -> None:
        submitted = self.service.submit_run(self._make_request())
        self._wait_for_completion(submitted.run_id)

        run = self.storage.get_run(submitted.run_id)
        self.assertEqual(run.status, "completed")

        # Should have update calls for "running" and "completed"
        update_calls = self.insforge.update_analysis_run.call_args_list
        self.assertGreaterEqual(len(update_calls), 2)

        # First update: status -> running
        first_update = update_calls[0]
        self.assertEqual(first_update[0][0], "fake-uuid-1234")
        self.assertEqual(first_update[0][1]["status"], "running")

        # Second update: status -> completed with results
        second_update = update_calls[1]
        self.assertEqual(second_update[0][0], "fake-uuid-1234")
        self.assertEqual(second_update[0][1]["status"], "completed")
        self.assertIn("results", second_update[0][1])

        # Should insert ticker verdicts
        self.insforge.insert_ticker_verdicts.assert_called_once()
        verdicts = self.insforge.insert_ticker_verdicts.call_args[0][0]
        self.assertIsInstance(verdicts, list)
        self.assertGreater(len(verdicts), 0)

        # Each verdict should have run_id and correct fields
        for v in verdicts:
            self.assertEqual(v["run_id"], "fake-uuid-1234")
            self.assertIn("ticker", v)
            self.assertIn("verdict", v)
            self.assertIn("judge_confidence", v)
            self.assertIn("rationale", v)
            self.assertIn("bull_confidence", v)
            self.assertIn("bear_confidence", v)
            self.assertIn("bull_argument", v)
            self.assertIn("bear_argument", v)
            self.assertIn("condition", v)

        # Should clean up _insforge_ids
        self.assertNotIn(submitted.run_id, self.service._insforge_ids)

    # ---- insforge=None tests ----

    def test_no_insforge_calls_when_client_is_none(self) -> None:
        service_no_insforge = AnalysisService(self.storage)
        self.assertIsNone(service_no_insforge.insforge)
        try:
            submitted = service_no_insforge.submit_run(self._make_request())
            self._wait_for_completion(submitted.run_id)

            run = self.storage.get_run(submitted.run_id)
            self.assertEqual(run.status, "completed")
        finally:
            service_no_insforge.shutdown()

    def test_no_insforge_calls_when_none_submit_only(self) -> None:
        """A service with insforge=None should not error on submit."""
        service_no_insforge = AnalysisService(self.storage)
        try:
            submitted = service_no_insforge.submit_run(self._make_request())
            self.assertIsNotNone(submitted.run_id)
            self.assertEqual(submitted.status, "queued")
        finally:
            service_no_insforge.shutdown()

    # ---- failed run tests ----

    def test_failed_run_updates_insforge_status_to_failed(self) -> None:
        """When the engine raises, Insforge should be updated to 'failed'."""
        mock_engine = MagicMock()
        mock_engine.analyze.side_effect = RuntimeError("boom")

        service = AnalysisService(self.storage, engine=mock_engine, insforge=self.insforge)
        # Reset mock counts from any prior calls
        self.insforge.reset_mock()
        self.insforge.insert_analysis_run.return_value = {"id": "fail-uuid-5678"}

        try:
            submitted = service.submit_run(self._make_request())
            self._wait_for_completion(submitted.run_id)

            run = self.storage.get_run(submitted.run_id)
            self.assertEqual(run.status, "failed")

            # Check running + failed updates
            update_calls = self.insforge.update_analysis_run.call_args_list
            self.assertGreaterEqual(len(update_calls), 2)

            statuses = [c[0][1]["status"] for c in update_calls]
            self.assertIn("running", statuses)
            self.assertIn("failed", statuses)

            # Should NOT insert ticker verdicts on failure
            self.insforge.insert_ticker_verdicts.assert_not_called()

            # Should clean up
            self.assertNotIn(submitted.run_id, service._insforge_ids)
        finally:
            service.shutdown()

    def test_insert_returns_none_no_crash(self) -> None:
        """If insert_analysis_run returns None, the service should not crash."""
        self.insforge.insert_analysis_run.return_value = None

        service = AnalysisService(self.storage, insforge=self.insforge)
        try:
            submitted = service.submit_run(self._make_request())
            self._wait_for_completion(submitted.run_id)

            run = self.storage.get_run(submitted.run_id)
            self.assertEqual(run.status, "completed")

            # No updates should happen since we have no Insforge ID
            self.insforge.update_analysis_run.assert_not_called()
            self.insforge.insert_ticker_verdicts.assert_not_called()
        finally:
            service.shutdown()


if __name__ == "__main__":
    unittest.main()
