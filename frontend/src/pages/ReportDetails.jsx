import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import PageHeading from '../components/common/PageHeading'
import Feedback from '../components/common/Feedback'
import StatusBadge from '../components/common/StatusBadge'
import ReportPhoto from '../components/reports/ReportPhoto'
import ReportFormSteps from '../components/reports/ReportFormSteps'
import Loading from '../components/Loading'
import EmptyState from '../components/common/EmptyState'
import useAuth from '../context/useAuth'
import useApi from '../data/useApi'
import { apiRequest } from '../data/api'
import { draftFromReport, reportPayload, validateReportStep } from '../data/reportFlow'

function EditReport({ report, onSaved, onCancel }) {
  const catalogue = useApi('/catalogue/')
  const [draft, setDraft] = useState(() => draftFromReport(report))
  const [photo, setPhoto] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => () => { if (photo) URL.revokeObjectURL(photo.url) }, [photo])
  const change = (field, value) => setDraft(current => ({ ...current, [field]: value }))
  function upload(file) {
    if (file && (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024)) { setError('Choose a JPEG, PNG or WebP image up to 5 MB.'); return false }
    setPhoto(file ? { file, url: URL.createObjectURL(file) } : null); return true
  }
  async function save(event) {
    event.preventDefault()
    if (busy) return
    for (const step of [1, 2, 3]) { const issue = validateReportStep(step, draft); if (issue) { setError(issue); return } }
    setBusy(true); setError('')
    try { await apiRequest(`/reports/${report.id}/`, { method: 'PATCH', data: reportPayload(draft, photo) }); onSaved() } catch (failure) { setError(failure.message) } finally { setBusy(false) }
  }
  if (catalogue.loading) return <Loading />
  if (catalogue.error) return <Feedback error={catalogue.error} />
  return <form onSubmit={save} className="panel space-y-8"><h2 className="text-xl font-bold">Edit your report</h2><p className="text-sm text-slate-600">Changes return the report to Pending Review. Your current photo remains unless replaced or removed.</p>{[1, 2, 3].map(step => <section className="form-section" key={step}><h3>{step === 1 ? 'Report type' : step === 2 ? 'Item details' : 'Place and time'}</h3><ReportFormSteps step={step} draft={draft} onChange={change} photo={photo} onPhotoChange={upload} catalogue={catalogue.data} /></section>)}{report.image && <label className="flex gap-3 text-sm"><input type="checkbox" checked={draft.removeImage} onChange={e => change('removeImage', e.target.checked)} />Remove current photograph</label>}<Feedback error={error} /><div className="flex gap-3"><button disabled={busy} className="btn-primary">{busy ? 'Saving...' : 'Save changes'}</button><button type="button" disabled={busy} className="btn-secondary" onClick={onCancel}>Cancel</button></div></form>
}

export default function ReportDetails() {
  const { id } = useParams()
  const { user } = useAuth()
  return <ReportDetailsView key={`${id}:${user?.id || 'guest'}`} id={id} />
}

