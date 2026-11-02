import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import useApi from '../data/useApi'
import useAuth from '../context/useAuth'
import { apiRequest } from '../data/api'
import PageHeading from '../components/common/PageHeading'
import Feedback from '../components/common/Feedback'
import Pagination from '../components/common/Pagination'
import Loading from '../components/Loading'

const roleLabels = { superadmin: 'Super Admin', admin: 'Administrator', osa: 'OSA', student: 'Student', guest: 'External user' }

function UserPermissions({ user, viewer, sites, onSave }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [osa, setOsa] = useState(user.roles.includes('osa'))
  const protectedTarget = user.isSuperuser || user.id === viewer.id || (!viewer.isSuperuser && user.isProtected)

  async function save(event) {
    event.preventDefault()
    if (busy) return
    setBusy(true); setError(''); setSaved(false)
    const values = new FormData(event.currentTarget)
    const data = { id: user.id, isActive: values.has('active'), ...(user.studentProfile ? { approval: values.get('approval') } : {}) }
    if (viewer.isSuperuser) {
      Object.assign(data, { isAdmin: values.has('admin'), isOsa: osa, siteIds: osa ? values.getAll('sites').map(Number) : [] })
    }
    try {
      await apiRequest('/staff/users/', { method: 'PATCH', data })
      setSaved(true)
      onSave()
    } catch (failure) { setError(failure.message) } finally { setBusy(false) }
  }

  return (
    <form className="panel space-y-4" onSubmit={save}>
      <div>
        <h3 className="font-bold">{user.fullName || user.username}</h3>
        <p className="mt-1 text-xs text-slate-500">{user.username} · {user.email}</p>
        <p className="mt-2 text-xs font-semibold">{user.roles.map(role => roleLabels[role] || role).join(' / ')}{!user.isActive ? ' · Inactive' : ''}</p>
      </div>
      {protectedTarget ? <p className="text-sm text-slate-500">Protected account. Your own account and Super Admin accounts cannot be changed here.</p> : (
        <details className="permissions-disclosure">
          <summary>{viewer.isSuperuser ? 'Edit account and role permissions' : 'Review ordinary account'}</summary>
          <div className="space-y-5 pt-4">
            <label className="flex gap-2 text-sm"><input name="active" type="checkbox" defaultChecked={user.isActive} />Active account</label>
            {viewer.isSuperuser && !user.isExternal && <>
              <fieldset className="space-y-3">
                <legend className="text-sm font-semibold">Application roles</legend>
                <label className="flex gap-2 text-sm"><input name="admin" type="checkbox" defaultChecked={user.roles.includes('admin')} />Administrator: ordinary accounts and catalogue</label>
                <label className="flex gap-2 text-sm"><input name="osa" type="checkbox" checked={osa} onChange={event => setOsa(event.target.checked)} />OSA: campus report operations</label>
                <p className="form-hint">These roles are independent. Administrator access does not grant ownership evidence or OSA controls.</p>
              </fieldset>
              {osa && <fieldset>
                <legend className="text-sm font-semibold">OSA campus assignments</legend>
                <div className="mt-3 flex flex-wrap gap-5 text-sm">{sites.map(site => <label key={site.id} className="flex gap-2"><input name="sites" value={site.id} type="checkbox" defaultChecked={user.siteIds.includes(site.id)} disabled={!site.is_active} />{site.name}{!site.is_active ? ' (inactive)' : ''}</label>)}</div>
                <p className="form-hint">Choose active campuses. Without an assignment, the OSA workspace contains no campus reports.</p>
              </fieldset>}
            </>}
            {user.studentProfile && <>
              <p className="text-sm">Student #{user.studentProfile.studentNumber} · {user.studentProfile.programName} · {user.studentProfile.siteName}</p>
              <label className="label">Student identity review<select className="field" name="approval" defaultValue={user.studentProfile.approvalStatus}><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option></select></label>
            </>}
            {!viewer.isSuperuser && <p className="form-hint">Only account activation and student review can be changed here. Roles, passwords, login identity and privileged accounts are protected.</p>}
            <Feedback error={error} message={saved ? 'Account changes saved.' : ''} />
            <button disabled={busy} className="btn-primary">{busy ? 'Saving...' : 'Save account changes'}</button>
          </div>
        </details>
      )}
    </form>
  )
}

