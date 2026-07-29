import { useEffect, useRef, useState } from 'react'
import { api } from './api'

const ROLES = ['Software Engineer', 'Data Analyst', 'Product Manager', 'Frontend Developer']
const MODES = [
  { id: 'mixed', label: 'Mixed', desc: 'Behavioral + technical' },
  { id: 'behavioral', label: 'Behavioral', desc: 'Experience & teamwork' },
  { id: 'technical', label: 'Technical', desc: 'Concepts & problem-solving' },
]

export default function App() {
  const [stage, setStage] = useState('setup') // setup | interview | feedback
  const [role, setRole] = useState('Software Engineer')
  const [mode, setMode] = useState('mixed')
  const [resume, setResume] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([]) // {who:'bot'|'user', text}
  const [input, setInput] = useState('')
  const [qNum, setQNum] = useState(0)
  const [totalQ, setTotalQ] = useState(8)
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [error, setError] = useState(null)
  const [timeLeft, setTimeLeft] = useState(120)
  const [qSeconds, setQSeconds] = useState(120) // budget for the current question
  const logRef = useRef(null)

  useEffect(() => {
    requestAnimationFrame(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight })
  }, [messages, busy])

  // Countdown — pauses while the interviewer is "thinking" (busy) or once finished.
  useEffect(() => {
    if (stage !== 'interview' || done || busy) return
    if (timeLeft <= 0) { submit(input.trim() || "(Ran out of time before answering.)"); return }
    const t = setTimeout(() => setTimeLeft((s) => s - 1), 1000)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft, stage, done, busy])

  const setClock = (secs) => { setQSeconds(secs); setTimeLeft(secs) }

  const startInterview = async () => {
    setBusy(true); setError(null)
    try {
      const res = await api.start(role, mode, resume)
      setSessionId(res.session_id)
      setMessages([{ who: 'bot', text: res.question }])
      setTotalQ(res.total_questions)
      setStage('interview'); setDone(false); setQNum(0)
      setClock(res.seconds)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const submit = async (answerText) => {
    const answer = (answerText ?? input).trim()
    if (!answer || busy || done) return
    setInput('')
    setMessages((m) => [...m, { who: 'user', text: answer }])
    setBusy(true); setError(null)
    try {
      const res = await api.answer(sessionId, answer)
      setMessages((m) => [...m, { who: 'bot', text: res.message }])
      setQNum(res.question_number); setDone(res.done)
      if (!res.done) setClock(res.seconds)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const getFeedback = async () => {
    setBusy(true); setError(null)
    try {
      setFeedback(await api.feedback(sessionId)); setStage('feedback')
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const reset = () => {
    setStage('setup'); setSessionId(null); setMessages([]); setInput('')
    setQNum(0); setDone(false); setFeedback(null); setError(null); setClock(120)
  }

  const onKey = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }

  const mmss = `${String(Math.floor(timeLeft / 60)).padStart(2, '0')}:${String(Math.max(0, timeLeft) % 60).padStart(2, '0')}`
  const timeClass = timeLeft <= 10 ? 'danger' : timeLeft <= 30 ? 'warn' : ''
  const timeColor = timeLeft <= 10 ? 'var(--red)' : timeLeft <= 30 ? 'var(--amber)' : 'var(--accent)'
  const currentQ = Math.min(done ? qNum : qNum + 1, totalQ)

  return (
    <div className="shell">
      <div className="brandbar">
        <div className="mark">🛫</div>
        <h1>Prep<span>Pilot</span></h1>
        <div className="by">AI Interview Simulator</div>
      </div>

      {/* ---------- SETUP ---------- */}
      {stage === 'setup' && (
        <div className="card">
          <p className="hero-eyebrow">Mock Interview</p>
          <h2 className="hero-title">Practice under real interview pressure.</h2>
          <p className="hero-sub">
            A timed, adaptive mock interview — it starts with your introduction, adapts to your
            answers, presses when they're vague, and (optionally) tailors questions to your resume.
          </p>

          <p className="field-label">Role</p>
          <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Software Engineer" />
          <div className="role-grid">
            {ROLES.map((r) => (
              <button key={r} className={`role-card ${role === r ? 'active' : ''}`} onClick={() => setRole(r)}>{r}</button>
            ))}
          </div>

          <p className="field-label" style={{ marginTop: 20 }}>Interview type</p>
          <div className="role-grid">
            {MODES.map((m) => (
              <button key={m.id} className={`role-card ${mode === m.id ? 'active' : ''}`} onClick={() => setMode(m.id)}>
                <div style={{ fontWeight: 600 }}>{m.label}</div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>{m.desc}</div>
              </button>
            ))}
          </div>

          <p className="field-label" style={{ marginTop: 20 }}>Paste your resume <span style={{ opacity: 0.7 }}>(optional — tailors the questions to your experience)</span></p>
          <textarea value={resume} onChange={(e) => setResume(e.target.value)} rows={4}
            placeholder="Paste your resume text here to get questions about your actual projects and skills…" />

          <button className="primary" onClick={startInterview} disabled={busy || !role.trim()}>
            {busy ? <span className="spinner" /> : 'Start Interview →'}
          </button>

          <div className="hero-meta">
            <div>🎬 Opens with <b>your introduction</b></div>
            <div>⏱️ <b>Variable</b> timing per question</div>
            <div>📊 Scored feedback at the end</div>
          </div>
          {error && <div className="error">⚠ {error}</div>}
        </div>
      )}

      {/* ---------- INTERVIEW ---------- */}
      {stage === 'interview' && (
        <div className="card">
          <div className="room-top">
            <div className="left">
              <span className="pill">{role}</span>
              <span className="pill">Question {currentQ} of {totalQ}</span>
              <span className="live"><span className="dot" /> Live</span>
            </div>
            {!done && (
              <div className="timer">
                <div className={`clock ${timeClass}`}>{mmss}</div>
                <div className="lbl">time left</div>
              </div>
            )}
          </div>

          {!done && (
            <div className="timerbar">
              <div className="fill" style={{ width: `${Math.max(0, (timeLeft / qSeconds) * 100)}%`, background: timeColor }} />
            </div>
          )}

          <div className="chat" ref={logRef}>
            {messages.map((m, i) => (
              <div key={i} className={`turn ${m.who}`}>
                <div className={`avatar ${m.who === 'bot' ? 'bot' : 'me'}`}>{m.who === 'bot' ? '🎤' : 'You'}</div>
                <div>
                  <div className="name">{m.who === 'bot' ? 'Interviewer' : 'You'}</div>
                  <div className="bubble">{m.text}</div>
                </div>
              </div>
            ))}
            {busy && <div className="thinking">Interviewer is thinking…</div>}
          </div>

          {!done ? (
            <div className="composer">
              <div className="row">
                <textarea value={input} placeholder="Type your answer… (Enter to send, Shift+Enter for a new line)"
                  onChange={(e) => setInput(e.target.value)} onKeyDown={onKey} disabled={busy} rows={3} />
                <button className="primary" onClick={() => submit()} disabled={busy || !input.trim()}>Send</button>
              </div>
              <div className="tip">The clock is running — answer with a specific example, like a real interview.</div>
            </div>
          ) : (
            <button className="primary" onClick={getFeedback} disabled={busy}>
              {busy ? <span className="spinner" /> : 'Finish & Get My Feedback →'}
            </button>
          )}
          {error && <div className="error">⚠ {error}</div>}
        </div>
      )}

      {/* ---------- FEEDBACK ---------- */}
      {stage === 'feedback' && feedback && (
        <div className="card">
          <div className="fb-head">
            <ScoreGauge score={feedback.overall_score} />
            <div className="summary"><b>Overall.</b> {feedback.summary}</div>
          </div>

          {(feedback.dimensions || []).map((d, i) => {
            const color = d.score >= 8 ? 'var(--green)' : d.score >= 5 ? 'var(--amber)' : 'var(--red)'
            return (
              <div className="dim" key={i}>
                <div className="dim-head"><b>{d.name}</b><span>{d.score}/10</span></div>
                <div className="bar-track"><div className="bar-fill" style={{ width: `${(d.score / 10) * 100}%`, background: color }} /></div>
                {d.note && <div className="dim-note">{d.note}</div>}
              </div>
            )
          })}

          <div className="fb-grid">
            <div className="fb-box good">
              <h3>What went well</h3>
              <ul>{(feedback.strengths || []).map((s, i) => <li key={i}><span className="ic">✓</span>{s}</li>)}</ul>
            </div>
            <div className="fb-box improve">
              <h3>Where to improve</h3>
              <ul>{(feedback.improvements || []).map((s, i) => <li key={i}><span className="ic">→</span>{s}</li>)}</ul>
            </div>
          </div>

          <button className="primary" onClick={reset}>Practice Again</button>
        </div>
      )}

      <p className="footer">PrepPilot · AI interview simulator · practice tool</p>
    </div>
  )
}

function ScoreGauge({ score }) {
  const r = 52, c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(10, Number(score) || 0)) / 10
  const color = score >= 8 ? '#22c55e' : score >= 5 ? '#f59e0b' : '#ef4444'
  return (
    <svg width="132" height="132" viewBox="0 0 132 132" style={{ flexShrink: 0 }}>
      <circle cx="66" cy="66" r={r} fill="none" stroke="var(--panel-2)" strokeWidth="12" />
      <circle cx="66" cy="66" r={r} fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - pct)} transform="rotate(-90 66 66)" />
      <text x="66" y="62" textAnchor="middle" fontSize="32" fontWeight="800" fill="var(--text)">{score}</text>
      <text x="66" y="84" textAnchor="middle" fontSize="12" fill="var(--muted)">out of 10</text>
    </svg>
  )
}
