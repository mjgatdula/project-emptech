import Loading from '../Loading'
import Feedback from '../common/Feedback'
export default function ReportReview({ draft, photo, onEdit, onSubmit, busy, error, catalogue, preview }) {
  const name = (rows, id) => rows.find(row => String(row.id) === String(id))?.name || id
  const groups = [
    { title: 'Report type', step: 1, values: [['Type', draft.type === 'found' ? 'I found something' : 'I lost something']] },
    { title: 'Item details', step: 2, values: [['Title', draft.title], ['Category', name(catalogue.categories, draft.category)], ['Description', draft.description]] },
    { title: 'Place and time', step: 3, values: [['Campus', name(catalogue.sites, draft.site)], ['Location', draft.location], ['Date', draft.date], ['Time', draft.unknownTime ? 'Unknown' : draft.time], ['Validity', `${draft.validity} days`]] },
  ]
  return <div>{groups.map(group => <section key={group.title} className="review-section"><div className="flex items-center justify-between gap-3"><h3 className="font-semibold">{group.title}</h3><button type="button" disabled={busy} onClick={() => onEdit(group.step)} aria-label={`Edit ${group.title.toLowerCase()}`} className="min-h-11 text-xs font-semibold underline underline-offset-4">Edit</button></div><dl>{group.values.map(([label, value]) => <div key={label}><dt>{label}</dt><dd className={label === 'Description' ? 'long-value' : ''}>{value}</dd></div>)}</dl></section>)}{photo && <img src={photo.url} alt="Selected item" className="my-5 max-h-48 w-full object-contain" />}<p className="my-6 border-l-2 border-brand-600 pl-4 text-xs leading-7">After submission, your report will be saved to My Reports as Pending Review. It becomes public only after authorized staff approve it.</p><Feedback error={error} /><button type="button" className="btn-primary w-full" disabled={busy || preview} aria-busy={busy} onClick={onSubmit}>{busy ? <Loading inline label="Submitting report…" /> : preview ? 'Sign in to submit' : 'Submit report for review'}</button></div>
}