export default function Administration() {
  const { user } = useAuth()
  const [section, setSection] = useState('catalogue')
  const configurationEditor = useRef(null)
  const catalogue = useApi(user.isAdmin ? '/staff/configuration/' : null)
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const users = useApi(user.isAdmin ? `/staff/users/?${new URLSearchParams({ q: query, page })}` : null)
  const empty = { kind: 'categories', id: '', name: '', code: '', site: '', is_active: true }
  const [form, setForm] = useState(empty)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const kinds = user.isSuperuser ? ['categories', 'sites', 'programs', 'offices'] : ['categories', 'programs', 'offices']

  function editRecord(kind, row) {
    if (busy) return
    setForm({ ...empty, ...row, kind, site: row.site_id || '' })
    setError(''); setMessage('')
    requestAnimationFrame(() => {
      const editor = configurationEditor.current
      editor?.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
      editor?.querySelector('input')?.focus({ preventScroll: true })
    })
  }
  function change(key, value) { setForm(current => ({ ...current, [key]: value })) }
  async function save(event) {
    event.preventDefault(); if (busy) return; setBusy(true); setError(''); setMessage('')
    try {
      await apiRequest('/staff/configuration/', { method: 'POST', data: form })
      catalogue.retry(); setForm(empty); setMessage('Campus configuration saved.')
    } catch (failure) { setError(failure.message) } finally { setBusy(false) }
  }

  if (!user.isAdmin) return <section className="app-page admin-page"><PageHeading title="Administrator access required" /><Link to="/profile" className="btn-secondary">My Profile</Link></section>

  return (
    <section className="app-page admin-page">
      <Link to={user.isOsa ? '/staff' : '/profile'} className="mb-6 inline-block text-sm underline">{user.isOsa ? 'Back to OSA workspace' : 'Back to my profile'}</Link>
      <PageHeading title="The details that keep it running." eyebrow="CAMPUS ADMINISTRATION">{user.isSuperuser ? 'Manage catalogue, ordinary accounts and privileged role assignments.' : 'Manage catalogue and ordinary accounts. Role assignments are reserved for the Super Admin.'}</PageHeading>
      <Feedback error={error || catalogue.error} message={message} />
      <div className="view-switch" role="group" aria-label="Administration area">
        <button type="button" aria-pressed={section === 'catalogue'} onClick={() => setSection('catalogue')}>Campus catalogue</button>
        <button type="button" aria-pressed={section === 'accounts'} onClick={() => setSection('accounts')}>Accounts & permissions</button>
      </div>
      {catalogue.error && <button className="btn-secondary mb-5" onClick={catalogue.retry}>Retry loading configuration</button>}
      {section === 'catalogue' && (catalogue.loading ? <Loading /> : catalogue.data && (
        <div className="admin-layout">
          <form ref={configurationEditor} className="panel scroll-mt-6" aria-busy={busy} onSubmit={save}><fieldset disabled={busy} className="min-w-0 space-y-4">
            <h2 className="text-xl font-bold">{form.id ? 'Edit configuration' : 'Add configuration'}</h2>
            <label className="label">Record type<select className="field" value={form.kind} onChange={event => setForm({ ...empty, kind: event.target.value })}>{kinds.map(kind => <option key={kind}>{kind}</option>)}</select></label>
            <label className="label">Name<input className="field" value={form.name} onChange={event => change('name', event.target.value)} required maxLength={form.kind === 'categories' ? 100 : 150} /></label>
            {['sites', 'programs'].includes(form.kind) && <label className="label">Code<input className="field" value={form.code} onChange={event => change('code', event.target.value)} required maxLength={32} /></label>}
            {form.kind === 'offices' && <label className="label">Campus<select className="field" value={form.site} onChange={event => change('site', event.target.value)} required><option value="">Choose a campus</option>{catalogue.data.sites.map(site => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label>}
            {form.kind !== 'programs' && <label className="flex gap-3 text-sm"><input type="checkbox" checked={form.is_active} onChange={event => change('is_active', event.target.checked)} />Active</label>}
            <div className="flex gap-3"><button disabled={busy} className="btn-primary">Save configuration</button><button type="button" className="btn-secondary" onClick={() => setForm(empty)}>Clear</button></div>
          </fieldset></form>
          <section className="configuration-list">
            <h2 className="text-xl font-semibold">{form.kind === 'sites' ? 'Campuses' : form.kind === 'programs' ? 'Programs' : form.kind === 'offices' ? 'Receiving offices' : 'Categories'}</h2>
            <p className="form-hint">Select a record type on the left to manage its entries.</p>
            {Object.entries(catalogue.data).filter(([kind]) => kind === form.kind).map(([kind, rows]) => <div className="mt-5" key={kind}>
              <h3 className="text-sm font-bold capitalize">{kind}</h3>
              {!rows.length && <p className="mt-2 text-xs text-slate-500">None configured.</p>}
              <ul className="mt-2 space-y-2">{rows.map(row => <li className="configuration-record" key={row.id}><span>{row.code ? `${row.code} · ` : ''}{row.name}{row.is_active === false ? ' (inactive)' : ''}</span><button type="button" disabled={busy} className="font-semibold underline" aria-label={`Edit ${row.name}`} aria-pressed={form.kind === kind && form.id === row.id} onClick={() => editRecord(kind, row)}>{form.kind === kind && form.id === row.id ? 'Editing' : 'Edit'}</button></li>)}</ul>
            </div>)}
          </section>
        </div>
      ))}
      {section === 'accounts' && <section>
        <h2 className="text-2xl font-bold">{user.isSuperuser ? 'Accounts & role assignments' : 'Ordinary accounts & identity review'}</h2>
        <form className="my-5 flex gap-3" onSubmit={event => { event.preventDefault(); setQuery(new FormData(event.currentTarget).get('q')); setPage(1) }}><label className="flex-1"><span className="sr-only">Search accounts</span><input className="field" name="q" placeholder="Search username or email" /></label><button className="btn-secondary self-end">Search</button></form>
        <Feedback error={users.error} />
        {users.error && <button className="btn-secondary mb-4" onClick={users.retry}>Retry loading accounts</button>}
        {users.loading || catalogue.loading ? <Loading /> : users.data && catalogue.data && <div className="space-y-5">
          {users.data.results.map(row => <UserPermissions key={`${row.id}:${JSON.stringify(row.siteIds)}:${row.roles.join(',')}:${row.isActive}:${row.studentProfile?.approvalStatus}`} user={row} viewer={user} sites={catalogue.data.sites} onSave={users.retry} />)}
          {!users.data.results.length && <p className="panel text-sm">No matching accounts.</p>}
        </div>}
        <Pagination data={users.data} onPage={setPage} />
      </section>}
    </section>
  )
}
