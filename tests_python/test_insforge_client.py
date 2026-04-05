"""Tests for InsforgeClient — all HTTP calls mocked."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from api.insforge_client import InsforgeClient


class InsforgeClientTests(unittest.TestCase):

    def setUp(self) -> None:
        self.client = InsforgeClient(
            base_url="https://test.us-east.insforge.app",
            service_key="sk_test_key",
        )

    def tearDown(self) -> None:
        self.client.close()

    @patch("httpx.Client.post")
    def test_insert_analysis_run_returns_created_row(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = [
            {"id": "abc-123", "tickers": ["NVDA"], "status": "queued"}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.client.insert_analysis_run({
            "tickers": ["NVDA"],
            "status": "queued",
            "results": {},
        })

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "abc-123")
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn("analysis_runs", call_args[0][0])

    @patch("httpx.Client.patch")
    def test_update_analysis_run_sends_patch(self, mock_patch: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_patch.return_value = mock_response

        self.client.update_analysis_run("abc-123", {"status": "completed"})

        mock_patch.assert_called_once()
        call_args = mock_patch.call_args
        self.assertIn("analysis_runs", call_args[0][0])
        self.assertIn("id=eq.abc-123", call_args[0][0])

    @patch("httpx.Client.post")
    def test_insert_ticker_verdicts_sends_array(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        verdicts = [
            {"run_id": "abc-123", "ticker": "NVDA", "verdict": "buy", "judge_confidence": 80},
            {"run_id": "abc-123", "ticker": "AAPL", "verdict": "hold", "judge_confidence": 60},
        ]
        self.client.insert_ticker_verdicts(verdicts)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn("ticker_verdicts", call_args[0][0])
        body = call_args[1]["json"]
        self.assertEqual(len(body), 2)

    @patch("httpx.Client.post")
    def test_insert_analysis_run_returns_none_on_failure(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = Exception("Connection refused")

        result = self.client.insert_analysis_run({
            "tickers": ["NVDA"],
            "status": "queued",
            "results": {},
        })

        self.assertIsNone(result)

    @patch("httpx.Client.patch")
    def test_update_analysis_run_swallows_errors(self, mock_patch: MagicMock) -> None:
        mock_patch.side_effect = Exception("Timeout")

        # Should not raise
        self.client.update_analysis_run("abc-123", {"status": "failed"})

    @patch("httpx.Client.post")
    def test_insert_ticker_verdicts_swallows_errors(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = Exception("Network error")

        # Should not raise
        self.client.insert_ticker_verdicts([
            {"run_id": "abc-123", "ticker": "NVDA", "verdict": "buy"}
        ])


if __name__ == "__main__":
    unittest.main()
