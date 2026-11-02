import { useState } from 'react'
import useApi from '../data/useApi'
import { apiRequest } from '../data/api'
import Feedback from './common/Feedback'
import Pagination from './common/Pagination'
import Loading from './Loading'

export default function ExternalInvitations() {
  const [page, setPage] = useState(1)
  const invitations = useApi(`/staff/external-access/?page=${page}`)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  async function submit(event) {
    event.preventDefault()
    if (busy) return
    const form = event.currentTarget
    const values = new FormData(form)
    await mutate('POST', { email: values.get('email').trim(), days: Number(values.get('days')) }, () => form.reset())
  }
  async function mutate(method, data, done) {
    if (busy) return
    setBusy(true); setError(''); setMessage('')
    try {
      const result = await apiRequest('/staff/external-access/', { method, data })
      setMessage(result.message); done?.(); if (method === 'POST') setPage(1); invitations.retry()
    } catch (failure) { setError(failure.message) } finally { setBusy(false) }
  }
  return <section className="panel space-y-5" aria-labelledby="external-access-heading">
    <h2 id="external-access-heading" className="text-xl font-bold">External Google accounts</h2>
    <p className="form-hint">Approve an exact external email before its owner signs in with Gmail or Google Workspace. TIP accounts do not need invitations. External users can submit reports and claims, but receive no staff privileges. No invitation email is sent.</p>
    <form onSubmit={submit}><fieldset disabled={busy} className="space-y-4">
      <label className="label">External email<input name="email" type="email" className="field" autoComplete="off" required maxLength={254} placeholder="visitor@gmail.com" /></label>
      <label className="label">Access duration (days)<input name="days" type="number" className="field" defaultValue="30" min="1" max="365" required /></label>
      <button className="btn-primary" disabled={busy}>{busy ? 'Saving...' : 'Approve or renew external email'}</button>
    </fieldset></form>
    <Feedback error={error || invitations.error} message={message} />
    {invitations.error && <button className="btn-secondary" onClick={invitations.retry}>Retry loading approvals</button>}
    {invitations.loading ? <Loading /> : <ul className="space-y-3">{invitations.data?.results.map(row => <li className="configuration-record flex-wrap gap-3" key={row.id}>
      <div className="min-w-0"><p className="break-words font-semibold">{row.email}</p><p className="form-hint">{row.canSignIn ? 'Active' : row.isActive ? 'Expired' : 'Revoked'} · {row.accepted ? 'Account linked' : 'Awaiting first Google sign-in'} · Expires {new Date(row.expiresAt).toLocaleDateString()}</p></div>
      {row.isActive && <button className="btn-secondary" disabled={busy} onClick={() => mutate('PATCH', { id: row.id })}>Revoke access</button>}
    </li>)}</ul>}
    {invitations.data?.count === 0 && <p className="form-hint">No external emails approved yet.</p>}
    <Pagination data={invitations.data} onPage={setPage} />
  </section>
}
