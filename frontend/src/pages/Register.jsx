import Loading from '../components/Loading'
import GoogleSignIn from '../components/GoogleSignIn'
import useApi from '../data/useApi'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { LuLockKeyhole, LuUserPlus } from 'react-icons/lu'
import PasswordField from '../components/PasswordField'
import useAuth from '../context/useAuth'
import PageHeading from '../components/common/PageHeading'
import ReportProgress from '../components/reports/ReportProgress'

const fieldClass = 'field'

export default function Register() {
  const [params] = useSearchParams()
  const configuration = useApi('/auth/config/')
  const { register, loading } = useAuth()
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const requestedNext = params.get('next') || ''
  const next = /^\/(?:report|my-reports|profile|notifications|staff(?:\/settings)?|browse\/[a-fA-F0-9-]{36})(?:\?|$)/.test(requestedNext) ? requestedNext : '/my-reports'
  const reporting = next.split('?')[0] === '/report'
  const [error, setError] = useState(null)
  const [message, setMessage] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting) return
    const form = event.currentTarget
    const values = new FormData(form)
    for (const field of ['fullName', 'username']) {
      if (!String(values.get(field) || '').trim()) {
        setError({ field, text: field === 'fullName' ? 'Enter your full name.' : 'Enter a username.' })
        form.elements.namedItem(field).focus()
        return
      }
    }
    if (values.get('password') !== values.get('confirmPassword')) {
      setError({ field: 'confirmPassword', text: 'Passwords do not match. Enter the same password in both fields.' })
      form.elements.namedItem('confirmPassword').focus()
      return
    }
    setError(null)
    setMessage('')
    setSubmitting(true)
    try {
      const result = await register({
        fullName: String(values.get('fullName')).trim(),
        username: String(values.get('username')).trim(),
        email: String(values.get('email')).trim(),
        password: values.get('password'),
      })
      if (result.ok) navigate(next, { replace: true })
      else setError({ field: '', text: result.message })
    } catch {
      setError({ field: '', text: 'Registration could not be completed. Please try again.' })
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <Loading label="Checking your session..." />

  return (
    <section className="app-page account-page">
      <div className="account-layout">
      <div className="account-editorial">
      <PageHeading title={<>A little care.<br /><em>A connection.</em></>} eyebrow="CREATE YOUR ACCOUNT">Join your campus lost and found community. Keep your reports, claims and updates together.</PageHeading>
      {reporting && <ReportProgress />}
      <p className="account-side-note">A misplaced essential. A thoughtful finder. Be part of the way back.</p></div><div className="account-form">
        <div className="account-form-note flex items-start gap-3">
          <LuLockKeyhole aria-hidden="true" className="mt-1 h-4 w-4 shrink-0 text-brand-800" />
          <p id="register-preview-note" className="text-xs leading-6 text-slate-600"><strong className="text-slate-900">Create your account.</strong> {configuration.data?.passwordAuthEnabled ? 'All fields are required. You can add student details later in your profile.' : 'TIP Google accounts can register directly. External Google accounts need Super Admin approval before signing in.'}</p>
        </div>
        <GoogleSignIn configuration={configuration} next={next} />
        {configuration.data?.passwordAuthEnabled && <form onSubmit={handleSubmit} onInput={() => { setError(null); setMessage('') }} aria-describedby="register-preview-note" className="space-y-5" aria-busy={submitting}><fieldset disabled={submitting} className="min-w-0 space-y-5">
          <div className="grid gap-5 sm:grid-cols-2">
            <div><label htmlFor="register-name" className="block text-sm font-semibold text-slate-700">Full name *</label><input id="register-name" name="fullName" autoComplete="name" required maxLength={150} aria-invalid={error?.field === 'fullName' || undefined} aria-describedby={error?.field === 'fullName' ? 'register-error' : undefined} placeholder="Your full name" className={fieldClass} /></div>
            <div><label htmlFor="register-username" className="block text-sm font-semibold text-slate-700">Username *</label><input id="register-username" name="username" autoComplete="username" autoCapitalize="none" spellCheck={false} required maxLength={150} aria-invalid={error?.field === 'username' || undefined} aria-describedby={error?.field === 'username' ? 'register-error' : undefined} placeholder="Choose a username" className={fieldClass} /></div>
          </div>
          <div><label htmlFor="register-email" className="block text-sm font-semibold text-slate-700">Email address *</label><input id="register-email" name="email" type="email" autoComplete="email" autoCapitalize="none" spellCheck={false} required maxLength={254} placeholder="you@example.edu" className={fieldClass} /></div>
          <PasswordField id="register-password" name="password" label="Password" autoComplete="new-password" minLength={8} describedBy="register-password-help" />
          <p id="register-password-help" className="text-xs leading-6 text-slate-500">Use at least 8 characters. Avoid common, entirely numeric passwords or passwords similar to your account details.</p>
          <PasswordField id="register-confirm-password" name="confirmPassword" label="Confirm password" autoComplete="new-password" minLength={8} invalid={error?.field === 'confirmPassword'} describedBy={error?.field === 'confirmPassword' ? 'register-error' : undefined} />
          {error && <p id="register-error" role="alert" className="text-sm text-red-700">{error.text}</p>}
          {message && <p role="status" className="rounded-xl border border-brand-200 bg-brand-50 p-4 text-sm leading-7 text-slate-700">{message}</p>}
          <button type="submit" disabled={submitting} aria-busy={submitting} className="btn-primary w-full">{submitting ? <Loading inline label="Creating account..." /> : <><LuUserPlus aria-hidden="true" />Create Account</>}</button>
        </fieldset></form>}
        <p className="mt-6 text-center text-sm leading-7 text-slate-600">Already registered? <Link to={`/login?${new URLSearchParams({ next })}`} className="font-semibold text-brand-800 underline underline-offset-4">Sign In</Link></p>
        {reporting && <div className="mt-5 text-center"><Link to={next} className="text-xs font-semibold text-slate-600 underline underline-offset-4">Back to reporting steps</Link></div>}
      </div>
      </div>
    </section>
  )
}
