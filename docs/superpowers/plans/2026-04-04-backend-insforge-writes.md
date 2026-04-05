# Backend Insforge Writes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Insforge writes for `analysis_runs` and `ticker_verdicts` from the React frontend to the FastAPI backend, making the backend the single source of truth for analysis data.

**Architecture:** New `api/insforge_client.jac` module wraps `httpx` calls to the Insforge REST API. `AnalysisService` and the `/v1/analyze-tickers` endpoint call this client after producing results. SQLite stays for ephemeral event streaming only. Frontend removes its insert calls and becomes read-only for analysis data.

**Tech Stack:** Jac (Python-compatible), httpx, Insforge REST API (PostgREST-style), React

**Spec:** `docs/superpowers/specs/2026-04-04-backend-insforge-writes-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `api/insforge_client.jac` | Thin httpx wrapper for Insforge REST API |
| Create | `tests_python/test_insforge_client.py` | Unit tests for InsforgeClient (mocked HTTP) |
| Modify | `api/service.jac:65-80` | Add InsforgeClient dependency injection |
| Modify | `api/service.jac:96-151` | Add Insforge writes in submit_run |
| Modify | `api/service.jac:168-214` | Add Insforge writes in _execute_run |
| Modify | `api/main.jac:57-63` | Initialize InsforgeClient from env vars |
| Modify | `api/main.jac:117-137` | Add Insforge writes in /v1/analyze-tickers |
| Modify | `requirements.txt` | Add httpx dependency |
| Modify | `frontend/src/App.jsx:452-489` | Remove Insforge insert calls from analyzeTickers |
| Create | `tests_python/test_insforge_integration.py` | Integration test for service + insforge client |

---

### Task 1: Add httpx dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add httpx to requirements.txt**

Add `httpx` after the existing dependencies:

```
httpx>=0.27,<1.0
```

Add this line after the `yfinance` line in `requirements.txt`.

- [ ] **Step 2: Install the dependency**

Run: `pip install httpx`
Expected: Successfully installed httpx

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add httpx for Insforge REST API client"
```

---

### Task 2: Create InsforgeClient with tests

**Files:**
- Create: `api/insforge_client.jac`
- Create: `tests_python/test_insforge_client.py`

- [ ] **Step 1: Write the failing tests**

Create `tests_python/test_insforge_client.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ychae/AlphaWalker/AlphaWalker && python -m pytest tests_python/test_insforge_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'api.insforge_client'`

- [ ] **Step 3: Implement InsforgeClient**

Create `api/insforge_client.jac`:

```jac
"""Thin httpx wrapper for Insforge REST API writes."""

import httpx;
import logging;

glob logger = logging.getLogger("api.insforge_client");

class InsforgeClient {
    has base_url: str;
    has service_key: str;
    has _http: httpx.Client;

    def __init__(self: InsforgeClient, base_url: str, service_key: str) {
        self.base_url = base_url.rstrip("/");
        self.service_key = service_key;
        self._http = httpx.Client(
            base_url=self.base_url + "/api/database/records",
            headers={
                "Authorization": "Bearer " + service_key,
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            },
            timeout=10.0
        );
    }

    def close(self: InsforgeClient) {
        self._http.close();
    }

    def insert_analysis_run(self: InsforgeClient, run_data: dict) -> dict | None {
        """Insert a row into analysis_runs. Returns the created row or None on failure."""
        try {
            resp = self._http.post("/analysis_runs", json=[run_data]);
            resp.raise_for_status();
            rows = resp.json();
            if isinstance(rows, list) and len(rows) > 0 {
                return rows[0];
            }
            return None;
        } except Exception as exc {
            logger.warning("Failed to insert analysis_run: %s", exc);
            return None;
        }
    }

    def update_analysis_run(self: InsforgeClient, id: str, updates: dict) -> None {
        """Update an analysis_runs row by id. Logs and swallows errors."""
        try {
            resp = self._http.patch(
                "/analysis_runs?id=eq." + str(id),
                json=updates
            );
            resp.raise_for_status();
        } except Exception as exc {
            logger.warning("Failed to update analysis_run %s: %s", id, exc);
        }
    }

    def insert_ticker_verdicts(self: InsforgeClient, verdicts: list[dict]) -> None {
        """Insert rows into ticker_verdicts. Logs and swallows errors."""
        if len(verdicts) == 0 {
            return;
        }
        try {
            resp = self._http.post("/ticker_verdicts", json=verdicts);
            resp.raise_for_status();
        } except Exception as exc {
            logger.warning("Failed to insert %d ticker_verdicts: %s", len(verdicts), exc);
        }
    }
}

def create_insforge_client(base_url: str | None, service_key: str | None) -> InsforgeClient | None {
    """Factory: returns an InsforgeClient if both env vars are set, else None."""
    if base_url is None or base_url == "" or service_key is None or service_key == "" {
        logger.info("Insforge credentials not configured; cloud writes disabled.");
        return None;
    }
    logger.info("Insforge client initialized for %s", base_url);
    return InsforgeClient(base_url=base_url, service_key=service_key);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/ychae/AlphaWalker/AlphaWalker && python -m pytest tests_python/test_insforge_client.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add api/insforge_client.jac tests_python/test_insforge_client.py
git commit -m "feat: add InsforgeClient for backend Insforge REST API writes"
```

