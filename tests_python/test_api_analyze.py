"""Tests for synchronous /v1/analyze-tickers and /analyze endpoints."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

import jaclang  # noqa: F401 — enables api.main from .jac

from fastapi.testclient import TestClient


class AnalyzeTickersApiTests(unittest.TestCase):
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

    @patch("api.main.run_jac_pipeline")
    def test_analyze_tickers_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = [
            {
                "ticker": "NVDA",
                "verdict": "hold",
                "judge_confidence": 85,
                "rationale": "reason",
                "condition": "",
                "bull_argument": "b",
                "bull_confidence": 60,
                "bear_argument": "e",
                "bear_confidence": 55,
            }
        ]
        client = TestClient(self._main.app)
        r = client.post("/v1/analyze-tickers", json={"tickers": ["nvda"]})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(len(body["data"]), 1)
        row = body["data"][0]
        self.assertEqual(row["ticker"], "NVDA")
        self.assertEqual(row["confidence"], 85)
        self.assertEqual(row["judge_confidence"], 85)
        self.assertEqual(row["verdict"], "hold")
        mock_run.assert_called_once_with(["NVDA"])

    def test_analyze_tickers_empty_returns_400(self) -> None:
        client = TestClient(self._main.app)
        r = client.post("/v1/analyze-tickers", json={"tickers": ["", "   "]})
        self.assertEqual(r.status_code, 400)

    @patch("api.main.run_jac_pipeline")
    def test_analyze_alias_matches_v1(self, mock_run: MagicMock) -> None:
        mock_run.return_value = [
            {
                "ticker": "AAPL",
                "verdict": "buy",
                "judge_confidence": 70,
                "rationale": "x",
                "condition": "c",
                "bull_argument": "",
                "bull_confidence": 0,
                "bear_argument": "",
                "bear_confidence": 0,
            }
        ]
        client = TestClient(self._main.app)
        r = client.post("/analyze", json={"tickers": ["aapl"]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"][0]["ticker"], "AAPL")

    @patch("api.main.run_jac_pipeline")
    def test_pipeline_failure_returns_502(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = RuntimeError("Jac worker failed")
        client = TestClient(self._main.app)
        r = client.post("/v1/analyze-tickers", json={"tickers": ["MSFT"]})
        self.assertEqual(r.status_code, 502)

    def test_requires_api_key_when_configured(self) -> None:
        self._main.API_KEY = "secret-key"
        client = TestClient(self._main.app)
        r = client.post("/v1/analyze-tickers", json={"tickers": ["X"]})
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
