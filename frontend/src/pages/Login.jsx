import Loading from '../components/Loading'
import GoogleSignIn from '../components/GoogleSignIn'
import useApi from '../data/useApi'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { LuLockKeyhole, LuLogIn } from 'react-icons/lu'
import PasswordField from '../components/PasswordField'
import useAuth from '../context/useAuth'
import PageHeading from '../components/common/PageHeading'
import ReportProgress from '../components/reports/ReportProgress'

export default function Login() {
  const [params] = useSearchParams()
  const configuration = useApi('/auth/config/')
  const navigate = useNavigate()
  const { signIn, loading } = useAuth()
  const [submitting, setSubmitting] = useState(false)
  const requestedNext = params.get('next') || ''
  const next = /^\/(?:report|my-reports|profile|notifications|staff(?:\/settings)?|browse\/[a-fA-F0-9-]{36})(?:\?|$)/.test(requestedNext) ? requestedNext : ''
  const reporting = next.split('?')[0] === '/report'
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting) return
    const identity = event.currentTarget.elements.namedItem('identity')
    if (!identity.value.trim()) {
      setError('Enter your email or username.')
      identity.focus()
      return
    }
    setError('')
    setMessage('')
    setSubmitting(true)
    const password = event.currentTarget.elements.namedItem('password').value
    try {
      const result = await signIn({ identity: identity.value.trim(), password })
      if (result.ok) navigate(next || (result.user.isAdmin ? '/staff/settings' : result.user.isOsa ? '/staff' : '/my-reports'), { replace: true })
      else setError(result.message)
    } catch {
      setError('Sign-in could not be completed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <Loading label="Checking your session..." />

  return (
    <section className="app-page account-page">
      <div className="account-layout">
      <div className="account-editorial">
      <PageHeading title={<>A familiar place.<br /><em>Welcome back.</em></>} eyebrow="YOUR CAMPUS ACCOUNT">Sign in to report a belonging, track an update or arrange a verified return.</PageHeading>
      {reporting && <ReportProgress />}
      <p className="account-side-note">Looking for an item? The campus board is open to everyone. You only need an account to report or claim.</p></div><div className="account-form">
        <div className="account-form-note flex items-start gap-3">
          <LuLockKeyhole aria-hidden="true" className="mt-1 h-4 w-4 shrink-0 text-brand-800" />
          <p id="login-preview-note" className="text-xs leading-6 text-slate-600"><strong className="text-slate-900">Sign in to TIPPED.</strong> {configuration.data?.passwordAuthEnabled ? 'Use Google or your existing email/username and password.' : 'Use your verified school Google account.'}</p>
        </div>
        <GoogleSignIn configuration={configuration} next={next} />
        {configuration.data?.passwordAuthEnabled && <form onSubmit={handleSubmit} onInput={() => { setMessage(''); setError('') }} aria-describedby="login-preview-note" className="space-y-5" aria-busy={submitting}><fieldset disabled={submitting} className="min-w-0 space-y-5">
          <div>
            <label htmlFor="login-identity" className="block text-sm font-semibold text-slate-700">Email or username *</label>
            <input id="login-identity" name="identity" type="text" autoComplete="username" autoCapitalize="none" spellCheck={false} required maxLength={254} aria-invalid={Boolean(error) || undefined} aria-describedby={error ? 'login-error' : undefined} placeholder="Enter your email or username" className="field" />
          </div>
          <PasswordField id="login-password" name="password" label="Password" autoComplete="current-password" />
          {error && <p id="login-error" role="alert" className="text-sm text-red-700">{error}</p>}
          {message && <p role="status" className="rounded-xl border border-brand-200 bg-brand-50 p-4 text-sm leading-7 text-slate-700">{message}</p>}
          <button type="submit" disabled={submitting} aria-busy={submitting} className="btn-primary w-full">{submitting ? <Loading inline label="Signing in..." /> : <><LuLogIn aria-hidden="true" />Sign In</>}</button>
        </fieldset></form>}
        <p className="mt-5 flex flex-wrap items-center justify-center gap-x-1 gap-y-1 text-center text-sm leading-6 text-slate-600">New to TIPPED? <Link to={`/register?${new URLSearchParams({ next })}`} className="font-semibold text-brand-800 underline underline-offset-4">Create an account</Link></p>
        <div className="mt-5 border-t border-slate-100 pt-5 text-center">
          <Link to={reporting ? next : '/browse'} className="rounded px-2 py-1 text-xs font-semibold text-slate-600 underline underline-offset-4">{reporting ? 'Back to reporting steps' : 'Browse items without signing in'}</Link>
        </div>
      </div>
      </div>
    </section>
  )
}
