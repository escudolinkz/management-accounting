'use client'
import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Home() {
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('admin123')
  const [csrf, setCsrf] = useState('')
  const [status, setStatus] = useState('')

  async function login() {
    const r = await fetch(`${API}/api/login`, { method: 'POST', headers: { 'Content-Type':'application/json' }, credentials: 'include', body: JSON.stringify({ email, password }) })
    if (r.ok) { const j = await r.json(); setCsrf(j.csrf); setStatus('Logged in') } else setStatus('Login failed')
  }

  async function upload(e: any) {
    e.preventDefault()
    const file = (document.getElementById('pdf') as HTMLInputElement).files?.[0]
    if (!file) return
    const fd = new FormData(); fd.append('f', file)
    const r = await fetch(`${API}/api/upload`, { method:'POST', body: fd, credentials:'include', headers: { 'x-csrf-token': csrf }})
    setStatus(r.ok ? 'Uploaded' : 'Upload failed')
  }

  return (
    <main className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold">Management Accounting</h1>
      <div className="p-4 border rounded bg-white space-y-2">
        <div className="font-semibold">Login</div>
        <input className="border p-2 w-full" value={email} onChange={e=>setEmail(e.target.value)} placeholder="email" />
        <input className="border p-2 w-full" value={password} onChange={e=>setPassword(e.target.value)} type="password" placeholder="password" />
        <button className="bg-black text-white px-4 py-2 rounded" onClick={login}>Sign in</button>
        <div className="text-sm text-gray-600">CSRF: {csrf || '(click Sign in)'}</div>
      </div>
      <form className="p-4 border rounded bg-white space-y-2" onSubmit={upload}>
        <div className="font-semibold">Upload PDF</div>
        <input id="pdf" type="file" accept="application/pdf" className="border p-2 w-full" />
        <button className="bg-blue-600 text-white px-4 py-2 rounded" type="submit">Upload</button>
      </form>
      <Dashboard />
      <div>{status}</div>
    </main>
  )
}

function Dashboard() {
  const [tx, setTx] = useState<any[]>([])
  async function refresh(){
    const r = await fetch(`${API}/api/transactions`, { credentials:'include' })
    if (r.ok) setTx(await r.json())
  }
  useEffect(()=>{ refresh() }, [])
  const total = tx.reduce((a,t)=>a + (t.amount||0), 0)
  return (
    <div className="p-4 border rounded bg-white">
      <div className="font-semibold mb-2">Dashboard</div>
      <div className="text-sm mb-4">Total amount: RM {total.toFixed(2)}</div>
      <button className="border px-3 py-1 rounded" onClick={refresh}>Refresh</button>
      <table className="mt-4 w-full text-sm">
        <thead><tr><th className="text-left">Date</th><th className="text-left">Description</th><th className="text-right">Amount</th></tr></thead>
        <tbody>
          {tx.map(t=> (
            <tr key={t.id} className="border-t"><td>{t.txn_date}</td><td>{t.description}</td><td className="text-right">{t.amount.toFixed(2)}</td></tr>
          ))}
        </tbody>
      </table>
      <div className="mt-3 space-x-2">
        <a className="underline" href={`${API}/api/transactions?export=csv`} target="_blank">Export CSV</a>
        <a className="underline" href={`${API}/api/transactions?export=xlsx`} target="_blank">Export XLSX</a>
      </div>
    </div>
  )
}
