type SyncPayload = {
  analysisRunId: string;
  runId: string;
  cursor?: number;
};

export default async function syncPortfolioAnalysisRun(payload: SyncPayload) {
  const apiBaseUrl = process.env.ALPHAWALKER_API_BASE_URL;
  const apiKey = process.env.ALPHAWALKER_API_KEY;

  if (!apiBaseUrl || !apiKey) {
    throw new Error("Missing AlphaWalker API configuration");
  }

  const [runResponse, eventsResponse, existingEvents] = await Promise.all([
    fetch(`${apiBaseUrl}/v1/analysis-runs/${payload.runId}`, {
      headers: { "X-API-Key": apiKey },
    }),
    fetch(`${apiBaseUrl}/v1/analysis-runs/${payload.runId}/events?cursor=${payload.cursor ?? 0}`, {
      headers: { "X-API-Key": apiKey },
    }),
    base44.entities.AnalysisEvent.list("-seq", 500, 0),
  ]);

  if (!runResponse.ok) {
    throw new Error(`AlphaWalker run fetch failed: ${await runResponse.text()}`);
  }
  if (!eventsResponse.ok) {
    throw new Error(`AlphaWalker event fetch failed: ${await eventsResponse.text()}`);
  }

  const run = await runResponse.json();
  const eventPayload = await eventsResponse.json();
  const events = eventPayload.events ?? [];
  const existingSeqs = new Set(
    existingEvents
      .filter((item) => item.run_id === payload.runId)
      .map((item) => `${item.run_id}:${item.seq}`)
  );

  for (const event of events) {
    const dedupeKey = `${payload.runId}:${event.seq}`;
    if (existingSeqs.has(dedupeKey)) {
      continue;
    }
    await base44.entities.AnalysisEvent.create({
      run_id: payload.runId,
      analysis_run_id: payload.analysisRunId,
      seq: event.seq,
      agent: event.agent,
      stage: event.stage,
      message: event.message,
      event_time: event.timestamp,
    });
  }

  await base44.entities.AnalysisRun.update(payload.analysisRunId, {
    status: run.status,
    result: run.result,
    error: run.error,
    updated_date: new Date().toISOString(),
    completed_date: run.finished_at,
  });

  const persistedEvents = await base44.entities.AnalysisEvent.list("-seq", 500, 0);
  const orderedEvents = persistedEvents
    .filter((item) => item.run_id === payload.runId)
    .sort((a, b) => a.seq - b.seq);

  return {
    runId: payload.runId,
    analysisRunId: payload.analysisRunId,
    status: run.status,
    progress: run.progress,
    result: run.result,
    error: run.error,
    startedAt: run.started_at,
    finishedAt: run.finished_at,
    events: orderedEvents,
    nextCursor: eventPayload.next_cursor,
  };
}
