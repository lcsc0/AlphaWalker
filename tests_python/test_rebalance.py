"""Tests for POST /v1/rebalance endpoint."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

import jaclang  # noqa: F401

from fastapi.testclient import TestClient


class RebalanceApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_key = os.environ.get("ALPHAWALKER_API_KEY")
        os.environ["ALPHAWALKER_API_KEY"] = ""
        import api.main as main_mod

        self._main = main_mod
        main_mod.API_KEY = ""

    def tearDown(self) -> None:
        self._main.API_KEY = ""
        if self._prev_key is None:
            os.environ.pop("ALPHAWALKER_API_KEY", None)
        else:
            os.environ["ALPHAWALKER_API_KEY"] = self._prev_key

    @patch("api.main.run_rebalance")
    def test_rebalance_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = {
            "gap_summary": "Portfolio is concentrated in semiconductors.",
            "picks": [
                {
                    "ticker": "XLP",
                    "asset_type": "ETF",
                    "gap_addressed": "adds defensive exposure",
                    "rationale": "Consumer staples provide ballast.",
                    "fit_score": 82,
                    "signals": {"price": 79.4, "rsi_14": 48.2},
                }
            ],
        }
        client = TestClient(self._main.app)
        r = client.post(
            "/v1/rebalance",
            json={
                "tickers": ["NVDA", "AMD"],
                "portfolio_annotation": {
                    "correlated_theme": "AI capex",
                    "hedging_gaps": "no defensive exposure",
                    "portfolio_conviction": "concentrated",
                },
                "results": [],
            },
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["data"]["gap_summary"], "Portfolio is concentrated in semiconductors.")
        self.assertEqual(len(body["data"]["picks"]), 1)
        self.assertEqual(body["data"]["picks"][0]["ticker"], "XLP")

    def test_rebalance_empty_tickers_returns_400(self) -> None:
        client = TestClient(self._main.app)
        r = client.post(
            "/v1/rebalance",
            json={
                "tickers": [],
                "portfolio_annotation": {},
                "results": [],
            },
        )
        self.assertEqual(r.status_code, 400)

    @patch("api.main.run_rebalance")
    def test_rebalance_agent_failure_returns_502(self, mock_run: MagicMock) -> None:
        mock_run.return_value = None
        client = TestClient(self._main.app)
        r = client.post(
            "/v1/rebalance",
            json={
                "tickers": ["NVDA"],
                "portfolio_annotation": {"hedging_gaps": "none"},
                "results": [],
            },
        )
        self.assertEqual(r.status_code, 502)

    @patch("api.main.run_rebalance")
    def test_rebalance_passes_annotation_to_bridge(self, mock_run: MagicMock) -> None:
        mock_run.return_value = {"gap_summary": "ok", "picks": []}
        client = TestClient(self._main.app)
        client.post(
            "/v1/rebalance",
            json={
                "tickers": ["TSLA"],
                "portfolio_annotation": {
                    "correlated_theme": "EV theme",
                    "hedging_gaps": "no bonds",
                    "portfolio_conviction": "mixed",
                },
                "results": [],
            },
        )
        call_kwargs = mock_run.call_args
        annotation_arg = call_kwargs[0][1]
        self.assertEqual(annotation_arg["hedging_gaps"], "no bonds")
        self.assertEqual(annotation_arg["correlated_theme"], "EV theme")


if __name__ == "__main__":
    unittest.main()
