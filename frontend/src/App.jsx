import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, LineChart, Line, RadialBarChart, RadialBar
} from 'recharts'
import { createClient } from '@insforge/sdk'

const API_BASE = 'http://localhost:8000'
const insforge = createClient({
  baseUrl: 'https://57pqpigm.us-east.insforge.app',
  anonKey: 'ik_8f69caa0712685e3f234149192249e6e'
})

// ─── Theme ────────────────────────────────────────────────────

const T = {
  bg: '#0f172a',
  surface: '#1e293b',
  surfaceHover: '#334155',
  border: '#334155',
  borderLight: '#475569',
  text: '#f1f5f9',
  textMuted: '#94a3b8',
  textDim: '#64748b',
  accent: '#6366f1',
  inputBg: '#1e293b',
  inputBorder: '#475569',
}

// ─── Sample data (shown before first real analysis) ───────────

const SAMPLE_RESULTS = [
  {
    ticker: 'NVDA', verdict: 'conviction buy', judge_confidence: 88,
    bull_confidence: 91, bear_confidence: 35,
    bull_argument: 'Dominant AI infrastructure play. Data center revenue up 409% YoY. Blackwell architecture ramping with record backlog. Every major hyperscaler increasing capex on NVIDIA GPUs. Gaming and auto segments provide diversification floor.',
    bear_argument: 'Valuation stretched at 35x forward earnings. Customer concentration risk with top 4 cloud providers. China export restrictions limit TAM by ~15%. Competitors (AMD MI300, custom ASICs) gaining traction at the margin.',
    rationale: 'Bull case is overwhelmingly supported by hard revenue data and confirmed hyperscaler capex plans. Bear concerns are valid but secondary to the structural demand tailwind.',
    condition: 'Maintain if data center revenue growth stays above 100% YoY through next 2 quarters'
  },
  {
    ticker: 'AAPL', verdict: 'hold', judge_confidence: 62,
    bull_confidence: 58, bear_confidence: 52,
    bull_argument: 'Services revenue growing 14% YoY with 80%+ margins. Installed base of 2.2B active devices creates unmatched ecosystem lock-in. Apple Intelligence rollout could drive upgrade supercycle. Strong buyback program supports EPS growth.',
    bear_argument: 'iPhone unit growth flat for 3 consecutive quarters. China market share declining amid Huawei resurgence. Apple Intelligence features lagging competitors. Regulatory pressure on App Store fees in EU.',
    rationale: 'Balanced case. Services growth is real but iPhone stagnation is a headwind. Hold until there is evidence of an AI-driven refresh cycle.',
    condition: 'Upgrade to buy if iPhone revenue re-accelerates above 5% YoY growth'
  },
  {
    ticker: 'TSLA', verdict: 'avoid with conditions', judge_confidence: 71,
    bull_confidence: 42, bear_confidence: 78,
    bull_argument: 'Robotaxi potential represents massive optionality. Energy storage business growing 100%+ YoY. Manufacturing cost advantages widening. Brand loyalty and Supercharger network are competitive moats.',
    bear_argument: 'Auto margins compressed from 28% to 16% due to aggressive price cuts. Market share losses in China and Europe to BYD and local EVs. FSD regulatory approval timeline remains uncertain.',
    rationale: 'Bear case is backed by deteriorating fundamentals — margin compression and market share loss are confirmed by data. Avoid until margins stabilize.',
    condition: 'Reconsider if auto gross margins recover above 20% for two consecutive quarters'
  },
  {
    ticker: 'MSFT', verdict: 'buy', judge_confidence: 79,
    bull_confidence: 82, bear_confidence: 40,
    bull_argument: 'Azure growing 31% with AI services contribution accelerating. Copilot adoption expanding across enterprise. GitHub Copilot at 1.8M paid subscribers. Diversified revenue across cloud, productivity, and gaming.',
    bear_argument: 'Azure growth decelerating from 40%+ levels. Copilot monetization still early. Antitrust scrutiny on Activision deal. Capex surge for AI infrastructure may pressure margins near-term.',
    rationale: 'Strong execution across cloud and AI. Azure deceleration is well-understood. Copilot represents genuine incremental revenue. Buy with understanding that near-term capex will weigh on FCF.',
    condition: 'Monitor Azure growth rate — below 25% would warrant downgrade to hold'
  }
]

