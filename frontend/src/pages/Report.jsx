import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import PageHeading from '../components/common/PageHeading'
import Feedback from '../components/common/Feedback'
import Loading from '../components/Loading'
import ReportProgress from '../components/reports/ReportProgress'
import ReportFormSteps from '../components/reports/ReportFormSteps'
import ReportReview from '../components/reports/ReportReview'
import { createReportDraft, reportSteps, validateReportStep, reportPayload } from '../data/reportFlow'
import { apiRequest } from '../data/api'
import useApi from '../data/useApi'

export default function Report({ user }) {
  const [params] = useSearchParams()
  const options = useApi('/catalogue/')
  const [draft, setDraft] = useState(() => createReportDraft(params.get('type')))
  const [step, setStep] = useState(user ? (['lost', 'found'].includes(params.get('type')) ? 2 : 1) : 0)
  const [completed, setCompleted] = useState(user ? (['lost', 'found'].includes(params.get('type')) ? [0, 1] : [0]) : [])
  const [preview, setPreview] = useState(false)
  const [error, setError] = useState('')
  const [photoError, setPhotoError] = useState('')
  const [photo, setPhoto] = useState(null)
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(null)
  const heading = useRef(null)
  const catalogue = options.data || { sites: [], categories: [] }
  useEffect(() => () => { if (photo) URL.revokeObjectURL(photo.url) }, [photo])
  useEffect(() => { heading.current?.focus({ preventScroll: true }) }, [step])
  function change(field, value) { setDraft(current => ({ ...current, [field]: value })); setError('') }
  function changePhoto(file) {
    if (file && (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024)) { setPhotoError('Choose a JPEG, PNG or WebP image up to 5 MB.'); return false }
    setPhotoError(''); setPhoto(file ? { file, url: URL.createObjectURL(file) } : null); return true
  }
  function advance(event) {
    event.preventDefault()
    const issue = validateReportStep(step, draft)
    if (issue) { setError(issue); return }
    setCompleted(current => [...new Set([...current, step])]); setError(''); setStep(step + 1)
  }
  async function submit() {
    if (busy || !user) return
    for (const index of [1, 2, 3]) { const issue = validateReportStep(index, draft); if (issue) { setError(issue); return } }
    setBusy(true); setError('')
    try {
      const result = await apiRequest('/reports/', { method: 'POST', data: reportPayload(draft, photo) })
      setSaved(result.report); setCompleted([0, 1, 2, 3, 4]); setStep(5)
    } catch (failure) { setError(failure.message) } finally { setBusy(false) }
  }
  const next = `/report${draft.type ? `?type=${draft.type}` : ''}`
  return <section className="app-page report-page">
    <PageHeading title="Report a lost or found item." eyebrow="REPORT AN ITEM">Add the item details, location and date. You’ll review everything before submitting.</PageHeading>
    <ReportProgress currentStep={step} completed={completed} preview={preview} onStepChange={busy || saved ? undefined : setStep} />
    <div className="report-layout">
      <div className="panel report-form-panel min-w-0"><h2 ref={heading} tabIndex={-1} className="outline-none">{reportSteps[step].title}</h2><p className="report-step-hint">{step > 0 && step < 4 ? "Fields marked * are required. You can go back to change your answers." : step === 4 ? "Check the details below before sending your report to staff." : "Your campus account keeps your reports and updates in one place."}</p>
        {saved ? <div className="space-y-5"><Feedback message={`Report saved: ${saved.reference}. Staff review is pending.`} /><p className="text-sm leading-7">Your report is stored in your account. You can follow decisions, edit eligible reports, and track ownership claims in My Reports.</p><Link className="btn-primary" to={`/browse/${saved.id}`}>View your report</Link><Link className="btn-secondary ml-3" to="/my-reports">My Reports</Link></div>
        : step === 0 ? <div className="space-y-5"><p className="text-sm leading-7">{user ? 'Your account is signed in. Continue to describe the item.' : 'Sign in to save a report to your account and follow staff updates.'}</p>{user ? <button className="btn-primary" onClick={() => setStep(1)}>Continue</button> : <><Link className="btn-primary" to={`/login?${new URLSearchParams({ next })}`}>Sign In</Link><Link className="btn-secondary ml-3" to={`/register?${new URLSearchParams({ next })}`}>Register</Link><button className="block text-sm underline" onClick={() => { setPreview(true); setStep(1) }}>Preview the form</button></>}</div>
        : options.loading ? <Loading label="Loading campus options..." /> : options.error ? <><Feedback error={options.error} /><button className="btn-secondary" onClick={options.retry}>Retry</button></>
        : step < 4 ? <form onSubmit={advance} className="space-y-6">{preview && <p className="text-sm text-brand-800">Preview only. Sign in before submitting.</p>}<ReportFormSteps step={step} draft={draft} onChange={change} photo={photo} onPhotoChange={changePhoto} photoError={photoError} catalogue={catalogue} /><Feedback error={error} /><div className="form-actions"><button type="button" className="btn-secondary" onClick={() => setStep(step - 1)}>Back</button><button className="btn-primary">{step === 3 ? 'Review Report' : 'Continue'}</button></div></form>
        : <><ReportReview draft={draft} photo={photo} onEdit={setStep} onSubmit={submit} busy={busy} error={error} catalogue={catalogue} preview={preview || !user} /><button disabled={busy} className="btn-secondary mt-5" onClick={() => setStep(3)}>Back</button>{!user && <Link className="ml-4 text-sm underline" to={`/login?${new URLSearchParams({ next })}`}>Sign in to submit</Link>}</>}
      </div>
      <aside className="report-guidance"><h2 className="font-bold">What happens next?</h2><ol className="mt-4 list-decimal space-y-4 pl-5"><li>Keep the reference number in My Reports.</li><li>OSA reviews the report before publication.</li><li>Found items need physical turnover and separate ownership verification before release.</li></ol><Link className="mt-5 inline-block font-semibold text-brand-800 underline" to="/browse">Browse Items</Link></aside>
    </div>
  </section>
}

