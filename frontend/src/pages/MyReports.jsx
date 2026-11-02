import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { LuArrowUpRight } from 'react-icons/lu'
import PageHeading from '../components/common/PageHeading'
import Feedback from '../components/common/Feedback'
import EmptyState from '../components/common/EmptyState'
import Pagination from '../components/common/Pagination'
import StatusBadge from '../components/common/StatusBadge'
import Loading from '../components/Loading'
import useApi from '../data/useApi'
import { apiRequest, downloadFile } from '../data/api'

export default function MyReports() {
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') === 'claims' ? 'claims' : 'reports'
  const page = params.get('page') || '1'
  const query = new URLSearchParams(tab === 'claims' ? { page } : { scope: 'mine', page })
  const resource = useApi(`${tab === 'claims' ? '/claims/' : '/reports/'}?${query}`)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState('')
  const [confirm, setConfirm] = useState('')
  async function withdraw(id) {
    if (busy) return
    setBusy(id); setError(''); setMessage('')
    try { await apiRequest(`/claims/${id}/`, { method: 'PATCH', data: {} }); setConfirm(''); setMessage('Claim withdrawn. You can still follow its history here.'); resource.retry() } catch (failure) { setError(failure.message) } finally { setBusy('') }
  }
  async function evidence(row) { try { await downloadFile(row.url, row.filename || `evidence-${row.id}`) } catch (failure) { setError(failure.message) } }
  return <section className="app-page app-page-narrow activity-page">
    <div className="page-title-row"><PageHeading title="Your way back." eyebrow="MY REPORTS & CLAIMS">Follow your reports, ownership claims and the next step towards a return.</PageHeading><Link className="btn-primary" to="/report">Report an item <LuArrowUpRight aria-hidden="true" /></Link></div>
    <div className="view-switch" role="group" aria-label="Your activity">{['reports', 'claims'].map(value => <button type="button" key={value} aria-pressed={tab === value} onClick={() => { setParams({ tab: value }); setError(''); setMessage(''); setConfirm('') }}>{value === 'reports' ? 'My reports' : 'My ownership claims'}</button>)}</div>
    <Feedback error={error || resource.error} message={message} />
    {resource.loading ? <Loading label={`Loading your ${tab}…`} /> : resource.error ? <button className="btn-secondary" onClick={resource.retry}>Retry loading {tab}</button> : !resource.data.results.length ? <EmptyState title={tab === 'claims' ? 'See something that’s yours?' : 'Your next step starts here.'} description={tab === 'claims' ? 'Open a found-item report on the campus board and submit a private ownership claim. You can follow staff decisions here.' : 'Lost something or found something? Submit a report and follow staff review here, even before it appears publicly.'}><Link className="btn-primary" to={tab === 'claims' ? '/browse?type=found' : '/report'}>{tab === 'claims' ? 'Browse found items' : 'Report an item'}</Link></EmptyState> : <><p className="row-meta text-xs text-slate-500">{resource.data.count} {tab} · most recent first</p>{resource.data.results.map(row => tab === 'reports' ? <article className="activity-row" key={row.id}><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="row-meta">{row.reference} · {row.status} · {row.siteName}</p><h2 className="mt-2"><Link to={`/browse/${row.id}`}>{row.title}</Link></h2></div><StatusBadge value={row.closed ? 'closed' : new Date(row.expiresAt) < new Date() ? 'expired' : row.reviewStatus} /></div><p className="row-meta mt-3">{row.report_type === 'found' ? row.inCustody ? 'Staff have recorded physical receipt.' : 'Physical receipt has not been recorded.' : row.closed ? 'This report has been closed.' : 'We’ll keep your report here while staff review it.'} {row.released ? 'Returned to the verified owner.' : ''}</p><Link className="row-action" to={`/browse/${row.id}`}>View report & next steps <LuArrowUpRight aria-hidden="true" className="ml-2" /></Link></article> : <article className="activity-row" key={row.id}><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="row-meta">{row.reference}</p><h2 className="mt-2"><Link to={`/browse/${row.reportId}`}>{row.title}</Link></h2></div><StatusBadge value={row.released ? 'released' : row.status} /></div><p className="mt-4 whitespace-pre-wrap text-sm leading-7">{row.explanation}</p>{row.remarks && <p className="mt-4 border-l-2 border-brand-600 pl-4 text-sm leading-7"><strong>Staff remarks: </strong>{row.remarks}</p>}<div className="mt-4 flex flex-wrap gap-3">{row.evidence.map((file, index) => <button className="btn-secondary" key={file.id} onClick={() => evidence(file)}>Download evidence {index + 1}</button>)}{row.status === 'pending' && (confirm === row.id ? <div className="w-full border-l-2 border-brand-600 pl-4"><p className="mb-3 text-sm">Withdraw this ownership claim? Staff will stop reviewing it.</p><div className="flex flex-wrap gap-3"><button disabled={Boolean(busy)} className="btn-secondary" onClick={() => withdraw(row.id)}>{busy === row.id ? 'Withdrawing…' : 'Yes, withdraw claim'}</button><button disabled={Boolean(busy)} className="btn-secondary" onClick={() => setConfirm('')}>Keep claim</button></div></div> : <button className="btn-secondary" disabled={Boolean(busy)} onClick={() => setConfirm(row.id)}>Withdraw claim</button>)}</div><p className="row-meta mt-4">Submitted {new Date(row.submittedAt).toLocaleString()}{row.status === 'verified' && !row.released ? ' · Contact OSA to arrange collection. Verification is not a pickup confirmation.' : ''}</p></article>)}</>}
    <Pagination data={resource.data} onPage={value => setParams({ tab, page: String(value) })} />
  </section>
}