// ─── Helpers ──────────────────────────────────────────────────

function verdictColor(verdict) {
  const v = (verdict || '').toLowerCase()
  if (v.includes('conviction buy')) return '#22c55e'
  if (v.includes('buy')) return '#4ade80'
  if (v.includes('hold')) return '#eab308'
  if (v.includes('conviction avoid')) return '#ef4444'
  if (v.includes('avoid')) return '#f87171'
  return '#94a3b8'
}

function verdictBg(verdict) {
  const v = (verdict || '').toLowerCase()
  if (v.includes('conviction buy')) return 'rgba(34,197,94,0.12)'
  if (v.includes('buy')) return 'rgba(74,222,128,0.10)'
  if (v.includes('hold')) return 'rgba(234,179,8,0.10)'
  if (v.includes('avoid')) return 'rgba(248,113,113,0.10)'
  return 'rgba(148,163,184,0.08)'
}

// ─── ConfidenceGauge ──────────────────────────────────────────

function ConfidenceGauge({ value = 0, color = '#6366f1', size = 80 }) {
  const data = [{ name: 'conf', value, fill: color }]
  return (
    <div style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart cx="50%" cy="50%" innerRadius="60%" outerRadius="90%"
          startAngle={180} endAngle={0} data={data} barSize={8}>
          <RadialBar dataKey="value" cornerRadius={4} background={{ fill: T.border }} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div style={{ textAlign: 'center', marginTop: -(size * 0.38), fontSize: size * 0.18, fontWeight: 700, color: T.text }}>
        {value}
      </div>
    </div>
  )
}

// ─── BullBearBar ──────────────────────────────────────────────

function BullBearBar({ bull = 0, bear = 0 }) {
  const total = bull + bear
  const bullPct = total > 0 ? (bull / total) * 100 : 50
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
        <span style={{ color: '#4ade80', fontWeight: 600 }}>Bull {bull}</span>
        <span style={{ color: '#f87171', fontWeight: 600 }}>Bear {bear}</span>
      </div>
      <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', backgroundColor: T.border }}>
        <div style={{ width: `${bullPct}%`, backgroundColor: '#4ade80' }} />
        <div style={{ flex: 1, backgroundColor: '#f87171' }} />
      </div>
    </div>
  )
}

// ─── CoalitionCard ────────────────────────────────────────────
// Used in the Analysis tab for the full bull/bear/judge breakdown

function CoalitionCard({ side, confidence, argument }) {
  const isBull = side === 'bull'
  const isJudge = side === 'judge'
  const accentColor = isJudge ? T.accent : isBull ? '#4ade80' : '#f87171'
  const bgColor = isJudge
    ? 'rgba(99,102,241,0.08)'
    : isBull ? 'rgba(74,222,128,0.06)' : 'rgba(248,113,113,0.06)'
  const label = isJudge ? 'Judge' : isBull ? 'Bull Coalition' : 'Bear Coalition'
  const icon = isJudge ? '⚖️' : isBull ? '📈' : '📉'

  return (
    <div style={{
      border: `1px solid ${accentColor}33`,
      borderRadius: 12, padding: 20,
      backgroundColor: bgColor, flex: 1
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 20 }}>{icon}</span>
          <span style={{ fontWeight: 700, fontSize: 15, color: accentColor }}>{label}</span>
        </div>
        <ConfidenceGauge value={confidence} color={accentColor} size={60} />
      </div>
      <p style={{ margin: 0, fontSize: 14, color: T.textMuted, lineHeight: 1.7 }}>{argument}</p>
    </div>
  )
}