---

### Task 3: Wire InsforgeClient into AnalysisService

**Files:**
- Modify: `api/service.jac:65-80` (constructor)
- Modify: `api/service.jac:96-151` (submit_run)
- Modify: `api/service.jac:168-214` (_execute_run)
- Create: `tests_python/test_insforge_integration.py`

- [ ] **Step 1: Write the failing test**

Create `tests_python/test_insforge_integration.py`:

```python
"""Tests that AnalysisService calls InsforgeClient at the right points."""

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


class ServiceInsforgeTests(unittest.TestCase):

    def setUp(self) -> None:
        self._prev_use_jac = os.environ.get("ALPHAWALKER_USE_JAC")
        os.environ["ALPHAWALKER_USE_JAC"] = "0"
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "runs.db"
        self.storage = RunStorage(str(db_path))
        self.mock_insforge = MagicMock()
        self.mock_insforge.insert_analysis_run.return_value = {
            "id": "insforge-uuid-123",
            "tickers": ["NVDA"],
            "status": "queued",
        }
        self.service = AnalysisService(self.storage, insforge=self.mock_insforge)

    def tearDown(self) -> None:
        self.service.shutdown()
        if self._prev_use_jac is None:
            os.environ.pop("ALPHAWALKER_USE_JAC", None)
        else:
            os.environ["ALPHAWALKER_USE_JAC"] = self._prev_use_jac
        self.temp_dir.cleanup()

    def _make_request(self, tickers: list[str]) -> AnalysisRequest:
        holdings = [Holding(ticker=t, weight=1.0 / len(tickers)) for t in tickers]
        return AnalysisRequest(
            portfolio=PortfolioInput(holdings=holdings, as_of_date="2026-04-04"),
            options=AnalysisOptions(),
            client_context=ClientContext(),
        )

    def test_submit_run_inserts_to_insforge(self) -> None:
        request = self._make_request(["NVDA"])
        self.service.submit_run(request)

        self.mock_insforge.insert_analysis_run.assert_called_once()
        call_data = self.mock_insforge.insert_analysis_run.call_args[0][0]
        self.assertEqual(call_data["tickers"], ["NVDA"])
        self.assertEqual(call_data["status"], "queued")

    def test_completed_run_updates_insforge_and_inserts_verdicts(self) -> None:
        request = self._make_request(["NVDA", "AAPL"])
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

        # Should have called update_analysis_run for running and completed
        update_calls = self.mock_insforge.update_analysis_run.call_args_list
        statuses = [c[0][1]["status"] for c in update_calls]
        self.assertIn("running", statuses)
        self.assertIn("completed", statuses)

        # Should have inserted ticker verdicts
        self.mock_insforge.insert_ticker_verdicts.assert_called_once()

    def test_no_insforge_means_no_calls(self) -> None:
        service_no_insforge = AnalysisService(self.storage, insforge=None)
        request = self._make_request(["NVDA"])
        submitted = service_no_insforge.submit_run(request)

        deadline = time.time() + 5
        while time.time() < deadline:
            run = self.storage.get_run(submitted.run_id)
            if run is not None and run.status in {"completed", "failed"}:
                break
            time.sleep(0.05)

        # No insforge calls — the mock on self was never wired in
        self.mock_insforge.insert_analysis_run.assert_not_called()
        service_no_insforge.shutdown()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/ychae/AlphaWalker/AlphaWalker && python -m pytest tests_python/test_insforge_integration.py -v`
Expected: FAIL — `AnalysisService` doesn't accept `insforge` parameter yet

- [ ] **Step 3: Modify AnalysisService constructor**

In `api/service.jac`, modify the `AnalysisService` class to add the `insforge` field and constructor parameter:

Add to the `has` declarations (after `has _run_locks: dict[str, threading.Lock];`):

```jac
has insforge: Any | None;
```

Modify `__init__` to accept and store the insforge client. Change the signature to:

```jac
def __init__(self: AnalysisService, storage: RunStorage, engine: Any | None = None, insforge: Any | None = None) {
```

Add at the end of `__init__`, after `self._run_locks = {};`:

```jac
self.insforge = insforge;
```

- [ ] **Step 4: Add Insforge write to submit_run**

In `api/service.jac`, at the end of `submit_run` (before the `self.executor.submit` line), add:

