import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuth from '../context/useAuth'
import { apiRequest, authApi } from '../data/api'
import Loading from './Loading'
import Feedback from './common/Feedback'

let sdk
function loadSdk() {
  if (window.google?.accounts?.id) return Promise.resolve(window.google.accounts.id)
  if (!sdk) sdk = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'; script.async = true
    const timer = setTimeout(() => { script.remove(); sdk = null; reject(new Error('Google sign-in could not load. Check your connection and try again.')) }, 15000)
    script.onload = () => { clearTimeout(timer); if (window.google?.accounts?.id) resolve(window.google.accounts.id); else { sdk = null; script.remove(); reject(new Error('Google sign-in could not initialize. Please retry.')) } }
    script.onerror = () => { clearTimeout(timer); script.remove(); sdk = null; reject(new Error('Google sign-in could not load. Try again.')) }
    document.head.append(script)
  })
  return sdk
}

export default function GoogleSignIn({ configuration, next = '', link = false }) {
  const { signIn, refreshSession } = useAuth()
  const navigate = useNavigate()
  const target = useRef(null), pending = useRef(false)
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), [revision, setRevision] = useState(0)
  const clientId = configuration.data?.googleClientId || ''
  useEffect(() => {
    if (!clientId) return undefined
    let active = true
    const element = target.current
    const originalPath = window.location.pathname
    Promise.all([loadSdk(), apiRequest('/auth/google/challenge/', { auth: false })]).then(([google, challenge]) => {
      if (!active) return
      google.initialize({client_id: clientId, nonce: challenge.nonce, auto_select: false,
        callback: async ({ credential }) => {
          if (!active || pending.current) return
          pending.current = true; setBusy(true); setError('')
          try {
            let result
            if (link) { const data = await authApi.linkGoogle(credential); await refreshSession({background:true}); result = {ok:true,user:data.user} }
            else result = await signIn({googleCredential: credential})
            if (!active && window.location.pathname !== originalPath) return
            if (!result.ok) throw new Error(result.message)
            navigate(link ? '/profile' : next || (result.user.isAdmin ? '/staff/settings' : result.user.isOsa ? '/staff' : '/my-reports'), {replace:true})
          } catch (failure) { if (active) setError(failure.message) }
          finally { pending.current = false; if (active) { setBusy(false); setRevision(v=>v+1) } }
        }})
      google.renderButton(element, {type:'standard', theme:'outline', size:'large', text:'continue_with', width:Math.min(350, element.clientWidth || 280)})
    }).catch(failure => { if (active) setError(failure.message) })
    return () => { active = false; element?.replaceChildren() }
  }, [clientId, next, link, signIn, refreshSession, navigate, revision])
  if (configuration.loading) return <Loading inline label="Loading sign-in options..." />
  if (configuration.error) return <><Feedback error={configuration.error} /><button className="btn-secondary" onClick={configuration.retry}>Retry sign-in options</button></>
  if (!clientId) return <p className="mb-5 text-sm text-slate-600">Google sign-in is not available yet. Contact the site administrator.</p>
  return <section className="mb-6 space-y-3" aria-label={link ? 'Link Google account' : 'Google sign-in'} aria-busy={busy}>
    {link && <p className="text-center text-sm leading-6">Link your Google account.</p>}
    <div ref={target} className={`flex min-w-0 justify-center ${busy ? 'pointer-events-none opacity-50' : ''}`} inert={busy || undefined} />
    {busy && <Loading inline label="Verifying Google sign-in..." />}<Feedback error={error} />
    {error && <button className="btn-secondary" onClick={() => {setError('');setRevision(v=>v+1)}}>Retry Google sign-in</button>}
  </section>
}