function AnalysisTickerSection({ data: d }) {
  return (
    <div style={{
      backgroundColor: T.surface, borderRadius: 14, padding: 24,
      marginBottom: 20, border: `1px solid ${T.border}`
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 24, fontWeight: 800, color: T.text }}>{d.ticker}</span>
          <span style={{
            padding: '5px 14px', borderRadius: 20,
            backgroundColor: verdictColor(d.verdict), color: '#0f172a',
            fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em'
          }}>{d.verdict}</span>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 12, color: T.textDim, marginBottom: 2 }}>Judge Confidence</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: verdictColor(d.verdict) }}>{d.judge_confidence}</div>
        </div>
      </div>

      {/* Coalition panels */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <CoalitionCard side="bull" confidence={d.bull_confidence} argument={d.bull_argument} />
        <CoalitionCard side="bear" confidence={d.bear_confidence} argument={d.bear_argument} />
      </div>

      {/* Judge verdict */}
      {d.rationale && (
        <div style={{
          borderRadius: 10, padding: 16,
          backgroundColor: 'rgba(99,102,241,0.08)',
          border: `1px solid ${T.accent}44`
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ fontSize: 16 }}>⚖️</span>
            <span style={{ fontWeight: 700, color: T.accent, fontSize: 14 }}>Judge Ruling</span>
          </div>
          <p style={{ margin: 0, fontSize: 14, color: T.textMuted, lineHeight: 1.7 }}>{d.rationale}</p>
          {d.condition && (
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${T.border}` }}>
              <span style={{ fontSize: 12, color: T.textDim, fontWeight: 600 }}>WATCH CONDITION — </span>
              <span style={{ fontSize: 13, color: T.textMuted }}>{d.condition}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Dashboard VerdictCard (compact, expandable) ──────────────

function VerdictCard({ data: d }) {
  const [expanded, setExpanded] = useState(false)
  const sectionStyle = { marginBottom: 10, padding: 12, backgroundColor: T.bg, borderRadius: 8, border: `1px solid ${T.border}` }
  return (
    <div
      style={{
        border: `1px solid ${T.border}`, borderRadius: 12, padding: 16,
        marginBottom: 12, backgroundColor: verdictBg(d.verdict), cursor: 'pointer',
        transition: 'border-color 0.2s'
      }}
      onClick={() => setExpanded(!expanded)}
      onMouseEnter={e => e.currentTarget.style.borderColor = T.borderLight}
      onMouseLeave={e => e.currentTarget.style.borderColor = T.border}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ fontSize: 20, fontWeight: 700, color: T.text }}>{d.ticker}</span>
          <span style={{
            marginLeft: 12, padding: '4px 12px', borderRadius: 20,
            backgroundColor: verdictColor(d.verdict), color: '#0f172a',
            fontSize: 12, fontWeight: 600, textTransform: 'uppercase'
          }}>{d.verdict}</span>
        </div>
        <ConfidenceGauge value={d.judge_confidence} color={verdictColor(d.verdict)} />
      </div>
      <div style={{ marginTop: 12 }}>
        <BullBearBar bull={d.bull_confidence} bear={d.bear_confidence} />
      </div>
      {expanded && (
        <div style={{ marginTop: 16 }}>
          <h4 style={{ margin: '0 0 8px', fontSize: 13, color: '#4ade80', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Bull</h4>
          <div style={sectionStyle}>
            <p style={{ fontSize: 13, color: T.textMuted, margin: 0, lineHeight: 1.5 }}>{d.bull_argument}</p>
          </div>
          <h4 style={{ margin: '12px 0 8px', fontSize: 13, color: '#f87171', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Bear</h4>
          <div style={sectionStyle}>
            <p style={{ fontSize: 13, color: T.textMuted, margin: 0, lineHeight: 1.5 }}>{d.bear_argument}</p>
          </div>
          {d.rationale && (
            <div style={{ ...sectionStyle, marginTop: 12, backgroundColor: 'rgba(99,102,241,0.08)' }}>
              <span style={{ fontWeight: 600, fontSize: 12, color: T.accent }}>JUDGE — </span>
              <span style={{ fontSize: 13, color: T.textMuted }}>{d.rationale}</span>
              {d.condition && <p style={{ fontSize: 12, color: T.textDim, margin: '6px 0 0' }}><strong style={{ color: T.textMuted }}>Condition:</strong> {d.condition}</p>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── MomentumSparkline ────────────────────────────────────────

function MomentumSparkline({ ticker }) {
  const [history, setHistory] = useState([])

  useEffect(() => {
    if (!ticker) return
    insforge.database
      .from('ticker_verdicts')
      .select('judge_confidence, created_at')
      .eq('ticker', ticker)
      .order('created_at', { ascending: false })
      .limit(4)
      .then(({ data }) => {
        const pts = (data || []).reverse().map((d, i) => ({ run: i + 1, conf: d.judge_confidence || 0 }))
        setHistory(pts)
      })
  }, [ticker])

  if (history.length < 2) return null
  return (
    <div style={{ width: 120, height: 40 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={history}>
          <Line type="monotone" dataKey="conf" stroke={T.accent} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ─── AddPortfolioDrawer ───────────────────────────────────────

function AddPortfolioDrawer({ open, onClose, onSaved }) {
  const [name, setName] = useState('')
  const [tickerIn, setTickerIn] = useState('')
  const [weightIn, setWeightIn] = useState('1.0')
  const [holdings, setHoldings] = useState([])
  const [saving, setSaving] = useState(false)

  if (!open) return null

  const addHolding = () => {
    const t = tickerIn.trim()
    if (!t) return
    setHoldings([...holdings, { ticker: t.toUpperCase(), weight: parseFloat(weightIn) || 1.0 }])
    setTickerIn('')
    setWeightIn('1.0')
  }

  const save = async () => {
    if (!name.trim() || holdings.length === 0) return
    setSaving(true)
    try {
      await insforge.database.from('portfolios').insert([{ name: name.trim(), holdings }])
      setSaving(false)
      onSaved()
      onClose()
      setName('')
      setHoldings([])
    } catch {
      setSaving(false)
    }
  }

  const inp = { padding: '8px 12px', border: `1px solid ${T.inputBorder}`, borderRadius: 8, backgroundColor: T.inputBg, color: T.text }

  return (
    <div style={{
      position: 'fixed', top: 0, right: 0, bottom: 0, width: 400,
      backgroundColor: T.surface, boxShadow: '-4px 0 24px rgba(0,0,0,0.4)',
      zIndex: 1000, padding: 24, overflowY: 'auto'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 18, color: T.text }}>Add Portfolio</h2>
        <button onClick={onClose} style={{ border: 'none', background: 'none', fontSize: 20, cursor: 'pointer', color: T.textMuted }}>×</button>
      </div>

      <label style={{ fontSize: 13, fontWeight: 600, color: T.textMuted, display: 'block', marginBottom: 6 }}>Portfolio Name</label>
      <input value={name} onChange={e => setName(e.target.value)} placeholder="My Watchlist"
        style={{ ...inp, width: '100%', marginBottom: 16, boxSizing: 'border-box' }} />

      <label style={{ fontSize: 13, fontWeight: 600, color: T.textMuted, display: 'block', marginBottom: 6 }}>Add Holdings</label>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <input value={tickerIn} onChange={e => setTickerIn(e.target.value)} placeholder="NVDA"
          onKeyDown={e => e.key === 'Enter' && addHolding()} style={{ ...inp, flex: 2 }} />
        <input value={weightIn} onChange={e => setWeightIn(e.target.value)} placeholder="1.0"
          type="number" step="0.1" style={{ ...inp, flex: 1 }} />
        <button onClick={addHolding}
          style={{ padding: '8px 16px', backgroundColor: T.accent, color: 'white', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>+</button>
      </div>

      {holdings.map((h, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: T.bg, borderRadius: 6, marginBottom: 4 }}>
          <span style={{ fontWeight: 600, color: T.text }}>{h.ticker}</span>
          <div>
            <span style={{ color: T.textDim, marginRight: 8 }}>{h.weight}</span>
            <button onClick={() => setHoldings(holdings.filter((_, j) => j !== i))}
              style={{ border: 'none', background: 'none', color: '#ef4444', cursor: 'pointer' }}>×</button>
          </div>
        </div>
      ))}

      <button onClick={save} disabled={saving || !name.trim() || holdings.length === 0}
        style={{
          width: '100%', marginTop: 24, padding: 12,
          backgroundColor: saving ? T.textDim : T.accent,
          color: 'white', border: 'none', borderRadius: 8,
          cursor: 'pointer', fontWeight: 600, fontSize: 15
        }}>
        {saving ? 'Saving...' : 'Save Portfolio'}
      </button>
    </div>
  )
}

// ─── RunHistory ───────────────────────────────────────────────

function RunHistory({ onSelectRun }) {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    insforge.database.from('analysis_runs').select('*')
      .order('created_at', { ascending: false }).limit(50)
      .then(({ data }) => { setRuns(data || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return <p style={{ textAlign: 'center', padding: 40, color: T.textMuted }}>Loading runs...</p>
  if (runs.length === 0) return <p style={{ textAlign: 'center', padding: 40, color: T.textDim }}>No past runs yet. Analyze some tickers to get started.</p>

  return (
    <div>
      {runs.map(run => {
        const tickers = run.tickers || []
        const results = run.results || []
        return (
          <div key={run.id}
            style={{ border: `1px solid ${T.border}`, borderRadius: 12, padding: 16, marginBottom: 12, cursor: 'pointer', backgroundColor: T.surface, transition: 'border-color 0.2s' }}
            onMouseEnter={e => e.currentTarget.style.borderColor = T.borderLight}
            onMouseLeave={e => e.currentTarget.style.borderColor = T.border}
            onClick={() => onSelectRun(run)}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontWeight: 600, color: T.text }}>{tickers.join(', ')}</span>
              <span style={{ fontSize: 12, color: T.textDim }}>{new Date(run.created_at).toLocaleString()}</span>
            </div>
            <div style={{ fontSize: 13, color: T.textDim, marginTop: 4 }}>{results.length} tickers analyzed</div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Main App ─────────────────────────────────────────────────

export default function App() {
  const [tab, setTab] = useState('dashboard')
  const [tickerInput, setTickerInput] = useState('')
  const [results, setResults] = useState(SAMPLE_RESULTS)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [portfolios, setPortfolios] = useState([])
  const [selectedPid, setSelectedPid] = useState('')

  const loadPortfolios = () => {
    insforge.database.from('portfolios').select('*').order('created_at', { ascending: false })
      .then(({ data }) => setPortfolios(data || []))
      .catch(() => {})
  }

  // Seed sample portfolios on first load if none exist
  useEffect(() => {
    insforge.database.from('portfolios').select('id').limit(1)
      .then(({ data }) => {
        if (!data || data.length === 0) {
          insforge.database.from('portfolios').insert([
            { name: 'Tech Giants', holdings: [{ ticker: 'NVDA', weight: 0.3 }, { ticker: 'AAPL', weight: 0.25 }, { ticker: 'MSFT', weight: 0.25 }, { ticker: 'GOOGL', weight: 0.2 }] },
            { name: 'EV & Energy', holdings: [{ ticker: 'TSLA', weight: 0.35 }, { ticker: 'RIVN', weight: 0.2 }, { ticker: 'ENPH', weight: 0.25 }, { ticker: 'FSLR', weight: 0.2 }] },
            { name: 'Semiconductor Bet', holdings: [{ ticker: 'NVDA', weight: 0.3 }, { ticker: 'AMD', weight: 0.25 }, { ticker: 'AVGO', weight: 0.25 }, { ticker: 'TSM', weight: 0.2 }] },
          ]).then(() => loadPortfolios())
        } else {
          loadPortfolios()
        }
      })
      .catch(() => loadPortfolios())
  }, [])

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

  const onPortfolioChange = (e) => {
    const pid = e.target.value
    setSelectedPid(pid)
    if (pid) {
      const p = portfolios.find(p => p.id === pid)
      if (p) setTickerInput((p.holdings || []).map(h => h.ticker).join(', '))
    }
  }

  const restoreRun = (run) => {
    setResults(run.results || [])
    setTab('dashboard')
  }

  const tabs = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'analysis', label: 'Analysis' },
    { id: 'history', label: 'History' },
  ]

  const tabBtn = (id) => ({
    padding: '6px 16px', border: `1px solid ${T.border}`, borderRadius: 8, cursor: 'pointer',
    fontWeight: tab === id ? 700 : 400, color: T.text,
    backgroundColor: tab === id ? 'rgba(99,102,241,0.15)' : 'transparent'
  })

  return (
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", backgroundColor: T.bg, minHeight: '100vh', color: T.text }}>

      {/* Top Bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 24px', backgroundColor: T.surface,
        borderBottom: `1px solid ${T.border}`, position: 'sticky', top: 0, zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: T.text }}>AlphaWalker</h1>

          <select value={selectedPid} onChange={onPortfolioChange}
            style={{ padding: '6px 12px', border: `1px solid ${T.inputBorder}`, borderRadius: 8, fontSize: 13, backgroundColor: T.inputBg, color: T.text }}>
            <option value="">Select portfolio...</option>
            {portfolios.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>

          <div style={{ display: 'flex', gap: 4 }}>
            {tabs.map(t => <button key={t.id} onClick={() => setTab(t.id)} style={tabBtn(t.id)}>{t.label}</button>)}
          </div>
        </div>

        <button onClick={() => setDrawerOpen(true)}
          style={{ padding: '8px 20px', backgroundColor: T.accent, color: 'white', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>
          + Add Portfolio
        </button>
      </div>

      {/* Ticker Input (visible on dashboard + analysis tabs) */}
      {(tab === 'dashboard' || tab === 'analysis') && (
        <div style={{ padding: '16px 24px', backgroundColor: T.surface, borderBottom: `1px solid ${T.border}` }}>
          <div style={{ maxWidth: 1200, margin: '0 auto', display: 'flex', gap: 8 }}>
            <input value={tickerInput}
              onChange={e => setTickerInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && analyzeTickers()}
              placeholder="Enter tickers: NVDA, AAPL, TSLA, MSFT"
              style={{ flex: 1, padding: '10px 16px', border: `1px solid ${T.inputBorder}`, borderRadius: 10, fontSize: 14, backgroundColor: T.inputBg, color: T.text }} />
            <button onClick={analyzeTickers} disabled={loading}
              style={{
                padding: '10px 28px', backgroundColor: loading ? T.textDim : T.accent,
                color: 'white', border: 'none', borderRadius: 10, cursor: 'pointer', fontWeight: 700, fontSize: 14
              }}>
              {loading ? 'Analyzing...' : 'Analyze'}
            </button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>

        {error && <div style={{ padding: 16, backgroundColor: 'rgba(239,68,68,0.12)', borderRadius: 8, color: '#f87171', marginBottom: 16, border: '1px solid rgba(239,68,68,0.3)' }}>{error}</div>}

        {loading && (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <div style={{ fontSize: 18, color: T.textMuted }}>Running bull/bear analysis...</div>
            <div style={{ fontSize: 13, color: T.textDim, marginTop: 8 }}>This may take a few minutes per ticker</div>
          </div>
        )}

        {/* ── Dashboard tab ── */}
        {!loading && tab === 'dashboard' && (
          <div>
            {results.length > 0 ? (
              <>
                <div style={{ backgroundColor: T.surface, borderRadius: 12, padding: 24, marginBottom: 24, border: `1px solid ${T.border}` }}>
                  <h3 style={{ margin: '0 0 16px', fontSize: 16, color: T.text }}>Confidence Overview</h3>
                  <ResponsiveContainer width="100%" height={Math.max(200, results.length * 50)}>
                    <BarChart data={results} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
                      <XAxis type="number" domain={[0, 100]} stroke={T.textDim} tick={{ fill: T.textDim }} />
                      <YAxis type="category" dataKey="ticker" width={60} stroke={T.textDim} tick={{ fill: T.textMuted }} />
                      <Tooltip contentStyle={{ backgroundColor: T.surface, border: `1px solid ${T.border}`, borderRadius: 8, color: T.text }} />
                      <Legend wrapperStyle={{ color: T.textMuted }} />
                      <Bar dataKey="bull_confidence" name="Bull" fill="#4ade80" />
                      <Bar dataKey="bear_confidence" name="Bear" fill="#f87171" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                {results.map(d => (
                  <div key={d.ticker} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}><VerdictCard data={d} /></div>
                    <MomentumSparkline ticker={d.ticker} />
                  </div>
                ))}
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: 80, color: T.textDim }}>
                <div style={{ fontSize: 18 }}>Enter tickers above to run bull/bear analysis</div>
              </div>
            )}
          </div>
        )}

        {/* ── Analysis tab ── */}
        {!loading && tab === 'analysis' && (
          <div>
            {results.length > 0 ? (
              <>
                <p style={{ color: T.textDim, fontSize: 13, margin: '0 0 20px' }}>
                  Full bull/bear coalition arguments and judge ruling for each ticker. Click a verdict card on Dashboard to expand a summary, or review the full breakdown here.
                </p>
                {results.map(d => <AnalysisTickerSection key={d.ticker} data={d} />)}
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: 80, color: T.textDim }}>
                <div style={{ fontSize: 18 }}>Run an analysis first to see the breakdown here</div>
              </div>
            )}
          </div>
        )}

        {/* ── History tab ── */}
        {tab === 'history' && <RunHistory onSelectRun={restoreRun} />}
      </div>

      <AddPortfolioDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} onSaved={loadPortfolios} />
      {drawerOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 999 }}
          onClick={() => setDrawerOpen(false)} />
      )}
    </div>
  )
}
