import { useState } from 'react'
import { Link } from 'react-router-dom'
import PageHeading from '../components/common/PageHeading'
import Feedback from '../components/common/Feedback'
import EmptyState from '../components/common/EmptyState'
import Loading from '../components/Loading'
import useApi from '../data/useApi'
import useAuth from '../context/useAuth'
import { apiRequest } from '../data/api'
export default function Notifications() {
  const { user } = useAuth()
  const resource = useApi('/notifications/')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function markRead() {
    if (busy) return
    setBusy(true); setError('')
    try { await apiRequest('/notifications/', { method: 'POST', data: {} }); resource.retry(); window.dispatchEvent(new Event('tipped:notifications')) } catch (failure) { setError(failure.message) } finally { setBusy(false) }
  }
  return <section className="app-page app-page-narrow notifications-page"><PageHeading title="A little closer." eyebrow="YOUR NOTIFICATIONS">{user.isOsa ? 'Your personal updates and operational alerts for campuses you can currently manage.' : 'Updates about your own reports and claims. These messages are private to your account.'}</PageHeading><Feedback error={error || resource.error} />{resource.loading ? <Loading label="Loading updates…" /> : resource.error ? <button className="btn-secondary" onClick={resource.retry}>Retry loading updates</button> : <><div className="results-heading"><p role="status"><strong>{resource.data.unread}</strong> unread updates</p><div className="flex flex-wrap gap-3"><button className="btn-secondary" disabled={busy} onClick={resource.retry}>Refresh updates</button><button className="btn-secondary" disabled={busy || !resource.data.unread} aria-busy={busy} onClick={markRead}>{busy ? 'Updating…' : 'Mark all as read'}</button></div></div>{resource.data.results.length ? resource.data.results.map(row => <article key={row.id} className={`notification-row ${row.read_at ? '' : 'is-unread'}`}>{!row.read_at && <p className="unread-label">UNREAD UPDATE</p>}<p className="text-sm leading-7">{row.message}</p><time className="mt-3 block text-xs text-slate-500" dateTime={row.created_at}>{new Date(row.created_at).toLocaleString()}</time>{row.actionUrl && <Link className="back-link mb-0 mt-3" to={row.actionUrl}>{row.audience === 'operations' ? 'Review in OSA workspace' : 'View report & updates'} ↗</Link>}</article>) : <EmptyState title="You’re all caught up." description="When staff review a report or update a claim, you’ll find the news here."><Link to="/my-reports" className="btn-secondary">Go to my reports</Link></EmptyState>}</>}</section>
}
