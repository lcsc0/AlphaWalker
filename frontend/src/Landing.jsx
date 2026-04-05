const T = {
  bg: '#0f172a',
  surface: '#1e293b',
  border: '#334155',
  borderLight: '#475569',
  text: '#f1f5f9',
  textMuted: '#94a3b8',
  textDim: '#64748b',
  accent: '#6366f1',
}

const features = [
  {
    icon: '⚔️',
    title: 'Adversarial Debate',
    body: 'A bull coalition and a bear coalition each build the strongest possible case. LLMs argue better than they hedge — so we make them argue.',
  },
  {
    icon: '⚖️',
    title: 'Judge Agent',
    body: 'A neutral judge reads both sides, weighs evidence quality, and renders a verdict: conviction buy, hold, avoid, or insufficient data.',
  },
  {
    icon: '📊',
    title: 'Portfolio Intelligence',
    body: 'A meta-agent traverses your entire portfolio at once, surfacing concentration risk, correlated bets, and hedging gaps no single ticker view can see.',
  },
]

export default function Landing({ onGetStarted }) {
  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: T.bg,
      color: T.text,
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      display: 'flex',
      flexDirection: 'column',
    }}>

      {/* Nav */}
      <nav style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '20px 48px',
        borderBottom: `1px solid ${T.border}`,
      }}>
        <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.3px' }}>AlphaWalker</span>
        <button
          onClick={onGetStarted}
          style={{
            padding: '8px 20px',
            backgroundColor: 'transparent',
            color: T.accent,
            border: `1px solid rgba(99,102,241,0.5)`,
            borderRadius: 8,
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: 14,
          }}>
          Open App
        </button>
      </nav>

      {/* Hero */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '80px 24px 60px',
      }}>
        {/* Badge */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          padding: '6px 14px',
          backgroundColor: 'rgba(99,102,241,0.12)',
          border: `1px solid rgba(99,102,241,0.3)`,
          borderRadius: 20,
          fontSize: 12,
          fontWeight: 600,
          color: T.accent,
          marginBottom: 32,
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}>
          Multi-Agent Investment Research
        </div>

        {/* Headline */}
        <h1 style={{
          fontSize: 'clamp(32px, 5vw, 58px)',
          fontWeight: 800,
          lineHeight: 1.1,
          letterSpacing: '-1px',
          margin: '0 0 24px',
          maxWidth: 780,
        }}>
          Two AI teams debate<br />
          <span style={{ color: T.accent }}>every stock</span> in your portfolio.
        </h1>

        {/* Sub */}
        <p style={{
          fontSize: 'clamp(15px, 2vw, 19px)',
          color: T.textMuted,
          lineHeight: 1.7,
          maxWidth: 600,
          margin: '0 0 48px',
        }}>
          One coalition argues buy. One argues sell. A judge agent weighs the evidence and renders a verdict — with confidence scores, rationale, and watch conditions.
        </p>

        {/* CTA */}
        <button
          onClick={onGetStarted}
          style={{
            padding: '16px 40px',
            backgroundColor: T.accent,
            color: '#fff',
            border: 'none',
            borderRadius: 10,
            cursor: 'pointer',
            fontWeight: 700,
            fontSize: 16,
            letterSpacing: '-0.2px',
            boxShadow: '0 0 32px rgba(99,102,241,0.35)',
            transition: 'opacity 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.opacity = '0.88'}
          onMouseLeave={e => e.currentTarget.style.opacity = '1'}
        >
          Get Started →
        </button>

        {/* Verdict preview strip */}
        <div style={{
          display: 'flex',
          gap: 10,
          marginTop: 48,
          flexWrap: 'wrap',
          justifyContent: 'center',
        }}>
          {[
            { label: 'CONVICTION BUY', color: '#22c55e', bg: 'rgba(34,197,94,0.1)' },
            { label: 'BUY WITH CONDITIONS', color: '#4ade80', bg: 'rgba(74,222,128,0.08)' },
            { label: 'HOLD', color: '#eab308', bg: 'rgba(234,179,8,0.1)' },
            { label: 'AVOID WITH CONDITIONS', color: '#f87171', bg: 'rgba(248,113,113,0.1)' },
            { label: 'CONVICTION AVOID', color: '#ef4444', bg: 'rgba(239,68,68,0.1)' },
            { label: 'INSUFFICIENT DATA', color: T.textDim, bg: 'rgba(100,116,139,0.1)' },
          ].map(v => (
            <span key={v.label} style={{
              padding: '4px 10px',
              borderRadius: 6,
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: '0.04em',
              color: v.color,
              backgroundColor: v.bg,
              border: `1px solid ${v.color}33`,
            }}>
              {v.label}
            </span>
          ))}
        </div>
      </div>

      {/* Features */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: 20,
        padding: '0 48px 80px',
        maxWidth: 1100,
        margin: '0 auto',
        width: '100%',
        boxSizing: 'border-box',
      }}>
        {features.map(f => (
          <div key={f.title} style={{
            backgroundColor: T.surface,
            border: `1px solid ${T.border}`,
            borderRadius: 14,
            padding: '28px 28px',
          }}>
            <div style={{ fontSize: 28, marginBottom: 14 }}>{f.icon}</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.text, marginBottom: 10 }}>{f.title}</div>
            <p style={{ fontSize: 13, color: T.textMuted, lineHeight: 1.7, margin: 0 }}>{f.body}</p>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={{
        borderTop: `1px solid ${T.border}`,
        padding: '20px 48px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: 12,
        color: T.textDim,
      }}>
        <span>AlphaWalker</span>
        <span>Built on Jac · Powered by OpenAI</span>
      </div>
    </div>
  )
}