```jac
if self.insforge is not None {
    tickers_list: list[str] = [h.ticker for h in normalized_holdings];
    insforge_row = self.insforge.insert_analysis_run({
        "tickers": tickers_list,
        "status": "queued",
        "results": {}
    });
    if insforge_row is not None and "id" in insforge_row {
        record.insforge_id = insforge_row["id"];
        self.storage.update_run(run_id, insforge_id=insforge_row["id"]);
    }
}
```

Note: We need to store the Insforge ID so `_execute_run` can update the correct row. This requires adding an `insforge_id` column to the SQLite schema. However, to keep this minimal, we'll use an in-memory dict instead. Add to `has` declarations:

```jac
has _insforge_ids: dict[str, str];
```

Initialize in `__init__`:

```jac
self._insforge_ids = {};
```

Then replace the storage update above with:

```jac
if self.insforge is not None {
    tickers_list: list[str] = [h.ticker for h in normalized_holdings];
    insforge_row = self.insforge.insert_analysis_run({
        "tickers": tickers_list,
        "status": "queued",
        "results": {}
    });
    if insforge_row is not None and "id" in insforge_row {
        self._insforge_ids[run_id] = insforge_row["id"];
    }
}
```

- [ ] **Step 5: Add Insforge writes to _execute_run**

In `api/service.jac`, modify `_execute_run`. After the existing `self.storage.update_run(run_id, status="running", ...)` line, add:

```jac
if self.insforge is not None and run_id in self._insforge_ids {
    self.insforge.update_analysis_run(
        self._insforge_ids[run_id],
        {"status": "running"}
    );
}
```

After the existing `self.storage.update_run(run_id, status="completed", ...)` line in the try block, add:

```jac
if self.insforge is not None and run_id in self._insforge_ids {
    insforge_id = self._insforge_ids[run_id];
    result_data = result.to_dict();
    self.insforge.update_analysis_run(
        insforge_id,
        {"status": "completed", "results": result_data}
    );
    # Build and insert ticker verdicts
    verdicts: list[dict] = [];
    ticker_results = result_data.get("holdings", []);
    for h in ticker_results {
        verdicts.append({
            "run_id": insforge_id,
            "ticker": h.get("ticker", ""),
            "verdict": h.get("sentiment", ""),
            "judge_confidence": h.get("risk_score", 0),
            "bull_confidence": 0,
            "bear_confidence": 0,
            "rationale": h.get("summary", ""),
            "condition": "",
            "bull_argument": "",
            "bear_argument": ""
        });
    }
    if len(verdicts) > 0 {
        self.insforge.insert_ticker_verdicts(verdicts);
    }
    self._insforge_ids.pop(run_id, None);
}
```

After the existing `self.storage.update_run(run_id, status="failed", ...)` line in the except block, add:

```jac
if self.insforge is not None and run_id in self._insforge_ids {
    self.insforge.update_analysis_run(
        self._insforge_ids[run_id],
        {"status": "failed"}
    );
    self._insforge_ids.pop(run_id, None);
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /home/ychae/AlphaWalker/AlphaWalker && python -m pytest tests_python/test_insforge_integration.py tests_python/test_service.py -v`
Expected: All tests PASS (both new integration tests and existing service tests)

- [ ] **Step 7: Commit**

```bash
git add api/service.jac tests_python/test_insforge_integration.py
git commit -m "feat: wire InsforgeClient into AnalysisService lifecycle"
```

---

### Task 4: Add Insforge writes to /v1/analyze-tickers endpoint

**Files:**
- Modify: `api/main.jac:1-10` (imports)
- Modify: `api/main.jac:57-63` (initialization)
- Modify: `api/main.jac:117-137` (_analyze_tickers_response)

- [ ] **Step 1: Add InsforgeClient import and initialization**

In `api/main.jac`, add to the import section (after the existing imports):

```jac
import from api.insforge_client { create_insforge_client }
```

After the existing `glob service = AnalysisService(storage);` line, add:

```jac
glob insforge_client = create_insforge_client(
    os.getenv("INSFORGE_URL"),
    os.getenv("INSFORGE_SERVICE_KEY")
);
```

Modify the `service` initialization to pass the client:

```jac
glob service = AnalysisService(storage, insforge=insforge_client);
```

- [ ] **Step 2: Add Insforge writes to _analyze_tickers_response**

In `api/main.jac`, modify `_analyze_tickers_response`. After the line `data.append(_row_with_confidence(r));` and before `return {"status": "success", "data": data};`, add:

