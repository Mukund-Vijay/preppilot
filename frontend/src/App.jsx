import { useEffect, useRef, useState } from 'react'
import { api } from './api'

const ROLES = ['Software Engineer', 'Data Analyst', 'Product Manager', 'Frontend Developer']

export default function App() {
  const [stage, setStage] = useState('setup') // setup | interview | feedback
  const [role, setRole] = useState('Software Engineer')
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([]) // {who: 'bot'|'user', text}
  const [input, setInput] = useState('')
  const [qNum, setQNum] = useState(0)
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [error, setError] = useState(null)
  const logRef = useRef(null)

  const scrollDown = () =>
    requestAnimationFrame(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight })

  useEffect(() => { scrollDown() }, [messages, busy])

  const startInterview = async () => {
    setBusy(true); setError(null)
    try {
      const res = await api.start(role)
      setSessionId(res.session_id)
      setMessages([{ who: 'bot', text: res.question }])
      setStage('interview')
      setDone(false); setQNum(0)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const sendAnswer = async () => {
    const answer = input.trim()
    if (!answer || busy || done) return
    setInput('')
    setMessages((m) => [...m, { who: 'user', text: answer }])
    setBusy(true); setError(null)
    try {
      const res = await api.answer(sessionId, answer)
      setMessages((m) => [...m, { who: 'bot', text: res.message }])
      setQNum(res.question_number)
      setDone(res.done)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const getFeedback = async () => {
    setBusy(true); setError(null)
    try {
      const fb = await api.feedback(sessionId)
      setFeedback(fb)
      setStage('feedback')
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const reset = () => {
    setStage('setup'); setSessionId(null); setMessages([]); setInput('')
    setQNum(0); setDone(false); setFeedback(null); setError(null)
  }

  return (
    <div className="app">
      <div className="brand">
        <span className="logo">🛫</span>
        <h1>Prep<span>Pilot</span></h1>
      </div>
      <p className="tagline">Your AI mock interviewer — it asks, follows up on your answers, and scores you.</p>

      {stage === 'setup' && (
        <div className="card">
          <label className="lbl">What role are you interviewing for?</label>
          <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Software Engineer" />
          <div className="chips">
            {ROLES.map((r) => <button key={r} className="chip" onClick={() => setRole(r)}>{r}</button>)}
          </div>
          <button className="primary" onClick={startInterview} disabled={busy || !role.trim()}>
            {busy ? <span className="spinner" /> : 'Start Interview'}
          </button>
          <p className="hint">5 behavioral questions · answer naturally · get scored feedback at the end.</p>
          {error && <div className="error">⚠ {error}</div>}
        </div>
      )}

      {stage === 'interview' && (
        <div className="card">
          <div className="topbar">
            <span className="pill">{role}</span>
            <span className="progress">{Math.min(qNum + (done ? 0 : 1), 5)} / 5 questions</span>
          </div>

          <div className="chat" ref={logRef}>
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.who}`}>
                <div className="who">{m.who === 'bot' ? '🎤 Interviewer' : 'You'}</div>
                {m.text}
              </div>
            ))}
            {busy && <div className="typing">Interviewer is thinking…</div>}
          </div>

          {!done ? (
            <div className="composer">
              <input
                value={input}
                placeholder="Type your answer…"
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendAnswer()}
                disabled={busy}
              />
              <button className="primary" onClick={sendAnswer} disabled={busy || !input.trim()}>Send</button>
            </div>
          ) : (
            <button className="primary" onClick={getFeedback} disabled={busy}>
              {busy ? <span className="spinner" /> : 'Finish & Get My Feedback →'}
            </button>
          )}
          {error && <div className="error">⚠ {error}</div>}
        </div>
      )}

      {stage === 'feedback' && feedback && (
        <div className="card">
          <div className="score-hero">
            <div className="score-num">{feedback.overall_score}<small>/10</small></div>
            <div className="score-sub">{feedback.summary}</div>
          </div>

          {(feedback.dimensions || []).map((d, i) => (
            <div className="dim" key={i}>
              <div className="dim-head"><b>{d.name}</b><span>{d.score}/10</span></div>
              <div className="bar-track"><div className="bar-fill" style={{ width: `${(d.score / 10) * 100}%` }} /></div>
              {d.note && <div className="dim-note">{d.note}</div>}
            </div>
          ))}

          {feedback.strengths?.length > 0 && (
            <div className="fb-section">
              <h3>What went well</h3>
              <ul className="fb-list">
                {feedback.strengths.map((s, i) => <li className="good" key={i}><span className="ic">✓</span>{s}</li>)}
              </ul>
            </div>
          )}

          {feedback.improvements?.length > 0 && (
            <div className="fb-section">
              <h3>Where to improve</h3>
              <ul className="fb-list">
                {feedback.improvements.map((s, i) => <li className="improve" key={i}><span className="ic">→</span>{s}</li>)}
              </ul>
            </div>
          )}

          <button className="primary" onClick={reset}>Practice Again</button>
        </div>
      )}

      <p className="footer">PrepPilot · practice tool · powered by an LLM</p>
    </div>
  )
}
