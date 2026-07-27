// Thin client for the PrepPilot backend. Vite proxies /api to :8001.

async function post(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Request failed (${res.status})`)
  }
  return res.json()
}

export const api = {
  start: (role) => post('/api/interview/start', { role }),
  answer: (session_id, answer) => post('/api/interview/answer', { session_id, answer }),
  feedback: (session_id) => post('/api/interview/feedback', { session_id }),
}
