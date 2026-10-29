import { useEffect, useState } from 'react'

const API = 'http://127.0.0.1:5000/api'
const rupees = (n) => 'Rs ' + Math.round(n).toLocaleString('en-IN')

async function call(path, options) {
  const res = await fetch(API + path, options)
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || res.statusText)
  return data
}

function Stat({ label, value, note, tone }) {
  return (
    <div className="card">
      <div className="muted">{label}</div>
      <div className={'big ' + (tone || '')}>{value}</div>
      <div className="muted small">{note}</div>
    </div>
  )
}

// Cumulative spend so far (solid) and the forecast to month end (dashed), drawn as plain SVG.
function SpendChart({ overview }) {
  const { daily, forecast, today, total_budget } = overview
  const todayN = Number(today.slice(8))
  const days = todayN + forecast.days_left
  const W = 640, H = 240, L = 50, R = 12, T = 12, B = 26
  let run = 0
  const cum = daily.map((d) => (run += d.spend))
  const top = Math.max(forecast.forecast, total_budget, run) * 1.08 || 1
  const x = (d) => L + ((d - 1) / (days - 1)) * (W - L - R)
  const y = (v) => H - B - (v / top) * (H - T - B)
  const path = cum.map((v, i) => `${i ? 'L' : 'M'}${x(i + 1)},${y(v)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img"
         aria-label={`Spent ${rupees(run)} so far, forecast ${rupees(forecast.forecast)} by month end`}>
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line x1={L} x2={W - R} y1={y(f * top)} y2={y(f * top)} className="grid" />
          <text x={L - 6} y={y(f * top) + 4} textAnchor="end" className="axis">{Math.round((f * top) / 1000)}k</text>
        </g>
      ))}
      <line x1={L} x2={W - R} y1={y(total_budget)} y2={y(total_budget)} className="budget" />
      <text x={L + 6} y={y(total_budget) - 5} className="axis bold">total budget {rupees(total_budget)}</text>
      <path d={path} className="line" />
      <line x1={x(todayN)} y1={y(run)} x2={x(days)} y2={y(forecast.forecast)} className="proj" />
      <circle cx={x(days)} cy={y(forecast.forecast)} r="4" className="end" />
      <text x={W - R} y={y(forecast.forecast) + 18} textAnchor="end" className="axis bold">forecast {rupees(forecast.forecast)}</text>
      {[1, 8, 15, 22, days].map((d) => (
        <text key={d} x={x(d)} y={H - 8} textAnchor="middle" className="axis">{d}</text>
      ))}
    </svg>
  )
}

function Budgets({ rows }) {
  const max = Math.max(1, ...rows.map((r) => Math.max(r.spent, r.budget)))
  return (
    <ul className="plain">
      {rows.map((r) => {
        const over = r.budget > 0 && r.spent > r.budget
        return (
          <li key={r.category}>
            <div className="row">
              <span>{r.category}</span>
              <span>{rupees(r.spent)} <span className="muted">/ {rupees(r.budget)}</span>{over && <b className="tag"> over</b>}</span>
            </div>
            <div className="track">
              <div className={'fill' + (over ? ' over' : '')} style={{ width: (r.spent / max) * 100 + '%' }} />
              <div className="mark" style={{ left: (r.budget / max) * 100 + '%' }} />
            </div>
          </li>
        )
      })}
    </ul>
  )
}

// One table row with a category dropdown. Saving teaches the agent a rule (the feedback loop).
function TxnRow({ t, categories, onSaved }) {
  const [cat, setCat] = useState(t.category)
  const save = async () => {
    try {
      const r = await call(`/transactions/${t.id}/correct`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category: cat }),
      })
      onSaved(`Learned: "${r.pattern}" is ${r.category}. ${r.relabelled} past transactions relabelled.`)
    } catch (e) {
      onSaved('Could not save: ' + e.message)
    }
  }
  return (
    <tr>
      <td>{t.date}</td>
      <td>{t.merchant}</td>
      <td className="right">{t.type === 'credit' ? '+' : ''}{rupees(t.amount)}</td>
      <td>
        <select value={cat} onChange={(e) => setCat(e.target.value)} disabled={t.type === 'credit'} aria-label={'Category for ' + t.merchant}>
          {categories.map((c) => <option key={c}>{c}</option>)}
        </select>
      </td>
      <td><span className={'chip ' + t.parser}>{t.parser}</span></td>
      <td><button onClick={save} disabled={cat === t.category}>Save rule</button></td>
    </tr>
  )
}
// Form for adding a transaction by hand (cash payments, or an SMS the agent never received).
function AddTransaction({ categories, onAdded }) {
  const empty = { date: new Date().toISOString().slice(0, 10), type: 'debit', amount: '', merchant: '', category: '' }
  const [form, setForm] = useState(empty)
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setProblem('')
    try {
      const t = await call('/transactions', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, amount: Number(form.amount), category: form.category || undefined }),
      })
      onAdded(`Added ${rupees(t.amount)} ${t.type === 'credit' ? 'received from' : 'to'} ${t.merchant} as ${t.category}.`)
      setForm({ ...empty, date: form.date, type: form.type })
    } catch (err) {
      setProblem(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="add" onSubmit={submit}>
      <label>Date<input type="date" value={form.date} onChange={set('date')} required /></label>
      <label>Type
        <select value={form.type} onChange={set('type')}>
          <option value="debit">Spent</option><option value="credit">Received</option>
        </select>
      </label>
      <label>Amount (Rs)<input type="number" min="0.01" step="0.01" value={form.amount} onChange={set('amount')} required /></label>
      <label>Merchant<input type="text" maxLength="60" value={form.merchant} onChange={set('merchant')} placeholder="e.g. Chai Point" required /></label>
      <label>Category
        <select value={form.category} onChange={set('category')}>
          <option value="">Auto-detect</option>
          {categories.map((c) => <option key={c}>{c}</option>)}
        </select>
      </label>
      <button type="submit" disabled={busy}>{busy ? 'Adding…' : 'Add transaction'}</button>
      {problem && <div className="problem" role="alert">{problem}</div>}
    </form>
  )
}
export default function App() {
  const [overview, setOverview] = useState(null)
  const [txns, setTxns] = useState([])
  const [categories, setCategories] = useState([])
  const [rules, setRules] = useState([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const [o, t, c, r] = await Promise.all([call('/overview'), call('/transactions?limit=40'), call('/categories'), call('/rules')])
      setOverview(o); setTxns(t); setCategories(c); setRules(r); setError('')
    } catch (e) {
      setError(e.message)
    }
  }
  useEffect(() => { load() }, [])

  if (error) return <main><div className="card">Cannot reach the backend ({error}). Start it with <code>python -m backend.api</code>.</div></main>
  if (!overview) return <main><div className="card">Loading…</div></main>

  const { forecast, total_budget, alerts, categories: cats } = overview
  const over = forecast.forecast > total_budget
  return (
    <main>
      <header>
        <div>
          <h1>Personal Finance Agent</h1>
          <p className="muted">As of {overview.today} · everything runs on this computer</p>
        </div>
        <span className="pill">● Offline · 127.0.0.1</span>
      </header>

      <section className="stats">
        <Stat label="Spent this month" value={rupees(forecast.spent)} note={`${forecast.days_left} days left`} />
        <Stat label="Forecast month-end" value={rupees(forecast.forecast)} tone={over ? 'bad' : 'good'}
              note={over ? `${rupees(forecast.forecast - total_budget)} over budget` : 'within budget'} />
        <Stat label="Total budget" value={rupees(total_budget)} note={`${Math.round((forecast.spent / total_budget) * 100)}% used`} />
      </section>

      <section className="two">
        <div className="card"><h2>Cumulative spend and forecast</h2><SpendChart overview={overview} /></div>
        <div className="card">
          <h2>Alerts {alerts.length > 0 && <span className="tag">{alerts.length}</span>}</h2>
          {alerts.length === 0 && <p className="muted">No category is forecast to exceed its budget.</p>}
          <ul className="plain">
            {alerts.map((a) => (
              <li key={a.category} className="alert">
                <b>{a.category}</b> is forecast {rupees(a.over_by)} over budget
                <div className="muted small">{rupees(a.spent)} spent of {rupees(a.budget)}</div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="card"><h2>Budget vs actual</h2><Budgets rows={cats} /></section>
      <section className="card">
        <h2>Add a transaction</h2>
        <AddTransaction categories={categories} onAdded={(m) => { setMessage(m); load() }} />
      </section>
      <section className="card">
        <h2>Latest transactions <span className="muted small">change a category and press Save to teach the agent</span></h2>
        {message && <div className="note" role="status">{message}</div>}
        <div className="scroll">
          <table>
            <thead><tr><th>Date</th><th>Merchant</th><th className="right">Amount</th><th>Category</th><th>Parsed by</th><th /></tr></thead>
            <tbody>
              {txns.map((t) => (
                <TxnRow key={t.id + t.category} t={t} categories={categories} onSaved={(m) => { setMessage(m); load() }} />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>Learned rules <span className="muted small">({rules.length})</span></h2>
        {rules.length === 0 ? <p className="muted">None yet. Correct a category above and it will appear here.</p> : (
          <ul className="plain">{rules.map((r) => <li key={r.id}><code>{r.pattern}</code> → <b>{r.category}</b></li>)}</ul>
        )}
      </section>
    </main>
  )
}