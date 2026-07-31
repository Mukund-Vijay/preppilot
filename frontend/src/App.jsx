import { useEffect, useRef, useState } from 'react'
import { api } from './api'

const ROLES = ['Software Engineer', 'Data Analyst', 'Product Manager', 'Frontend Developer']
const MODES = [
  { id: 'mixed', label: 'Mixed', desc: 'Behavioral + technical' },
  { id: 'behavioral', label: 'Behavioral', desc: 'Experience & teamwork' },
  { id: 'technical', label: 'Technical', desc: 'Concepts & problem-solving' },
]

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('pp-theme') || 'light')
  const [stage, setStage] = useState('setup')
  const [role, setRole] = useState('Software Engineer')
  const [mode, setMode] = useState('mixed')
  const [resume, setResume] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [qNum, setQNum] = useState(0)
  const [totalQ, setTotalQ] = useState(8)
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [error, setError] = useState(null)
  const [timeLeft, setTimeLeft] = useState(120)
  const [qSeconds, setQSeconds] = useState(120)
  const logRef = useRef(null)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('pp-theme', theme)
  }, [theme])

  useEffect(() => {
    requestAnimationFrame(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight })
  }, [messages, busy])

  useEffect(() => {
    if (stage !== 'interview' || done || busy) return
    if (timeLeft <= 0) { submit(input.trim() || '(Ran out of time before answering.)'); return }
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
      setTotalQ(res.total_questions); setStage('interview'); setDone(false); setQNum(0)
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
    try { setFeedback(await api.feedback(sessionId)); setStage('feedback') }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const reset = () => {
    setStage('setup'); setSessionId(null); setMessages([]); setInput('')
    setQNum(0); setDone(false); setFeedback(null); setError(null); setClock(120)
  }

  const onKey = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }

  const mmss = `${String(Math.floor(Math.max(0, timeLeft) / 60)).padStart(2, '0')}:${String(Math.max(0, timeLeft) % 60).padStart(2, '0')}`
  const clockColor = timeLeft <= 10 ? '#c14b3f' : timeLeft <= 30 ? '#bf8b3a' : 'var(--ink)'
  const currentQ = Math.min(done ? qNum : qNum + 1, totalQ)
  const lastBotIndex = messages.map((m) => m.who).lastIndexOf('bot')

  const Topbar = (
    <div className="topbar">
      <div className="brand">Prep<span>Pilot</span><span className="sub">AI Interview</span></div>
      <button className="toggle" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
        title="Toggle theme" aria-label="Toggle light or dark mode">{theme === 'light' ? '☾' : '☀'}</button>
    </div>
  )

  return (
    <div className="shell">
      {Topbar}

      {stage === 'setup' && (
        <div className="card">
          <h2 className="intro-title">Practice under real interview pressure.</h2>
          <p className="intro-sub">A timed, adaptive mock interview — it opens with your introduction, adapts to your answers, presses when they're vague, and scores you at the end.</p>

          <label className="field-label">Role</label>
          <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Software Engineer" />
          <div className="opt-grid" style={{ marginTop: 10 }}>
            {ROLES.map((r) => (
              <button key={r} className={`opt ${role === r ? 'active' : ''}`} onClick={() => setRole(r)}>{r}</button>
            ))}
          </div>

          <label className="field-label">Interview type</label>
          <div className="opt-grid">
            {MODES.map((m) => (
              <button key={m.id} className={`opt ${mode === m.id ? 'active' : ''}`} onClick={() => setMode(m.id)}>
                <div>{m.label}</div><div className="opt-desc">{m.desc}</div>
              </button>
            ))}
          </div>

          <label className="field-label">Paste your resume (optional)</label>
          <textarea value={resume} onChange={(e) => setResume(e.target.value)} rows={4}
            placeholder="Paste your resume text to get questions about your actual projects and skills…" />

          <button className="btn full" onClick={startInterview} disabled={busy || !role.trim()}>
            {busy ? <span className="spinner" /> : 'Start interview'}
          </button>
          {error && <div className="error">{error}</div>}
        </div>
      )}

      {stage === 'interview' && (
        <div className="card">
          <div className="room-top">
            <div><div className="label">Interview in progress</div></div>
            {!done && <div className="clock"><div className="t" style={{ color: clockColor }}>{mmss}</div><div className="label">Time left</div></div>}
          </div>

          <div className="prog-row">
            <span className="label">{role}</span>
            <span className="label">Question {currentQ} / {totalQ}</span>
          </div>
          <div className="prog-track"><div className="prog-fill" style={{ width: `${(currentQ / totalQ) * 100}%` }} /></div>

          <div className="chat" ref={logRef}>
            {messages.map((m, i) => (
              <div key={i} className={`turn ${m.who} ${i === lastBotIndex && !done ? 'latest' : ''}`}>
                <div className={`label turn-label ${m.who === 'user' ? 'you' : ''}`}>{m.who === 'bot' ? 'Interviewer' : 'You'}</div>
                <div className="turn-text">{m.text}</div>
              </div>
            ))}
            {busy && <div className="thinking">Interviewer is thinking…</div>}
          </div>

          {!done ? (
            <div className="composer">
              <div className="row">
                <textarea value={input} rows={3} placeholder="Type your answer…"
                  onChange={(e) => setInput(e.target.value)} onKeyDown={onKey} disabled={busy} />
                <button className="btn" onClick={() => submit()} disabled={busy || !input.trim()}>Send</button>
              </div>
              <div className="hint">Enter to send · Shift+Enter for a new line</div>
            </div>
          ) : (
            <button className="btn full" onClick={getFeedback} disabled={busy}>
              {busy ? <span className="spinner" /> : 'Finish & get my feedback'}
            </button>
          )}
          {error && <div className="error">{error}</div>}
        </div>
      )}

      {stage === 'feedback' && feedback && (
        <div className="card">
          <div className="fb-top">
            <div className="score-num">{feedback.overall_score}<small>/10</small></div>
            <div className="fb-summary">{feedback.summary}</div>
          </div>

          {(feedback.dimensions || []).map((d, i) => (
            <div className="dim" key={i}>
              <div className="dim-top"><b>{d.name}</b><span>{d.score} / 10</span></div>
              <div className="bar-track"><div className="bar-fill" style={{ width: `${(d.score / 10) * 100}%` }} /></div>
            </div>
          ))}

          <div className="cols">
            <div>
              <div className="label">Strengths</div>
              <ul>{(feedback.strengths || []).map((s, i) => <li key={i}>{s}</li>)}</ul>
            </div>
            <div>
              <div className="label">To improve</div>
              <ul>{(feedback.improvements || []).map((s, i) => <li key={i}>{s}</li>)}</ul>
            </div>
          </div>

          <button className="btn full" onClick={reset}>Practice again</button>
        </div>
      )}

      <p className="footer">PrepPilot · AI interview simulator</p>
    </div>
  )
}
