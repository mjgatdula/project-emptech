import { useState } from 'react'
import PageHeading from '../components/common/PageHeading'
import Feedback from '../components/common/Feedback'
import PasswordField from '../components/PasswordField'
import Loading from '../components/Loading'
import GoogleSignIn from '../components/GoogleSignIn'
import useAuth from '../context/useAuth'
import useApi from '../data/useApi'
import { apiRequest, authApi } from '../data/api'

export default function Profile() {
  const { user, refreshSession } = useAuth()
  const catalogue = useApi('/catalogue/')
  const configuration = useApi('/auth/config/')
  const [number, setNumber] = useState(user.studentProfile?.studentNumber || '')
  const [busy, setBusy] = useState(false)
  const [passwordBusy, setPasswordBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  async function save(event) {
    event.preventDefault(); if (busy || passwordBusy) return; setBusy(true); setError(''); setMessage('')
    const values = new FormData(event.currentTarget)
    const data = { fullName: values.get('fullName'), ...(!user.isExternal && number ? { studentNumber: number, site: values.get('site'), program: values.get('program') } : {}) }
    try { await apiRequest('/auth/profile/', { method: 'PATCH', data }); await refreshSession({ background: true }); setMessage('Profile saved. Changed student details are pending identity review.') } catch (failure) { setError(failure.message) } finally { setBusy(false) }
  }
  async function password(event) {
    event.preventDefault(); if (busy || passwordBusy) return; setError(''); setMessage('')
    const form = event.currentTarget
    const values = new FormData(form)
    if (values.get('new_password') !== values.get('confirm_password')) { setError('New passwords do not match.'); return }
    setPasswordBusy(true)
    try { await authApi.changePassword({ current_password: values.get('current_password'), new_password: values.get('new_password') }); form.reset(); await refreshSession({ background: true }); setMessage('Your password has been changed. Use the new password next time you sign in.') } catch (failure) { setError(failure.message) } finally { setPasswordBusy(false) }
  }
  return <section className="app-page app-page-narrow profile-page"><PageHeading title="Your campus, your details." eyebrow="MY PROFILE">Manage your account, student information and password.</PageHeading><Feedback error={error || catalogue.error} message={message} /><div className="profile-layout"><aside className="profile-summary text-sm">{[['Username', user.username], ['Email', user.email], ['Role', user.isSuperuser ? 'Super Admin' : user.isAdmin && user.isOsa ? 'Administrator / OSA' : user.isAdmin ? 'Administrator' : user.isOsa ? 'OSA personnel' : user.isExternal ? 'External user' : 'Student'], ['Identity review', user.studentProfile?.approvalStatus || 'No student details submitted']].map(([label, value]) => <div key={label}><p className="text-xs text-slate-500">{label}</p><p className="mt-2 break-words font-semibold">{value}</p></div>)}</aside><div>
    {catalogue.loading ? <Loading /> : catalogue.data && <form className="panel space-y-5" onSubmit={save}><h2 className="text-xl font-bold">Account details</h2><label className="label">Full name<input className="field" name="fullName" defaultValue={user.fullName || user.username} required maxLength={150} /></label>{!user.isExternal && <details className="form-section" open={Boolean(user.studentProfile) || undefined}><summary>Student details <span className="font-normal text-slate-500">· optional unless already registered</span></summary><div className="mt-4 space-y-5"><label className="label">Student number{user.studentProfile ? '' : ' (optional)'}<input className="field" required={Boolean(user.studentProfile)} value={number} onChange={e => setNumber(e.target.value)} maxLength={50} /></label><p className="text-xs text-slate-500">If you provide a student number, select your campus and program. Identity approval is performed by authorized administrators.</p><div className="grid gap-5 sm:grid-cols-2"><label className="label">Campus<select className="field" name="site" defaultValue={user.studentProfile?.site || ''} required={Boolean(number)}><option value="">Choose a campus</option>{catalogue.data.sites.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label><label className="label">Program<select className="field" name="program" defaultValue={user.studentProfile?.program || ''} required={Boolean(number)}><option value="">Choose a program</option>{catalogue.data.programs.map(row => <option key={row.id} value={row.id}>{row.code} · {row.name}</option>)}</select></label></div>{!catalogue.data.programs.length && <p className="text-xs text-slate-500">The administrator can add your institution's programs in Campus Administration. You can save your name without student details.</p>}</div></details>}<button disabled={busy || passwordBusy} className="btn-primary">{busy ? 'Saving...' : 'Save profile'}</button></form>}
    {!user.googleLinked && <GoogleSignIn configuration={configuration} link />}
    {configuration.data?.passwordAuthEnabled && <details className="security-settings"><summary>Security · change your password</summary><form className="mt-5 space-y-5" onSubmit={password}><h2 className="text-xl font-bold">Change password</h2><PasswordField id="current-password" name="current_password" label="Current password" autoComplete="current-password" /><PasswordField id="new-password" name="new_password" label="New password" minLength={8} autoComplete="new-password" /><PasswordField id="confirm-password" name="confirm_password" label="Confirm new password" minLength={8} autoComplete="new-password" /><button disabled={busy || passwordBusy} className="btn-primary">{passwordBusy ? 'Changing password...' : 'Change password'}</button></form></details>}</div></div>
  </section>
}
