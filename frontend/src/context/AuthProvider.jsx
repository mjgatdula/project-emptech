import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { AuthContext } from './AuthContext'
import { authApi } from '../data/api'
import Loading from '../components/Loading'

export function AuthProvider({ children }) {
  const location = useLocation()
  const [user, setUser] = useState(null)
  const [isLoading, setLoading] = useState(true)
  const [backendConnected, setBackendConnected] = useState(false)
  const [authError, setAuthError] = useState('')
  const revision = useRef(0)
  const isAuthenticated = backendConnected && Boolean(user)

  const refreshSession = useCallback(async ({ background = false } = {}) => {
    const current = ++revision.current
    if (!background) setLoading(true)
    try {
      const result = await authApi.session({ force: true })
      if (current === revision.current) {
        setUser(result.user)
        setBackendConnected(true)
        setAuthError('')
      }
      return result
    } catch (error) {
      if (current === revision.current) {
        setUser(null)
        setBackendConnected(false)
        setAuthError(error.message)
      }
      return null
    } finally {
      if (current === revision.current) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    let active = true
    const current = ++revision.current
    // Initial verification blocks rendering. Later route checks reuse verified
    // results briefly or run in the background without unmounting the pages.
    authApi.session().then((result) => {
      if (!active || current !== revision.current) return
      setUser(result.user)
      setBackendConnected(true)
      setAuthError('')
    }).catch((error) => {
      if (!active || current !== revision.current) return
      setUser(null)
      setBackendConnected(false)
      setAuthError(error.message)
    }).finally(() => {
      if (active && current === revision.current) {
        setLoading(false)
      }
    })
    return () => { active = false }
  }, [location.key])

  useEffect(() => {
    const syncStorage = (event) => {
      if (event.key !== null && event.key !== 'access_token' && event.key !== 'refresh_token') return
      // Sign out immediately when another tab removes credentials.
      try {
        if (!localStorage.getItem('access_token') && !localStorage.getItem('refresh_token')) setUser(null)
      } catch { setUser(null) }
      refreshSession({ background: true })
    }
    const clearAuthentication = () => {
      revision.current += 1
      setLoading(false)
      setUser(null)
      setAuthError('')
    }
    window.addEventListener('storage', syncStorage)
    window.addEventListener('tipped:auth-cleared', clearAuthentication)
    return () => {
      window.removeEventListener('storage', syncStorage)
      window.removeEventListener('tipped:auth-cleared', clearAuthentication)
    }
  }, [refreshSession])

  const signIn = useCallback(async (credentials) => {
    const current = ++revision.current
    try {
      const result = await authApi.signIn(credentials)
      const authenticated = result.isAuthenticated === true && Boolean(result.user)
      if (!authenticated) throw new Error('Django did not confirm an authenticated session.')
      if (current !== revision.current) return { ok: false, message: 'The page changed while signing in. Please try again.' }
      console.log(authenticated)
      if (current === revision.current) {
        setUser(result.user)
        setBackendConnected(true)
        setAuthError('')
      }
      return { ok: true, user: result.user }
    } catch (error) {
      console.log(false)
      if (current === revision.current) {
        setBackendConnected(Boolean(error.status && error.status < 500))
        setAuthError(!error.status || error.status >= 500 ? error.message : '')
      }
      return { ok: false, message: error.message }
    }
  }, [])

  const register = useCallback(async (details) => {
    const current = ++revision.current
    try {
      const result = await authApi.register(details)
      if (current !== revision.current) return { ok: false, message: 'The page changed while registering. Please sign in to check your account.' }
      if (result.isAuthenticated !== true || !result.user) throw new Error('Django did not confirm an authenticated session.')
      if (current === revision.current) {
        setUser(result.user)
        setBackendConnected(true)
        setAuthError('')
      }
      return { ok: true, user: result.user }
    } catch (error) {
      if (current === revision.current) {
        setBackendConnected(Boolean(error.status && error.status < 500))
        setAuthError(!error.status || error.status >= 500 ? error.message : '')
      }
      return { ok: false, message: error.message }
    }
  }, [])

  const signOut = useCallback(async () => {
    const current = ++revision.current
    try {
      await authApi.signOut()
      if (current !== revision.current) return { ok: false, message: 'The page changed while signing out. Please check your session.' }
      if (current === revision.current) {
        setUser(null)
        setBackendConnected(true)
        setAuthError('')
      }
      return { ok: true }
    } catch (error) {
      if (current === revision.current) setAuthError(error.message)
      return { ok: false, message: error.message }
    }
  }, [])

  // Keep the existing pages' loading name compatible with isLoading.
  const value = useMemo(() => ({
    user, isAuthenticated, isLoading, loading: isLoading,
    backendConnected, authError, refreshSession, signIn, register, signOut,
  }), [user, isAuthenticated, isLoading, backendConnected, authError, refreshSession, signIn, register, signOut])

  return (
    <AuthContext.Provider value={value}>
      {isLoading ? <Loading label="Checking your session..." /> : children}
    </AuthContext.Provider>
  )
}

export default AuthProvider