```jac
if insforge_client is not None and len(data) > 0 {
    insforge_row = insforge_client.insert_analysis_run({
        "tickers": tickers,
        "status": "completed",
        "results": data
    });
    if insforge_row is not None and "id" in insforge_row {
        insforge_run_id = insforge_row["id"];
        verdicts: list[dict] = [];
        for d in data {
            verdicts.append({
                "run_id": insforge_run_id,
                "ticker": d.get("ticker", ""),
                "verdict": d.get("verdict", ""),
                "judge_confidence": d.get("judge_confidence", 0),
                "bull_confidence": d.get("bull_confidence", 0),
                "bear_confidence": d.get("bear_confidence", 0),
                "rationale": d.get("rationale", ""),
                "condition": d.get("condition", ""),
                "bull_argument": d.get("bull_argument", ""),
                "bear_argument": d.get("bear_argument", "")
            });
        }
        if len(verdicts) > 0 {
            insforge_client.insert_ticker_verdicts(verdicts);
        }
    }
}
```

- [ ] **Step 3: Run all backend tests**

Run: `cd /home/ychae/AlphaWalker/AlphaWalker && python -m pytest tests_python/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add api/main.jac
git commit -m "feat: add Insforge writes to /v1/analyze-tickers endpoint"
```

---

### Task 5: Remove Insforge writes from frontend

**Files:**
- Modify: `frontend/src/App.jsx:452-489`

- [ ] **Step 1: Simplify analyzeTickers function**

In `frontend/src/App.jsx`, replace the `analyzeTickers` function (lines 452-490) with:

```jsx
const analyzeTickers = async () => {
    const raw = tickerInput.trim()
    if (!raw) return
    const tickers = raw.split(',').map(t => t.trim().toUpperCase()).filter(t => t.length > 0)
    if (tickers.length === 0) return

    setLoading(true)
    setError('')
    try {
      const resp = await fetch(`${API_BASE}/v1/analyze-tickers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers })
      }).then(r => r.json())

      if (resp.status === 'success') {
        setResults(resp.data || [])
      } else {
        setError('Analysis failed')
      }
    } catch (e) {
      setError('Failed to connect to API: ' + e.message)
    }
    setLoading(false)
  }
```

This removes the `insforge.database.from('analysis_runs').insert(...)` and `insforge.database.from('ticker_verdicts').insert(...)` calls. The backend now handles these writes.

- [ ] **Step 2: Verify the frontend builds**

Run: `cd /home/ychae/AlphaWalker/AlphaWalker/frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "refactor: remove Insforge writes from frontend analyzeTickers

Backend now writes to analysis_runs and ticker_verdicts via
InsforgeClient. Frontend is read-only for analysis data."
```

---

### Task 6: Manual smoke test

**Files:** None (verification only)

- [ ] **Step 1: Set environment variables**

```bash
export INSFORGE_URL="https://57pqpigm.us-east.insforge.app"
export INSFORGE_SERVICE_KEY="<your-service-key>"
```

- [ ] **Step 2: Start the backend**

Run: `cd /home/ychae/AlphaWalker/AlphaWalker && bash start.sh`
Expected: Server starts. Log should show `Insforge client initialized for https://57pqpigm.us-east.insforge.app`

- [ ] **Step 3: Test via curl (CLI path)**

```bash
curl -X POST http://localhost:8000/v1/analyze-tickers \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL"]}'
```

Expected: Returns `{"status": "success", "data": [...]}`. Check Insforge:

```bash
npx @insforge/cli db query "SELECT id, tickers, status FROM analysis_runs ORDER BY created_at DESC LIMIT 1" --json
```

Expected: Shows a row with `tickers: ["AAPL"]` and `status: "completed"`.

```bash
npx @insforge/cli db query "SELECT ticker, verdict FROM ticker_verdicts ORDER BY created_at DESC LIMIT 1" --json
```

Expected: Shows a row with `ticker: "AAPL"`.

- [ ] **Step 4: Test via frontend (browser path)**

Start frontend with `cd frontend && npm run dev`. Open `http://localhost:5173`. Enter `MSFT` and click Analyze. After results appear, click the History tab. Verify both the AAPL (curl) and MSFT (browser) runs appear.

- [ ] **Step 5: Test without credentials (local-only mode)**

```bash
unset INSFORGE_URL
unset INSFORGE_SERVICE_KEY
```

Restart backend. Run another curl analysis. Verify it succeeds (returns results) but no new row appears in Insforge. Log should show `Insforge credentials not configured; cloud writes disabled.`

---

### Task 7: Run full test suite

**Files:** None (verification only)

- [ ] **Step 1: Run all Python tests**

Run: `cd /home/ychae/AlphaWalker/AlphaWalker && python -m pytest tests_python/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run frontend build**

Run: `cd /home/ychae/AlphaWalker/AlphaWalker/frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Final commit if any cleanup needed**

If any fixes were needed during smoke testing, commit them:

```bash
git add -A
git commit -m "fix: address issues found during smoke testing"
```