function ReportDetailsView({ id }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const resource = useApi(`/reports/${encodeURIComponent(id)}/`)
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  async function action(path, data, success, method = 'POST') {
    if (busy) return false
    setBusy(true); setError(''); setMessage('')
    try { await apiRequest(path, { method, data }); setMessage(success); resource.retry(); return true } catch (failure) { setError(failure.message); return false } finally { setBusy(false) }
  }
  async function claim(event) {
    event.preventDefault()
    if (busy) return
    const form = event.currentTarget
    const data = new FormData(form)
    const evidence = data.getAll('evidence').filter(file => file.size > 0)
    if (evidence.length > 3 || evidence.some(file => file.size > 5 * 1024 * 1024)) { setError('Choose at most three evidence files, up to 5 MB each.'); return }
    data.set('report', id)
    const ok = await action('/claims/', data, 'Ownership claim submitted. Follow verification in My Reports & Claims.')
    if (ok) form.reset()
  }
  if (resource.loading) return <Loading label="Loading report..." />
  if (resource.error) return <section className="app-page detail-page"><PageHeading title="Report unavailable" /><EmptyState title="Let’s find another way." description={resource.error}><button className="btn-primary" onClick={resource.retry}>Retry</button><Link className="btn-secondary" to="/browse">Browse items</Link></EmptyState></section>
  const report = resource.data.report
  if (editing) return <section className="app-page detail-page"><EditReport report={report} onCancel={() => setEditing(false)} onSaved={() => { setEditing(false); setMessage('Changes saved and returned to staff review.'); resource.retry() }} /></section>
  return <section className="app-page detail-page"><Link className="back-link" to={report.isOwner ? '/my-reports' : '/browse'}>Back to {report.isOwner ? 'My Reports' : 'Browse Items'}</Link><PageHeading title={report.title}>{report.reference} · {report.status} · {report.siteName}</PageHeading><Feedback error={error} message={message} />
    <article className="report-detail-article"><div className="mb-5 flex flex-wrap gap-3"><StatusBadge value={report.closed ? 'closed' : new Date(report.expiresAt) < new Date() ? 'expired' : report.reviewStatus} />{report.inCustody && <StatusBadge value="in_custody" />}{report.released && <StatusBadge value="released" />}</div><div className="detail-composition"><div className="detail-photo-wrap"><ReportPhoto path={report.image} title={report.title} className="detail-photo" /></div><div className="detail-information"><p className="text-xs leading-7 text-slate-600">{report.report_type === 'found' ? report.inCustody ? 'Staff have recorded physical receipt. Ownership is checked before collection.' : 'A finder reported this item. Physical receipt by staff is not yet recorded.' : 'Someone is looking for this belonging. If you found it, submit a found-item report so staff can help.'}</p><dl className="mt-6 grid gap-6 text-sm sm:grid-cols-2">{[['Category', report.categoryName], ['Location', report.location], [report.report_type === 'found' ? 'Date found' : 'Date last seen', report.date], ['Approximate time', report.time || 'Unknown'], ['Submitted', new Date(report.createdAt).toLocaleString()], ['Listing expires', new Date(report.expiresAt).toLocaleString()]].map(([label, value]) => <div key={label}><dt className="text-slate-500">{label}</dt><dd className="mt-2 font-semibold">{value}</dd></div>)}</dl></div></div><div className="detail-description"><h2 className="font-semibold">About this item</h2><p className="mt-3 whitespace-pre-wrap break-words text-sm leading-7">{report.description}</p>{report.report_type === 'lost' && !report.closed && !report.isOwner && <Link className="btn-primary mt-5" to="/report?type=found">Found something like this? Report it</Link>}</div></article>
    {report.history?.length > 0 && <details className="detail-secondary"><summary>Review history</summary><ol className="mt-4 space-y-4">{report.history.map((row, index) => <li key={index} className="border-l-2 border-brand-600 pl-4 text-sm"><StatusBadge value={row.decision} /><p className="mt-2">{row.reason || 'Staff review recorded.'}</p><time className="text-xs text-slate-500">{new Date(row.decided_at).toLocaleString()}</time></li>)}</ol></details>}
    {report.closure?.length > 0 && <Feedback message={`Closed: ${report.closure[0].reason}`} />}
    {report.isOwner && <section className="panel detail-manage space-y-4"><h2 className="font-bold">Manage your report</h2><div className="flex flex-wrap gap-3">{report.canEdit && <button className="btn-secondary" onClick={() => setEditing(true)}>Edit report</button>}{report.canDelete && <button disabled={busy} className="btn-secondary" onClick={async () => { if (!confirmDelete) { setConfirmDelete(true); return } if (await action(`/reports/${id}/`, undefined, '', 'DELETE')) navigate('/my-reports') }}>{confirmDelete ? 'Confirm permanent deletion' : 'Delete report'}</button>}{confirmDelete && <button className="btn-secondary" onClick={() => setConfirmDelete(false)}>Cancel deletion</button>}</div>{report.report_type === 'lost' && !report.closed && <form className="space-y-3" onSubmit={event => { event.preventDefault(); action(`/reports/${id}/close/`, { reason: new FormData(event.currentTarget).get('reason') }, 'Report closed.') }}><label className="label">Recovered your item? Explain how it was resolved<input className="field" name="reason" required maxLength={255} /></label><button disabled={busy} className="btn-primary">Mark recovered / close report</button></form>}</section>}
    {report.canManage && <Link className="btn-primary mt-6" to={`/staff?report=${id}`}>Open in OSA workspace</Link>}
    {(report.canClaim || report.myClaim) && <section className="panel detail-private"><p className="app-eyebrow mb-3">PRIVATE OWNERSHIP CHECK</p><h2>{report.myClaim ? 'Your ownership claim' : 'Does this belong to you?'}</h2>{report.myClaim ? <div className="mt-4 space-y-4"><StatusBadge value={report.myClaim.status} /><p className="text-sm">You already submitted a claim for this report. Follow staff updates in My Reports & Claims.</p><Link className="btn-secondary" to="/my-reports?tab=claims">Track my claim</Link></div> : !user ? <p className="mt-4 text-sm"><Link className="font-semibold underline" to={`/login?${new URLSearchParams({ next: `/browse/${id}` })}`}>Sign in</Link> to submit a private ownership claim.</p> : <form className="claim-form mt-5 space-y-5" onSubmit={claim}><p className="text-sm leading-7">Describe identifying details that only the owner would know. This information and your evidence are visible only to you and authorized staff. Verification and physical pickup are separate steps.</p><label className="label">Private ownership explanation *<textarea className="field" name="private_explanation" rows={4} required minLength={15} maxLength={4000} /></label><label className="label">Evidence (optional, up to three files)<input className="field" type="file" name="evidence" accept=".pdf,.png,.jpg,.jpeg" multiple /></label><p className="text-xs text-slate-500">PDF, PNG or JPEG; 5 MB per file. Do not upload passwords or unrelated sensitive documents.</p><button disabled={busy} className="btn-primary">{busy ? 'Submitting...' : 'Submit private claim'}</button><Link className="ml-4 text-sm underline" to="/my-reports?tab=claims">Track my claims</Link></form>}</section>}
  </section>
}
